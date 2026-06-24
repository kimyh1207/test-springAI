---
title: "14-1. 임베딩의 의미와 거리 척도"
order: 1
tags: [embedding, similarity, cosine, openai-embeddings]
status: draft
author: vivace
---

# 14-1. 임베딩의 의미와 거리 척도

임베딩은 텍스트(또는 이미지, 오디오)를 고차원 숫자 벡터로 변환합니다. 의미가 비슷한 텍스트는 벡터 공간에서 가까운 위치에 놓입니다.

---

## 임베딩이란

```
"강아지"  → [0.21, -0.54, 0.87, ..., 0.13]  # 1536차원 벡터
"고양이"  → [0.19, -0.51, 0.84, ..., 0.11]  # 비슷한 위치
"자동차"  → [-0.43, 0.82, -0.21, ..., 0.67]  # 먼 위치
```

단어의 의미가 수치로 인코딩됩니다. 키워드 검색과 달리 **의미 기반 검색**이 가능합니다.

키워드 검색의 한계:
```
질문: "어떻게 결제하나요?"
문서: "구매 방법 안내" → 키워드 불일치로 검색 실패
임베딩: 두 문장의 의미가 유사 → 검색 성공
```

---

## 임베딩 생성

```python
from openai import OpenAI
import numpy as np

client = OpenAI()

def embed(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",  # 1536차원, 저렴
        input=text
    )
    return response.data[0].embedding

# 단일 텍스트
vec = embed("Spring AI를 사용하면 LLM 통합이 쉬워진다")
print(f"차원: {len(vec)}")  # 1536

# 배치 처리 (비용 효율)
texts = ["문서1 내용", "문서2 내용", "문서3 내용"]
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=texts
)
vectors = [item.embedding for item in response.data]
```

### 오픈소스 임베딩 모델

API 비용 없이 로컬에서 실행합니다.

```python
from sentence_transformers import SentenceTransformer

# 한국어 지원 모델
model = SentenceTransformer("jhgan/ko-sroberta-multitask")

sentences = [
    "오늘 날씨가 좋네요",
    "오늘 기후가 화창합니다",  # 유사
    "주식 시장이 폭락했습니다"  # 다름
]

vectors = model.encode(sentences)
print(f"shape: {vectors.shape}")  # (3, 768)
```

---

## 거리 척도

### 코사인 유사도 (가장 많이 사용)

벡터 간 각도를 측정합니다. 크기가 달라도 방향이 같으면 유사합니다.

```python
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# 1에 가까울수록 유사, -1에 가까울수록 반대 의미
vec_dog = np.array(embed("강아지"))
vec_cat = np.array(embed("고양이"))
vec_car = np.array(embed("자동차"))

print(cosine_similarity(vec_dog, vec_cat))  # ~0.85 (유사)
print(cosine_similarity(vec_dog, vec_car))  # ~0.45 (다름)
```

### 유클리드 거리

두 벡터 사이의 직선 거리입니다.

```python
def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    return np.linalg.norm(a - b)
```

### 내적(Dot Product)

벡터가 정규화(L2 norm = 1)되어 있으면 코사인 유사도와 동일합니다. 연산이 빠릅니다.

---

## 실전: 의미 검색 구현

```python
import numpy as np
from openai import OpenAI

client = OpenAI()

def embed_batch(texts: list[str]) -> np.ndarray:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return np.array([item.embedding for item in response.data])

# 문서 데이터베이스
documents = [
    "환불 신청은 구매 후 30일 이내에 가능합니다.",
    "배송은 결제 완료 후 2~3일 이내 출발합니다.",
    "회원가입은 이메일 인증 후 완료됩니다.",
    "포인트는 구매금액의 1%가 적립됩니다.",
    "교환은 상품 수령 후 7일 이내 가능합니다.",
]

doc_vectors = embed_batch(documents)

def semantic_search(query: str, top_k: int = 3) -> list[tuple[str, float]]:
    query_vec = np.array(embed(query))
    
    # 모든 문서와 코사인 유사도 계산
    similarities = np.dot(doc_vectors, query_vec) / (
        np.linalg.norm(doc_vectors, axis=1) * np.linalg.norm(query_vec)
    )
    
    # 상위 k개 반환
    top_indices = np.argsort(similarities)[::-1][:top_k]
    return [(documents[i], float(similarities[i])) for i in top_indices]

results = semantic_search("물건을 돌려주고 싶어요")
for doc, score in results:
    print(f"{score:.3f}: {doc}")
# 0.812: 환불 신청은 구매 후 30일 이내에 가능합니다.
# 0.743: 교환은 상품 수령 후 7일 이내 가능합니다.
```

---

## 임베딩 모델 선택

| 모델 | 차원 | 특징 | 적합한 용도 |
|------|------|------|------------|
| text-embedding-3-small | 1536 | 저렴, 빠름 | 일반 텍스트 검색 |
| text-embedding-3-large | 3072 | 고성능 | 정확도가 중요한 경우 |
| ko-sroberta-multitask | 768 | 한국어 특화, 무료 | 한국어 도메인 |
| BAAI/bge-m3 | 1024 | 다국어, 무료 | 다국어 서비스 |

---

> 임베딩의 품질이 RAG 전체의 품질을 결정합니다. 도메인에 맞는 모델을 선택하는 것이 첫 번째 결정입니다.
