---
title: "18-3. ★확장 — 데모를 넘어 운영 가능한 형태로"
order: 183
tags: [capstone, production, docker, monitoring, ci-cd, evaluation]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 18-3. ★확장 — 데모를 넘어 운영 가능한 형태로

## 데모와 프로덕션의 차이

데모에서 작동한 코드가 프로덕션에서 실패하는 이유는 세 가지다.

| 구분 | 데모 | 프로덕션 |
|------|------|----------|
| 동시 요청 | 1건 | 수백 건 |
| 오류 처리 | 없음 | 필수 |
| 비용 | 무시 | 월 수백만원 가능 |

이 절에서는 캡스톤 프로젝트를 운영 가능한 수준으로 끌어올린다.

---

## 세션 관리와 멀티턴

```python
# agent/session.py
from dataclasses import dataclass, field
from collections import deque
import time
import json
from pathlib import Path

@dataclass
class ConversationSession:
    session_id: str
    customer_id: str | None
    created_at: float = field(default_factory=time.time)
    messages: deque = field(default_factory=lambda: deque(maxlen=20))
    total_tokens: int = 0
    tool_calls: list[str] = field(default_factory=list)
    
    def add_turn(self, role: str, content):
        self.messages.append({"role": role, "content": content})
    
    def get_history(self) -> list[dict]:
        return list(self.messages)
    
    def is_expired(self, ttl_seconds: int = 3600) -> bool:
        return time.time() - self.created_at > ttl_seconds
    
    def save(self, sessions_dir: str = "data/sessions"):
        path = Path(sessions_dir) / f"{self.session_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "session_id": self.session_id,
            "customer_id": self.customer_id,
            "created_at": self.created_at,
            "messages": list(self.messages),
            "total_tokens": self.total_tokens,
        }, ensure_ascii=False), encoding="utf-8")
    
    @classmethod
    def load(cls, session_id: str, sessions_dir: str = "data/sessions") -> "ConversationSession":
        path = Path(sessions_dir) / f"{session_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        session = cls(
            session_id=data["session_id"],
            customer_id=data["customer_id"],
            created_at=data["created_at"]
        )
        session.messages = deque(data["messages"], maxlen=20)
        session.total_tokens = data["total_tokens"]
        return session


class SessionStore:
    """인메모리 세션 저장소 (프로덕션에서는 Redis로 교체)."""
    
    def __init__(self):
        self._sessions: dict[str, ConversationSession] = {}
    
    def get_or_create(
        self, session_id: str, customer_id: str | None = None
    ) -> ConversationSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(
                session_id=session_id,
                customer_id=customer_id
            )
        return self._sessions[session_id]
    
    def cleanup_expired(self):
        expired = [
            sid for sid, s in self._sessions.items()
            if s.is_expired()
        ]
        for sid in expired:
            del self._sessions[sid]

session_store = SessionStore()
```

---

## 비용 추적과 토큰 제한

```python
# agent/cost_tracker.py
from dataclasses import dataclass, field
import anthropic
from threading import Lock

PRICING = {
    "claude-opus-4-8":   {"input": 15.0,  "output": 75.0},   # per 1M tokens
    "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25},
}

@dataclass
class UsageRecord:
    model: str
    input_tokens: int
    output_tokens: int
    session_id: str
    
    @property
    def cost_usd(self) -> float:
        price = PRICING.get(self.model, {"input": 3.0, "output": 15.0})
        return (
            self.input_tokens / 1_000_000 * price["input"] +
            self.output_tokens / 1_000_000 * price["output"]
        )


class CostTracker:
    def __init__(self, daily_limit_usd: float = 50.0):
        self._records: list[UsageRecord] = []
        self._lock = Lock()
        self.daily_limit_usd = daily_limit_usd
    
    def record(self, record: UsageRecord):
        with self._lock:
            self._records.append(record)
    
    def daily_cost(self) -> float:
        from datetime import date
        today = str(date.today())
        with self._lock:
            return sum(
                r.cost_usd for r in self._records
                # 실제로는 타임스탬프 비교
            )
    
    def check_limit(self) -> bool:
        """일일 한도 초과 여부."""
        return self.daily_cost() >= self.daily_limit_usd
    
    def summary(self) -> dict:
        with self._lock:
            total_cost = sum(r.cost_usd for r in self._records)
            total_tokens = sum(r.input_tokens + r.output_tokens for r in self._records)
            return {
                "total_requests": len(self._records),
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 4),
                "daily_limit_usd": self.daily_limit_usd
            }

cost_tracker = CostTracker()
```

---

## 속도 제한과 재시도

```python
# agent/resilient_orchestrator.py
import asyncio
import anthropic
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type
)
from agent.cost_tracker import cost_tracker, UsageRecord

class RateLimitError(Exception):
    pass


@retry(
    retry=retry_if_exception_type(anthropic.RateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4)
)
async def create_message_with_retry(client, **kwargs):
    """속도 제한 시 지수 백오프로 재시도."""
    return client.messages.create(**kwargs)


async def run_agent_with_limits(
    user_query: str,
    session_id: str,
    max_tokens_per_turn: int = 2048
):
    """비용 한도 및 속도 제한을 적용한 에이전트 실행."""
    
    # 일일 비용 한도 확인
    if cost_tracker.check_limit():
        return {
            "answer": "일시적으로 서비스가 제한되었습니다. 잠시 후 다시 시도해 주세요.",
            "error": "daily_limit_exceeded"
        }
    
    client = anthropic.Anthropic()
    
    try:
        response = await create_message_with_retry(
            client,
            model="claude-opus-4-8",
            max_tokens=max_tokens_per_turn,
            messages=[{"role": "user", "content": user_query}]
        )
        
        # 사용량 기록
        cost_tracker.record(UsageRecord(
            model="claude-opus-4-8",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            session_id=session_id
        ))
        
        return {"answer": response.content[0].text}
    
    except anthropic.APIError as e:
        return {"answer": f"서비스 오류가 발생했습니다. ({e.status_code})", "error": str(e)}
```

---

## Docker Compose 배포

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN addgroup --system app && adduser --system --group app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 데이터 디렉토리
RUN mkdir -p data/sessions data/policy_docs && chown -R app:app data

USER app

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
```

```yaml
# docker-compose.yml
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=sqlite:///data/shop.db
    volumes:
      - ./data:/app/data
    depends_on:
      - redis
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

volumes:
  redis_data:
```

---

## Prometheus 모니터링 연동

```python
# api/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

agent_requests_total = Counter(
    "agent_requests_total",
    "총 에이전트 요청 수",
    ["status"]  # success / error
)

agent_latency_seconds = Histogram(
    "agent_latency_seconds",
    "에이전트 응답 시간",
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
)

tool_calls_total = Counter(
    "tool_calls_total",
    "도구별 호출 횟수",
    ["tool_name"]
)

active_sessions = Gauge(
    "active_sessions",
    "현재 활성 세션 수"
)


# FastAPI 미들웨어로 자동 계측
from fastapi import Request
import time

async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    if request.url.path == "/chat":
        status = "success" if response.status_code == 200 else "error"
        agent_requests_total.labels(status=status).inc()
        agent_latency_seconds.observe(duration)
    
    return response
```

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'capstone-api'
    static_configs:
      - targets: ['api:8080']
    metrics_path: '/metrics'
```

---

## GitHub Actions CI/CD

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --tb=short
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -t capstone-api:${{ github.sha }} .
      - name: Push to registry
        run: |
          echo ${{ secrets.REGISTRY_TOKEN }} | docker login -u ${{ secrets.REGISTRY_USER }} --password-stdin
          docker push capstone-api:${{ github.sha }}

  eval:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run evaluation
        run: python evaluation/runner.py --output eval_results.json
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - name: Check pass rate
        run: |
          python -c "
          import json, sys
          results = json.load(open('eval_results.json'))
          pass_rate = sum(r['passed'] for r in results) / len(results)
          print(f'통과율: {pass_rate:.0%}')
          sys.exit(0 if pass_rate >= 0.8 else 1)
          "
      - uses: actions/upload-artifact@v4
        with:
          name: eval-results
          path: eval_results.json
```

---

## 프로덕션 체크리스트

```
아키텍처:
□ MCP 서버 도구 경계가 단일 책임 원칙을 따르는가
□ 에이전트 루프에 최대 반복 횟수가 설정되어 있는가
□ 멀티턴 세션이 메모리 누수 없이 관리되는가

신뢰성:
□ API 호출에 재시도 로직이 있는가
□ 타임아웃이 설정되어 있는가 (도구 호출 SLA)
□ 부분 실패 시 graceful degradation이 있는가

비용:
□ 토큰 사용량을 추적하는가
□ 일일 비용 한도가 설정되어 있는가
□ 복잡도에 따라 모델을 계층화했는가 (Haiku/Sonnet/Opus)

보안:
□ 환경변수로 API 키를 관리하는가
□ 도구 입력 검증이 있는가
□ PII 로깅 방지가 되어 있는가

관측성:
□ 요청별 도구 호출 로그가 남는가
□ Prometheus 메트릭이 수집되는가
□ 평가 파이프라인이 CI에 통합되어 있는가

배포:
□ Docker 이미지가 non-root 사용자로 실행되는가
□ 헬스체크 엔드포인트가 있는가
□ 롤백 절차가 문서화되어 있는가
```

---

## 18장 정리

이 캡스톤에서 구현한 스택 전체를 한 눈에 본다.

```
이커머스 고객 지원 에이전트
│
├── MCP Server (FastMCP)
│   ├── get_order_status    → SQLite 주문 DB
│   ├── search_products     → 상품 DB + 검색
│   ├── search_policy_docs  → Chroma RAG
│   └── check_coupon        → 프로모션 DB
│
├── Agent Orchestrator
│   ├── Anthropic Claude (ReAct 루프)
│   ├── 세션 관리 (멀티턴)
│   ├── 비용 추적 + 한도
│   └── 재시도 + 속도 제한
│
├── FastAPI
│   ├── POST /chat
│   ├── GET /health
│   └── GET /metrics
│
└── 인프라
    ├── Docker Compose
    ├── Prometheus 모니터링
    └── GitHub Actions CI/CD + 평가
```

> "운영 가능한 에이전트는 잘 동작하는 코드가 아니라 — 실패를 예측하고 비용을 측정하며 자동으로 검증되는 시스템이다."
