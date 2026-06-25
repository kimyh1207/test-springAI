---
title: "19-1. 프론트(UI) + 백엔드(Spring) + AI(RAG·Agent) 아키텍처 통합"
order: 191
tags: [architecture, fullstack, spring-ai, react, rag, agent]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 19-1. 프론트(UI) + 백엔드(Spring) + AI(RAG·Agent) 아키텍처 통합

## 전체 시스템 그림

풀스택 AI 서비스는 세 레이어가 명확히 나뉜다.

```
┌──────────────────────────────────────────────────────────────────┐
│                        클라이언트 레이어                           │
│                                                                  │
│   React / Next.js                                                │
│   - 채팅 UI (SSE 스트리밍)                                        │
│   - 대시보드 (메트릭 시각화)                                       │
│   - 인증 (JWT 토큰 관리)                                          │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTPS / REST / SSE
┌───────────────────────────▼──────────────────────────────────────┐
│                        API 게이트웨이 레이어                        │
│                                                                  │
│   Spring Boot (API Gateway 역할)                                  │
│   - 인증/인가 (Spring Security + JWT)                             │
│   - 요청 라우팅 (/api/chat → AI 서비스)                            │
│   - 비용 제한 (Redis rate limiting)                               │
│   - 응답 캐싱 (Redis)                                             │
└──────┬────────────────────┬───────────────────────────────────────┘
       │                    │
       │ REST               │ REST / gRPC
┌──────▼──────┐    ┌────────▼────────────────────────────────────┐
│  비즈니스    │    │              AI 레이어                       │
│  서비스      │    │                                             │
│  (Spring)   │    │  FastAPI / Python                           │
│  - 주문 DB  │    │  - RAG 파이프라인 (LangChain)                │
│  - 상품 DB  │◄───│  - Agent (MCP + Anthropic)                  │
│  - 사용자   │    │  - 벡터 DB (Chroma / pgvector)               │
└─────────────┘    └─────────────────────────────────────────────┘
```

---

## 계층별 책임

### 프론트엔드 (React/Next.js)

```typescript
// 채팅 UI — SSE 스트리밍 수신
async function streamChat(query: string, sessionId: string) {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getToken()}`
    },
    body: JSON.stringify({ query, session_id: sessionId })
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        if (data.type === 'token') {
          appendToken(data.content);      // 토큰 단위로 화면 업데이트
        } else if (data.type === 'tool_call') {
          showToolCallIndicator(data.tool); // "검색 중..." 표시
        } else if (data.type === 'done') {
          finalizeMessage(data.citations); // 인용 출처 표시
        }
      }
    }
  }
}
```

### 백엔드 게이트웨이 (Spring Boot)

```java
// ChatController.java
@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;
    private final RateLimiter rateLimiter;

    // SSE 스트리밍 엔드포인트
    @PostMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> streamChat(
            @RequestBody ChatRequest request,
            @AuthenticationPrincipal UserDetails user) {
        
        // 속도 제한 확인
        if (!rateLimiter.tryAcquire(user.getUsername())) {
            return Flux.error(new TooManyRequestsException("요청 한도 초과"));
        }

        return chatService.streamResponse(request, user.getUsername())
                .map(chunk -> ServerSentEvent.builder(chunk)
                        .event("message")
                        .build());
    }

    // 단건 요청 엔드포인트
    @PostMapping
    public Mono<ChatResponse> chat(
            @RequestBody ChatRequest request,
            @AuthenticationPrincipal UserDetails user) {
        return chatService.getResponse(request, user.getUsername());
    }
}
```

```java
// ChatService.java — AI 레이어 호출
@Service
@RequiredArgsConstructor
public class ChatService {

    private final WebClient aiServiceClient;
    private final ResponseCache responseCache;

    public Flux<String> streamResponse(ChatRequest request, String userId) {
        // 캐시 확인 (동일 질문 반복 시)
        String cacheKey = DigestUtils.md5Hex(request.getQuery());
        String cached = responseCache.get(cacheKey);
        if (cached != null) {
            return Flux.just(cached);
        }

        return aiServiceClient.post()
                .uri("/chat/stream")
                .bodyValue(Map.of(
                        "query", request.getQuery(),
                        "session_id", request.getSessionId(),
                        "user_id", userId
                ))
                .retrieve()
                .bodyToFlux(String.class)
                .doOnComplete(() -> {
                    // 스트림 완료 후 캐시 저장은 별도 엔드포인트
                });
    }
}
```

### AI 레이어 (FastAPI + Python)

```python
# ai_service/main.py
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from agent.orchestrator import CustomerSupportAgent
from rag.pipeline import RAGPipeline
import json

app = FastAPI(title="AI Service")

rag_pipeline = RAGPipeline()
agent = CustomerSupportAgent()


@app.post("/chat/stream")
async def chat_stream(request: dict):
    """Spring Boot가 호출하는 스트리밍 AI 엔드포인트."""
    
    async def event_generator():
        async for event in agent.stream(
            query=request["query"],
            session_id=request["session_id"],
            user_id=request["user_id"]
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@app.post("/rag/query")
async def rag_query(request: dict):
    """순수 RAG 조회 (에이전트 없이)."""
    result = await rag_pipeline.query(
        query=request["query"],
        doc_type=request.get("doc_type")
    )
    return result
```

---

## 서비스 간 통신 설계

```
┌──────────────────────────────────────────────────────────────┐
│                    통신 패턴 선택 기준                          │
│                                                              │
│  동기 REST:                                                  │
│  - 즉시 응답이 필요한 단건 조회                                 │
│  - 예: 주문 상태, 쿠폰 확인                                    │
│                                                              │
│  SSE (Server-Sent Events):                                   │
│  - LLM 토큰 스트리밍                                          │
│  - 에이전트 사고 과정 실시간 전달                               │
│                                                              │
│  비동기 메시지 (Kafka):                                        │
│  - 배치 처리 (대량 문서 인덱싱)                                 │
│  - 이벤트 기록 (사용량 로그)                                    │
└──────────────────────────────────────────────────────────────┘
```

```yaml
# application.yml — AI 서비스 연결 설정
ai:
  service:
    base-url: http://ai-service:8000
    timeout: 30s
    connect-timeout: 5s
  
  rate-limit:
    requests-per-minute: 20
    requests-per-day: 500
    
  cache:
    ttl-seconds: 300
    max-size: 1000
```

---

## 공유 데이터 모델

Spring과 Python이 공통으로 사용하는 데이터 구조다.

```java
// Spring — ChatRequest.java
public record ChatRequest(
    @NotBlank String query,
    String sessionId,
    String docType  // nullable
) {}

// Spring — ChatResponse.java
public record ChatResponse(
    String answer,
    List<String> toolsCalled,
    List<Citation> citations,
    long responseTimeMs
) {}

public record Citation(
    String source,
    String excerpt
) {}
```

```python
# Python — schemas.py
from pydantic import BaseModel

class ChatRequest(BaseModel):
    query: str
    session_id: str
    user_id: str
    doc_type: str | None = None

class Citation(BaseModel):
    source: str
    excerpt: str

class ChatResponse(BaseModel):
    answer: str
    tools_called: list[str]
    citations: list[Citation]
    response_time_ms: float
```

두 언어에서 필드명(snake_case)을 통일하고, Spring에서는 `@JsonNaming(SnakeCaseStrategy.class)` 또는 `spring.jackson.property-naming-strategy=SNAKE_CASE`를 설정한다.

---

## 기술 스택 선택 이유

| 레이어 | 선택 | 이유 |
|--------|------|------|
| 프론트엔드 | React + Vite | SSE 스트리밍, 컴포넌트 재사용 |
| API 게이트웨이 | Spring Boot | 인증/인가 생태계, Java 팀 익숙 |
| AI 레이어 | FastAPI | LangChain/MCP SDK가 Python 우선 |
| 벡터 DB | pgvector | 기존 PostgreSQL 인프라 재활용 |
| 캐시 | Redis | 세션·속도 제한·응답 캐시 통합 |
| 메시지 | Kafka | 배치 인덱싱 비동기 처리 |

> "좋은 아키텍처는 선택을 늦춘다 — 계층 경계가 명확하면 AI 모델을 바꿔도 프론트가 모른다."
