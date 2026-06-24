---
title: "14-3. ★확장 — 청킹·메타데이터 설계가 검색 품질을 좌우한다"
order: 3
tags: [chunking, metadata, rag, retrieval-quality]
status: draft
author: vivace
---

# 14-3. ★확장 — 청킹·메타데이터 설계가 검색 품질을 좌우한다

임베딩 모델이 좋아도 문서를 어떻게 쪼개고, 어떤 메타데이터를 붙이느냐에 따라 검색 품질이 극적으로 달라집니다.

---

## 청킹이란

문서를 임베딩할 수 있는 작은 단위로 나누는 과정입니다. 너무 크면 관련 없는 내용이 섞이고, 너무 작으면 맥락이 사라집니다.

```
문서 전체 (10,000자)
    ↓ 청킹
청크 1 (500자): 환불 정책 1절
청크 2 (500자): 환불 정책 2절
청크 3 (500자): 배송 정책 1절
...
```

---

## 청킹 전략

### 고정 크기 청킹

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,    # 청크 간 50자 중복 (맥락 보존)
    separators=["\n\n", "\n", ".", " ", ""]
)

with open("policy.txt") as f:
    text = f.read()

chunks = splitter.split_text(text)
print(f"청크 수: {len(chunks)}")
print(f"첫 청크: {chunks[0][:100]}...")
```

`chunk_overlap`: 청크 경계에서 문장이 잘리는 문제를 완화합니다. 보통 청크 크기의 10~20%.

### 의미 단위 청킹 (권장)

문단, 섹션, 문장 단위로 나눕니다. 고정 크기보다 검색 품질이 높습니다.

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

# Markdown 헤더 기준으로 분할
md_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "chapter"),
        ("##", "section"),
        ("###", "subsection")
    ]
)

with open("manual.md") as f:
    md_text = f.read()

chunks = md_splitter.split_text(md_text)

# 각 청크에 헤더 정보가 메타데이터로 자동 포함
for chunk in chunks[:3]:
    print(chunk.metadata)  # {'chapter': '3장', 'section': '환불 정책'}
    print(chunk.page_content[:100])
    print()
```

### 부모-자식 청킹

검색은 작은 청크로 하고, LLM에는 더 큰 맥락을 제공합니다.

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.retrievers import ParentDocumentRetriever
from langchain_chroma import Chroma

# 부모: 큰 단위 (2000자)
parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000)

# 자식: 작은 단위 (200자)로 검색
child_splitter = RecursiveCharacterTextSplitter(chunk_size=200)

vectorstore = Chroma(collection_name="child_chunks", embedding_function=embedding_fn)
docstore = InMemoryStore()

retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    docstore=docstore,
    child_splitter=child_splitter,
    parent_splitter=parent_splitter
)

# 쿼리: 자식 청크로 검색 → 부모 청크(맥락) 반환
docs = retriever.get_relevant_documents("환불 기간은?")
```

---

## 메타데이터 설계

메타데이터는 필터링과 재랭킹에 사용됩니다. 잘 설계하면 검색 정확도를 크게 높일 수 있습니다.

```python
# 풍부한 메타데이터 예시
documents = [
    {
        "content": "환불 신청은 구매 후 30일 이내에 가능합니다...",
        "metadata": {
            "source": "policy/refund-policy.md",
            "section": "환불 정책",
            "subsection": "신청 기간",
            "doc_type": "policy",
            "language": "ko",
            "last_updated": "2024-03-01",
            "version": "2.1",
            "tags": ["환불", "기간", "정책"]
        }
    }
]

# 메타데이터 필터로 범위 좁히기
results = collection.query(
    query_embeddings=[query_vec],
    n_results=5,
    where={
        "$and": [
            {"doc_type": {"$eq": "policy"}},
            {"language": {"$eq": "ko"}}
        ]
    }
)
```

---

## 하이브리드 검색

벡터 검색(의미)과 키워드 검색(정확 매칭)을 결합하면 단독보다 높은 성능을 냅니다.

```python
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# 키워드 기반 BM25
bm25_retriever = BM25Retriever.from_documents(docs)
bm25_retriever.k = 3

# 벡터 기반
vectorstore = Chroma.from_documents(docs, OpenAIEmbeddings())
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 앙상블: 60% 벡터 + 40% BM25
ensemble = EnsembleRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    weights=[0.6, 0.4]
)

results = ensemble.get_relevant_documents("환불 30일")
```

---

## 재랭킹(Re-ranking)

초기 검색 결과를 더 정교한 모델로 재정렬합니다.

```python
from anthropic import Anthropic

client = Anthropic()

def rerank(query: str, candidates: list[str], top_k: int = 3) -> list[str]:
    numbered = "\n".join(f"{i+1}. {doc}" for i, doc in enumerate(candidates))
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": f"""질문: {query}

다음 문서들을 질문에 대한 관련성 순으로 번호만 나열하세요:
{numbered}

형식: 1, 3, 2 (관련성 높은 순)"""
        }]
    )
    
    order = [int(x.strip()) - 1 for x in response.content[0].text.split(",")]
    return [candidates[i] for i in order[:top_k]]
```

---

## RAG 품질 평가

```python
def evaluate_rag(qa_pairs: list[dict], retriever, llm) -> dict:
    """
    qa_pairs: [{"question": "...", "expected_answer": "..."}, ...]
    """
    scores = []
    
    for item in qa_pairs:
        docs = retriever.get_relevant_documents(item["question"])
        context = "\n\n".join(d.page_content for d in docs)
        
        response = llm.invoke(f"문서:\n{context}\n\n질문: {item['question']}")
        
        # LLM 기반 채점 (0~1)
        score_response = llm.invoke(f"""
예상 답변: {item['expected_answer']}
실제 답변: {response}

실제 답변이 예상 답변의 핵심 내용을 포함하면 1, 아니면 0을 반환하세요.
숫자만 반환하세요.""")
        
        scores.append(float(score_response.strip()))
    
    return {
        "accuracy": sum(scores) / len(scores),
        "total": len(scores),
        "passed": sum(1 for s in scores if s >= 0.5)
    }
```

---

## 청킹 설계 체크리스트

```
[ ] 청크 크기가 임베딩 모델의 최대 토큰 이내인가 (대부분 8192 토큰)
[ ] 청크 오버랩으로 경계 문제를 완화했는가
[ ] 의미 단위(문단, 섹션)로 나눴는가
[ ] 각 청크에 출처(source) 메타데이터가 있는가
[ ] 필터링에 사용할 메타데이터를 설계했는가
[ ] 검색 품질을 평가할 Q&A 쌍을 만들었는가
```

---

> 청킹은 RAG의 가장 저평가된 부분입니다. 임베딩 모델을 바꾸는 것보다 청킹 전략을 개선하는 것이 더 큰 효과를 낼 때가 많습니다.
