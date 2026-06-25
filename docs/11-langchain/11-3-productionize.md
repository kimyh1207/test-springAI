---
title: "11-3. ★확장 — 프로토타입을 안정적 서비스로 다듬기"
order: 3
tags: [langserve, langsmith, production, observability]
status: draft
author: vivace
---

# 11-3. ★확장 — 프로토타입을 안정적 서비스로 다듬기

LangChain으로 빠르게 만든 프로토타입을 프로덕션으로 가져가려면 API 서빙, 관찰 가능성, 비용 관리가 필요합니다.

---

## LangServe — 체인을 REST API로

LangChain 체인을 FastAPI 엔드포인트로 자동 변환합니다.

```bash
pip install langserve[all] fastapi uvicorn
```

```python
# app.py
from fastapi import FastAPI
from langserve import add_routes
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

app = FastAPI(title="AI Review Service")

llm = ChatOpenAI(model="gpt-4o", temperature=0)

review_chain = (
    ChatPromptTemplate.from_template(
        "다음 리뷰를 분석하고 긍정/부정/중립으로 분류하세요:\n{review}"
    )
    | llm
    | StrOutputParser()
)

# /review/invoke, /review/stream, /review/batch 자동 생성
add_routes(app, review_chain, path="/review")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

```bash
uvicorn app:app --reload
```

자동 생성되는 엔드포인트:
- `POST /review/invoke` — 단일 요청
- `POST /review/batch` — 배치 요청
- `POST /review/stream` — 스트리밍
- `GET /review/playground` — 브라우저에서 직접 테스트

### Spring Boot에서 호출

```java
@Service
public class ReviewAnalysisService {

    private final RestTemplate restTemplate;
    private final String langserveUrl = "http://ai-service:8000";

    public String analyzeReview(String review) {
        Map<String, Object> body = Map.of(
            "input", Map.of("review", review)
        );
        
        Map response = restTemplate.postForObject(
            langserveUrl + "/review/invoke",
            body,
            Map.class
        );
        
        return (String) response.get("output");
    }
}
```

---

## LangSmith — 관찰 가능성

체인의 모든 단계를 추적하고 디버깅합니다.

```bash
pip install langsmith
```

```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "ls__..."
os.environ["LANGCHAIN_PROJECT"] = "review-service"

# 이후 모든 체인 호출이 자동으로 LangSmith에 기록됨
result = review_chain.invoke({"review": "배송 빠르고 좋아요"})
```

LangSmith 대시보드에서 확인할 수 있는 것들:
- 각 체인 단계의 입력/출력
- 소요 시간
- 토큰 사용량과 비용
- 오류 추적

---

## 비용 추적

```python
from langchain_community.callbacks import get_openai_callback

with get_openai_callback() as cb:
    result = review_chain.invoke({"review": "테스트 리뷰입니다."})
    print(f"총 토큰: {cb.total_tokens}")
    print(f"프롬프트 토큰: {cb.prompt_tokens}")
    print(f"응답 토큰: {cb.completion_tokens}")
    print(f"비용: ${cb.total_cost:.6f}")
```

---

## 에러 핸들링과 Fallback

```python
from langchain_core.runnables import RunnableLambda

def handle_error(error: Exception) -> str:
    print(f"AI 서비스 오류: {error}")
    return "현재 분석 서비스를 이용할 수 없습니다. 잠시 후 다시 시도해주세요."

safe_chain = review_chain.with_fallbacks(
    [RunnableLambda(lambda _: "서비스 일시 중단")]
)

# 또는 다른 모델로 fallback
from langchain_anthropic import ChatAnthropic

fallback_chain = (
    ChatPromptTemplate.from_template("리뷰 분석: {review}")
    | ChatAnthropic(model="claude-haiku-4-5-20251001")
    | StrOutputParser()
)

resilient_chain = review_chain.with_fallbacks([fallback_chain])
```

---

## 응답 캐싱

```python
from langchain_core.globals import set_llm_cache
from langchain_community.cache import RedisCache
import redis

# Redis 캐싱 설정 — 동일 프롬프트는 API 호출 없이 캐시에서 반환
set_llm_cache(RedisCache(redis_=redis.Redis(host="localhost", port=6379)))

# 첫 번째 호출: API 실제 호출
result1 = review_chain.invoke({"review": "좋아요"})

# 두 번째 호출: 캐시에서 반환 (비용 0)
result2 = review_chain.invoke({"review": "좋아요"})
```

---

## Docker 배포

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
services:
  ai-service:
    build: ./ai-service
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY}
      - LANGCHAIN_TRACING_V2=true
    depends_on:
      - redis

  spring-backend:
    build: ./backend
    ports:
      - "8080:8080"
    environment:
      - AI_SERVICE_URL=http://ai-service:8000
    depends_on:
      - ai-service

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## Spring AI vs LangChain 선택 기준

| 상황 | 선택 |
|------|------|
| 기존 Spring Boot 팀 | Spring AI |
| Python ML 팀이 AI 서비스 개발 | LangChain |
| 빠른 프로토타입 | LangChain |
| 엔터프라이즈 Java 서비스에 LLM 추가 | Spring AI |
| 복잡한 멀티에이전트 시스템 | LangChain + LangGraph |
| 팀이 두 기술 모두 안다면 | AI 서비스는 LangChain, 비즈니스 로직은 Spring |

---

> 프로토타입을 만드는 것과 운영하는 것은 다른 문제입니다. 서빙, 추적, 캐싱, 장애 대응. 이 네 가지가 갖춰져야 서비스입니다.
