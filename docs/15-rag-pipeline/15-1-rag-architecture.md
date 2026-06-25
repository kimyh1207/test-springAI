---
title: "15-1. RAG 아키텍처 전체 그림"
order: 1
tags: [rag, architecture, indexing, retrieval]
status: draft
author: vivace
---

# 15-1. RAG 아키텍처 전체 그림

RAG는 두 개의 독립적인 파이프라인으로 이루어집니다. 문서를 미리 처리하는 **인덱싱 파이프라인**과 사용자 질문을 처리하는 **쿼리 파이프라인**입니다.

---

## 전체 구조

```
[인덱싱 파이프라인] — 오프라인, 문서 추가/수정 시 실행
─────────────────────────────────────────────────────
원본 문서
  ↓ 로드 (PDF, Markdown, HTML, DB)
텍스트 추출
  ↓ 청킹 (의미 단위 분할)
청크 목록
  ↓ 임베딩 (텍스트 → 벡터)
벡터 + 메타데이터
  ↓ 저장
Vector DB


[쿼리 파이프라인] — 온라인, 사용자 요청마다 실행
─────────────────────────────────────────────────────
사용자 질문
  ↓ 쿼리 임베딩
질문 벡터
  ↓ 유사도 검색
관련 청크 k개
  ↓ (선택) 리랭킹
정렬된 청크
  ↓ 프롬프트 조립
[시스템] + [컨텍스트] + [질문]
  ↓ LLM 호출
최종 답변
```

---

## 인덱싱 파이프라인 설계 결정

### 문서 로더 선택

```python
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredMarkdownLoader,
    WebBaseLoader,
    CSVLoader,
    JSONLoader
)

# PDF
loader = PyPDFLoader("policy.pdf")
docs = loader.load()  # 페이지별 Document 리스트

# 웹 페이지
loader = WebBaseLoader("https://docs.spring.io/spring-ai/")
docs = loader.load()

# CSV
loader = CSVLoader("products.csv", content_columns=["description"],
                   metadata_columns=["id", "category", "price"])
docs = loader.load()
```

### 언제 인덱싱을 재실행하는가

| 트리거 | 방법 |
|--------|------|
| 새 문서 추가 | 해당 문서만 청킹·임베딩 후 추가 |
| 문서 수정 | 기존 청크 삭제 후 재인덱싱 |
| 임베딩 모델 변경 | 전체 재인덱싱 필요 |
| 청킹 전략 변경 | 전체 재인덱싱 필요 |

문서에 고유 ID를 부여하고 변경 감지를 구현하면 증분 업데이트가 가능합니다.

---

## 쿼리 파이프라인 설계 결정

### 검색 방법

| 방법 | 설명 | 적합한 상황 |
|------|------|------------|
| 의미 검색 | 벡터 유사도 | 자연어 질문 |
| 키워드 검색 | BM25, TF-IDF | 고유 명사, 코드, 숫자 |
| 하이브리드 | 둘 결합 | 대부분의 실제 서비스 |
| 메타데이터 필터 | 범위 제한 후 검색 | 날짜, 카테고리 등 |

### top_k 설정

```python
# top_k가 너무 작으면 → 관련 정보를 놓침
# top_k가 너무 크면 → 컨텍스트 오염, 토큰 낭비

# 일반적인 권장값
top_k = 5           # 검색 단계
rerank_top_k = 3    # 리랭킹 후

# 컨텍스트 크기 계산
avg_chunk_tokens = 200
max_context_tokens = top_k * avg_chunk_tokens  # 1000 토큰
```

### 쿼리 변환

사용자 질문이 모호하거나 짧을 때 검색 품질을 높이는 기법들입니다.

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 1. 쿼리 재작성
def rewrite_query(query: str) -> str:
    return llm.invoke(f"""다음 질문을 문서 검색에 최적화된 형태로 재작성하세요.
간결하고 핵심 키워드 중심으로.

원본 질문: {query}
재작성된 질문:""").content

# 2. 다중 쿼리 생성 (여러 관점으로 검색)
def generate_multi_queries(query: str) -> list[str]:
    response = llm.invoke(f"""다음 질문과 관련해 다양한 관점의 검색 쿼리 3개를 생성하세요.
각 쿼리를 새 줄에 작성하세요.

질문: {query}
검색 쿼리:""").content
    return [q.strip() for q in response.strip().split('\n') if q.strip()]

# 3. HyDE (Hypothetical Document Embedding)
def hyde_query(query: str) -> str:
    """가상의 답변 문서를 생성하고, 그것을 임베딩해 검색"""
    hypothetical_doc = llm.invoke(f"""다음 질문에 대한 이상적인 답변 문서 단락을 작성하세요:

질문: {query}
답변 문서:""").content
    return hypothetical_doc  # 이것을 임베딩해 검색
```

---

## 컨텍스트 조립

검색된 청크를 LLM에게 전달할 형태로 구성합니다.

```python
def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("metadata", {}).get("source", "알 수 없는 출처")
        parts.append(f"[문서 {i}] (출처: {source})\n{chunk['content']}")
    return "\n\n---\n\n".join(parts)

def build_prompt(query: str, context: str) -> str:
    return f"""다음 문서들을 참고해 질문에 답하세요.

규칙:
1. 반드시 제공된 문서 내용만을 근거로 답하세요
2. 문서에 없는 내용은 "제공된 문서에서 찾을 수 없습니다"라고 답하세요
3. 답변 끝에 근거가 된 문서 번호를 표시하세요 (예: [출처: 문서 1, 3])

[참고 문서]
{context}

[질문]
{query}

[답변]"""
```

---

> RAG 아키텍처를 이해하면 어디서 성능 병목이 생기는지 보입니다. 검색 실패인지, 생성 실패인지를 구분해야 올바른 개선 방향을 잡을 수 있습니다.
