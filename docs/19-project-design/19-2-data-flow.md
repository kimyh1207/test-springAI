---
title: "19-2. 데이터 흐름과 책임 분리"
order: 192
tags: [data-flow, separation-of-concerns, ddd, api-design]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 19-2. 데이터 흐름과 책임 분리

## 요청 흐름 추적

사용자가 "반품하고 싶어"라고 입력했을 때 시스템이 어떻게 처리하는지 단계별로 따라간다.

```
1. 사용자 입력
   브라우저 → POST /api/chat
              { query: "반품하고 싶어", session_id: "S123" }

2. Spring Boot — 인증/검증/라우팅
   - JWT 검증: 유효한 사용자인가
   - 속도 제한: Redis에서 카운터 확인
   - 요청 로깅: 감사 로그 기록
   - AI 서비스로 포워딩

3. FastAPI AI 레이어 — 에이전트 실행
   a. 세션 히스토리 로드
   b. Claude에 query + tools 전달
   c. Claude: "search_policy_docs 호출 필요" 결정
   d. MCP 서버 → search_policy_docs(query="반품")
   e. Chroma에서 반품 정책 청크 검색
   f. Claude: 결과 기반 답변 생성
   g. SSE 스트림으로 토큰 전송

4. Spring Boot — 응답 변환
   - SSE를 그대로 클라이언트에 relay
   - 응답 완료 후 캐시 저장
   - 사용량 메트릭 기록

5. 브라우저 — UI 업데이트
   - 토큰 단위 화면 렌더링
   - 인용 출처 표시
   - 세션 ID 유지
```

---

## 책임 분리 원칙

각 컴포넌트가 "무엇만" 책임지는지 명확히 한다.

```
Spring Boot가 책임지는 것:
  ✓ 인증/인가
  ✓ 속도 제한
  ✓ 요청/응답 로깅
  ✓ 캐시 (동일 쿼리 중복 방지)
  ✗ AI 로직 (하지 않음)
  ✗ 벡터 검색 (하지 않음)

FastAPI AI 서비스가 책임지는 것:
  ✓ 에이전트 오케스트레이션
  ✓ RAG 파이프라인
  ✓ MCP 도구 호출
  ✓ 세션 히스토리
  ✗ 인증 (Spring에 위임)
  ✗ DB 직접 접근 (MCP 도구 경유)

MCP 서버가 책임지는 것:
  ✓ 외부 시스템 연동 (DB, API)
  ✓ 도구 입력 검증
  ✓ 결과 포맷팅
  ✗ AI 의사결정 (에이전트에 위임)
```

---

## 레이어 간 데이터 변환

```
브라우저           Spring Boot          FastAPI            MCP Server
─────────          ──────────          ───────            ──────────
ChatRequest   →    AIRequest      →    AgentInput    →   ToolInput
{query,           {query,             {query,            {order_id}
 session_id}       session_id,         session_id,
                   user_id,            history,
                   rate_limit_ok}      tools[]}

              ←    ChatResponse   ←    AgentOutput   ←   ToolResult
{answer,          {answer,            {answer,           {status,
 citations}        citations,          tool_results,       eta,
                   cached: false}      tokens_used}        items[]}
```

변환은 각 레이어 경계에서만 일어난다. Spring이 MCP의 응답 구조를 알면 결합도가 높아진다.

---

## 세션 데이터 흐름

```python
# 세션은 AI 레이어에서만 관리한다
# Spring Boot는 session_id를 전달할 뿐, 내용은 모른다

class SessionManager:
    """세션 저장소 — Redis 또는 인메모리."""
    
    def __init__(self, redis_client=None):
        self._store = redis_client or {}  # 로컬 개발은 dict
    
    def get_history(self, session_id: str) -> list[dict]:
        if hasattr(self._store, 'get'):  # Redis
            data = self._store.get(f"session:{session_id}")
            return json.loads(data) if data else []
        return self._store.get(session_id, [])
    
    def append(self, session_id: str, role: str, content):
        history = self.get_history(session_id)
        history.append({"role": role, "content": content})
        
        # 최대 20턴 유지
        if len(history) > 40:  # (user + assistant) × 20
            history = history[-40:]
        
        if hasattr(self._store, 'setex'):  # Redis
            self._store.setex(
                f"session:{session_id}",
                3600,  # 1시간 TTL
                json.dumps(history, ensure_ascii=False)
            )
        else:
            self._store[session_id] = history
```

---

## 이벤트 기록 (감사 로그)

```java
// Spring Boot — AuditLogFilter.java
@Component
public class AuditLogFilter extends OncePerRequestFilter {
    
    private final AuditLogRepository auditLog;
    
    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain chain) throws ServletException, IOException {
        
        long start = System.currentTimeMillis();
        chain.doFilter(request, response);
        long duration = System.currentTimeMillis() - start;
        
        if (request.getRequestURI().startsWith("/api/chat")) {
            auditLog.save(AuditEntry.builder()
                    .userId(getUserId(request))
                    .endpoint(request.getRequestURI())
                    .statusCode(response.getStatus())
                    .durationMs(duration)
                    .timestamp(Instant.now())
                    .build());
        }
    }
}
```

```python
# FastAPI — AI 사용량 기록
import structlog

log = structlog.get_logger()

async def log_agent_run(
    session_id: str,
    user_id: str,
    query: str,
    tools_called: list[str],
    tokens_used: int,
    duration_ms: float
):
    log.info(
        "agent_run_completed",
        session_id=session_id,
        user_id=user_id,
        query_length=len(query),
        tools=tools_called,
        tokens=tokens_used,
        duration_ms=round(duration_ms, 1)
    )
    # PII 방지: query 원문은 로깅하지 않는다
```

---

## 비동기 인덱싱 파이프라인

문서 업데이트는 동기 요청 경로 바깥에서 처리한다.

```
[관리자]
   │
   │ POST /admin/index
   ▼
[Spring Boot]
   │ Kafka produce
   │ topic: document-indexing
   ▼
[Kafka]
   │
   ▼
[Python Consumer]
   │
   ├── 문서 로드
   ├── 청크 분할
   ├── 임베딩 생성
   └── Chroma upsert
```

```python
# indexing/consumer.py
from kafka import KafkaConsumer
from rag.indexer import DocumentIndexer
import json

consumer = KafkaConsumer(
    "document-indexing",
    bootstrap_servers=["kafka:9092"],
    value_deserializer=lambda m: json.loads(m.decode())
)

indexer = DocumentIndexer()

for message in consumer:
    event = message.value
    doc_path = event["path"]
    doc_type = event["type"]
    
    print(f"인덱싱: {doc_path}")
    indexer.index_file(doc_path, doc_type=doc_type)
    print(f"완료: {doc_path}")
```

---

## 오류 응답 표준화

```python
# FastAPI 오류 응답 형식 통일
from fastapi.responses import JSONResponse
from fastapi import Request

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, ValueError):
        return JSONResponse(status_code=400, content={
            "error": "invalid_request",
            "message": str(exc)
        })
    if isinstance(exc, TimeoutError):
        return JSONResponse(status_code=504, content={
            "error": "ai_timeout",
            "message": "AI 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요."
        })
    return JSONResponse(status_code=500, content={
        "error": "internal_error",
        "message": "서버 오류가 발생했습니다."
    })
```

```java
// Spring Boot 오류 응답 형식 통일
@RestControllerAdvice
public class GlobalExceptionHandler {
    
    @ExceptionHandler(TooManyRequestsException.class)
    public ResponseEntity<ErrorResponse> handleRateLimit(TooManyRequestsException e) {
        return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS)
                .body(new ErrorResponse("rate_limit_exceeded", e.getMessage()));
    }
    
    @ExceptionHandler(WebClientResponseException.class)
    public ResponseEntity<ErrorResponse> handleAIServiceError(WebClientResponseException e) {
        return ResponseEntity.status(e.getStatusCode())
                .body(new ErrorResponse("ai_service_error", "AI 서비스 오류"));
    }
    
    public record ErrorResponse(String error, String message) {}
}
```

> "데이터 흐름이 명확하면 버그 위치가 보인다 — 어느 레이어가 틀렸는지 로그 한 줄로 파악된다."
