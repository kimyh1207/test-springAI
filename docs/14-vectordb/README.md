---
title: "14장. Vector DB와 임베딩"
order: 14
tags: [vector-db, embedding, rag, similarity-search]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 14장. Vector DB와 임베딩

## 들어가며

LLM은 훈련 데이터 이후의 정보를 모릅니다. 내부 문서, 최신 데이터, 개인화된 정보를 모델에 주입하려면 RAG(Retrieval-Augmented Generation)가 필요합니다. 그 핵심이 임베딩과 Vector DB입니다.

텍스트를 숫자 벡터로 변환하고, 의미가 비슷한 것을 빠르게 찾는 기술입니다.

---

## 이 챕터에서 배울 것

- **[14-1. 임베딩의 의미와 거리 척도](./14-1-embedding.md)** — 텍스트가 어떻게 벡터가 되고, 유사도는 어떻게 계산하는가
- **[14-2. Vector DB 구조와 인덱싱](./14-2-vectordb-structure.md)** — HNSW 알고리즘, Pinecone·Chroma·pgvector 비교
- **[14-3. ★ 청킹·메타데이터 설계가 검색 품질을 좌우한다](./14-3-chunking.md)** — 잘 쪼개야 잘 찾는다

---

> 임베딩은 의미를 공간으로 변환합니다. "왕 - 남자 + 여자 = 여왕"이 벡터 연산으로 성립하는 이유입니다.

이 챕터를 마치면 문서를 임베딩하고 Vector DB에 저장해 의미 기반 검색과 RAG를 구현할 수 있습니다.
