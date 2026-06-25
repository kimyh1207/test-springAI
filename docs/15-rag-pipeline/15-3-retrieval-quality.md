---
title: "15-3. 검색 품질 향상(리랭킹 · 하이브리드 검색)"
order: 3
tags: [reranking, hybrid-search, retrieval, bm25]
status: draft
author: vivace
---

# 15-3. 검색 품질 향상(리랭킹 · 하이브리드 검색)

벡터 검색만으로 부족할 때 리랭킹과 하이브리드 검색을 추가하면 검색 정확도가 눈에 띄게 올라갑니다.

---

## 문제: 벡터 검색의 한계

벡터 검색은 의미적 유사도를 잘 잡지만 두 가지 약점이 있습니다.

1. **정확한 키워드 매칭에 약하다** — "RFC-7231", "CVE-2024-1234" 같은 고유 식별자는 의미 벡터보다 키워드 검색이 정확합니다.
2. **top-k 결과 내 순위가 항상 최적이 아니다** — 유사도 점수가 가장 높은 것이 실제로 가장 관련성 높은 문서가 아닐 수 있습니다.

---

## 하이브리드 검색

BM25(키워드)와 벡터 검색을 결합합니다.

```python
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

# 준비된 청크 목록
chunks: list[Document] = [...]  # 인덱싱된 청크들

# BM25 — 키워드 기반
bm25 = BM25Retriever.from_documents(chunks)
bm25.k = 5

# 벡터 기반
vectorstore = Chroma.from_documents(chunks, OpenAIEmbeddings())
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# 앙상블: RRF(Reciprocal Rank Fusion)로 결합
ensemble = EnsembleRetriever(
    retrievers=[vector_retriever, bm25],
    weights=[0.6, 0.4]   # 벡터 60%, BM25 40%
)

results = ensemble.invoke("환불 정책 30일")
for doc in results:
    print(doc.page_content[:100])
```

---

## 크로스 인코더 리랭킹

벡터 검색으로 후보군을 뽑은 다음, 더 정교한 모델로 순위를 재정렬합니다.

```python
from sentence_transformers import CrossEncoder

# 크로스 인코더: 쿼리와 문서를 함께 입력해 관련성 점수 계산
# 바이 인코더(벡터 검색)보다 느리지만 정확
cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank_with_cross_encoder(
    query: str,
    candidates: list[Document],
    top_k: int = 3
) -> list[Document]:
    # (쿼리, 문서) 쌍으로 점수 계산
    pairs = [(query, doc.page_content) for doc in candidates]
    scores = cross_encoder.predict(pairs)
    
    # 점수 기준 정렬
    ranked = sorted(zip(scores, candidates), reverse=True)
    return [doc for _, doc in ranked[:top_k]]

# 사용: 벡터 검색으로 10개 뽑은 후 리랭킹해서 3개만
candidates = vectorstore.similarity_search(query, k=10)
final_docs = rerank_with_cross_encoder(query, candidates, top_k=3)
```

---

## Cohere Rerank API

크로스 인코더를 직접 운영하기 어려울 때 API를 씁니다.

```python
import cohere
import os

co = cohere.Client(os.environ["COHERE_API_KEY"])

def cohere_rerank(query: str, candidates: list[Document], top_k: int = 3) -> list[Document]:
    docs_text = [doc.page_content for doc in candidates]
    
    response = co.rerank(
        query=query,
        documents=docs_text,
        top_n=top_k,
        model="rerank-multilingual-v3.0"  # 한국어 지원
    )
    
    return [candidates[r.index] for r in response.results]
```

---

## 맥락적 검색 (Contextual Retrieval)

청크에 맥락 설명을 추가해 검색 정확도를 높입니다. 원본 문서에서 해당 청크가 어떤 위치에 있는지 LLM이 설명을 생성합니다.

```python
from anthropic import Anthropic

client = Anthropic()

def add_context_to_chunk(full_document: str, chunk: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": f"""<document>
{full_document}
</document>

위 문서에서 아래 청크가 어떤 맥락에 있는지 짧게 설명하세요.
이 설명은 검색 인덱스에 사용됩니다. 2~3문장으로 간결하게.

<chunk>
{chunk}
</chunk>

맥락 설명:"""
        }]
    )
    context = response.content[0].text
    # 맥락 + 원본 청크를 결합해 인덱싱
    return f"{context}\n\n{chunk}"

# 전체 문서를 읽고 각 청크에 맥락 추가
with open("policy.pdf", "rb") as f:
    full_text = extract_text(f)

enhanced_chunks = []
for chunk in raw_chunks:
    enhanced = add_context_to_chunk(full_text, chunk.page_content)
    enhanced_chunks.append(Document(page_content=enhanced, metadata=chunk.metadata))
```

---

## 검색 파이프라인 조합

```python
class AdvancedRetriever:
    def __init__(self, vectorstore, chunks, top_k=5):
        self.vectorstore = vectorstore
        self.bm25 = BM25Retriever.from_documents(chunks)
        self.bm25.k = top_k * 2
        self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.top_k = top_k

    def retrieve(self, query: str) -> list[Document]:
        # 1. 하이브리드 검색으로 후보 확보
        vector_docs = self.vectorstore.similarity_search(query, k=self.top_k * 2)
        bm25_docs = self.bm25.invoke(query)
        
        # 중복 제거
        seen = set()
        candidates = []
        for doc in vector_docs + bm25_docs:
            key = doc.page_content[:100]
            if key not in seen:
                seen.add(key)
                candidates.append(doc)
        
        # 2. 크로스 인코더 리랭킹
        if len(candidates) > self.top_k:
            candidates = rerank_with_cross_encoder(query, candidates, self.top_k)
        
        return candidates[:self.top_k]
```

---

> 검색 품질은 벡터 검색 → 하이브리드 → 리랭킹 순으로 개선됩니다. 각 단계를 추가할 때마다 평가 지표로 실제 개선을 확인하세요.
