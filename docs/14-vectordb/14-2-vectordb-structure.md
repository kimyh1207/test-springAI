---
title: "14-2. Vector DB 구조와 인덱싱"
order: 2
tags: [vector-db, hnsw, chroma, pgvector, pinecone]
status: draft
author: vivace
---

# 14-2. Vector DB 구조와 인덱싱

수백만 개의 벡터 중에서 가장 유사한 것을 빠르게 찾는 것이 Vector DB의 역할입니다. 단순 선형 검색은 너무 느립니다.

---

## 왜 특별한 인덱스가 필요한가

1백만 개의 1536차원 벡터에서 가장 유사한 것을 찾는다면:
- 선형 탐색: 매 쿼리마다 1백만 번 코사인 유사도 계산 → 느림
- HNSW 인덱스: 로그 복잡도로 근사 최근접 이웃 탐색 → 수십 ms

**ANN(Approximate Nearest Neighbor)**: 정확한 최근접 이웃 대신 충분히 가까운 것을 빠르게 찾습니다. 검색 품질을 조금 희생해 속도를 크게 높입니다.

---

## HNSW — 계층형 그래프 인덱스

HNSW(Hierarchical Navigable Small World)는 대부분의 Vector DB가 채택한 알고리즘입니다.

```
레이어 2 (희소): A ─────────────── E
레이어 1 (중간): A ─── B ─────── D ─ E
레이어 0 (밀집): A ─ B ─ C ─ D ─ E ─ F ─ G
```

검색 시 상위 레이어(넓은 이동)에서 시작해 하위 레이어(세밀한 탐색)로 내려오며 후보를 좁힙니다. 삽입/검색 모두 O(log n) 복잡도.

---

## Chroma — 로컬 개발용

설치가 간단하고 파일 기반 저장을 지원합니다. 개발·프로토타입에 적합합니다.

```bash
pip install chromadb openai
```

```python
import chromadb
from openai import OpenAI

client = OpenAI()
chroma = chromadb.PersistentClient(path="./chroma_db")

# 컬렉션 생성
collection = chroma.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}  # 코사인 유사도
)

# 문서 추가
documents = [
    {"id": "doc1", "text": "환불 신청은 구매 후 30일 이내에 가능합니다.", "category": "refund"},
    {"id": "doc2", "text": "배송은 결제 완료 후 2~3일 이내 출발합니다.", "category": "shipping"},
    {"id": "doc3", "text": "교환은 상품 수령 후 7일 이내 가능합니다.", "category": "exchange"},
]

# 임베딩 생성 (배치)
texts = [d["text"] for d in documents]
embeddings = client.embeddings.create(
    model="text-embedding-3-small",
    input=texts
).data

collection.add(
    ids=[d["id"] for d in documents],
    documents=texts,
    embeddings=[e.embedding for e in embeddings],
    metadatas=[{"category": d["category"]} for d in documents]
)

# 검색
query = "물건 반품하려고 해요"
query_embedding = client.embeddings.create(
    model="text-embedding-3-small",
    input=[query]
).data[0].embedding

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=2,
    where={"category": "refund"}  # 메타데이터 필터링
)

for doc, distance in zip(results["documents"][0], results["distances"][0]):
    print(f"거리: {distance:.4f} | {doc}")
```

---

## pgvector — PostgreSQL 확장

기존 PostgreSQL에 벡터 검색을 추가합니다. 이미 PostgreSQL을 쓴다면 별도 인프라 없이 Vector DB를 도입할 수 있습니다.

```sql
-- PostgreSQL에 pgvector 설치
CREATE EXTENSION IF NOT EXISTS vector;

-- 테이블 생성
CREATE TABLE documents (
    id          SERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    category    VARCHAR(50),
    embedding   VECTOR(1536),  -- text-embedding-3-small 차원
    created_at  TIMESTAMP DEFAULT NOW()
);

-- HNSW 인덱스 생성
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 유사 문서 검색
SELECT content, category,
       1 - (embedding <=> '[0.21, -0.54, ...]'::vector) AS similarity
FROM documents
ORDER BY embedding <=> '[0.21, -0.54, ...]'::vector
LIMIT 5;

-- 메타데이터 필터 + 벡터 검색
SELECT content,
       1 - (embedding <=> $1::vector) AS similarity
FROM documents
WHERE category = 'refund'
ORDER BY embedding <=> $1::vector
LIMIT 3;
```

```python
# Python에서 pgvector 사용
import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

conn = psycopg2.connect("postgresql://user:pw@localhost/db")
register_vector(conn)
cur = conn.cursor()

# 문서 삽입
embedding = np.array(embed("환불 정책 안내"))
cur.execute(
    "INSERT INTO documents (content, category, embedding) VALUES (%s, %s, %s)",
    ("환불 신청은 구매 후 30일 이내에 가능합니다.", "refund", embedding)
)

# 유사도 검색
query_vec = np.array(embed("반품 방법"))
cur.execute("""
    SELECT content, 1 - (embedding <=> %s) AS similarity
    FROM documents
    ORDER BY embedding <=> %s
    LIMIT 3
""", (query_vec, query_vec))

for row in cur.fetchall():
    print(f"{row[1]:.3f}: {row[0]}")
```

---

## Vector DB 선택 가이드

| 요구사항 | 선택 |
|---------|------|
| 빠른 프로토타입, 로컬 개발 | Chroma |
| 이미 PostgreSQL 사용 중 | pgvector |
| 대규모(수억 벡터), 관리형 서비스 | Pinecone |
| 오픈소스, 자체 호스팅 대규모 | Weaviate, Qdrant |
| Spring AI 통합 | pgvector (Spring AI VectorStore 지원) |

---

## Spring AI + pgvector

```yaml
# application.yml
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/mydb
  ai:
    vectorstore:
      pgvector:
        index-type: hnsw
        distance-type: cosine_distance
        dimensions: 1536
```

```java
@Service
@RequiredArgsConstructor
public class DocumentService {

    private final VectorStore vectorStore;

    public void addDocument(String content, Map<String, Object> metadata) {
        Document doc = new Document(content, metadata);
        vectorStore.add(List.of(doc));
    }

    public List<Document> search(String query, int topK) {
        return vectorStore.similaritySearch(
            SearchRequest.query(query)
                .withTopK(topK)
                .withSimilarityThreshold(0.7)
        );
    }
}
```

---

> Vector DB는 "의미 기반 검색"을 현실로 만드는 인프라입니다. 키워드가 달라도 뜻이 같으면 찾아냅니다.
