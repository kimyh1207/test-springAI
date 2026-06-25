---
title: "20-3. 운영 점검 체크리스트"
order: 203
tags: [operations, checklist, production-readiness, sre]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 20-3. 운영 점검 체크리스트

## 런칭 전 체크리스트

### 코드 품질

```
□ 모든 유닛 테스트 통과 (커버리지 ≥ 80%)
□ 통합 테스트 통과 (핵심 시나리오 5개 이상)
□ 에이전트 평가 통과율 ≥ 80%
□ 코드 린터 경고 없음 (ruff, eslint, checkstyle)
□ 의존성 취약점 스캔 완료 (pip-audit, npm audit)
```

### 보안

```
□ API 키 환경변수로 관리 (코드에 없음)
□ JWT 시크릿 32자 이상 랜덤 문자열
□ HTTPS 전용 (HTTP → HTTPS 리다이렉트)
□ CORS 허용 도메인 명시 (와일드카드 없음)
□ SQL 인젝션 방지 (파라미터화 쿼리)
□ PII 로그 미기록 확인
□ 도커 이미지 non-root 사용자
```

### 인프라

```
□ 헬스체크 엔드포인트 응답 정상
□ Redis 연결 정상
□ 벡터 DB 인덱스 로드 확인
□ 데이터베이스 마이그레이션 완료
□ 디스크 여유 공간 ≥ 30%
□ 메모리 사용률 ≤ 70%
```

### 모니터링

```
□ Prometheus 메트릭 수집 확인
□ Grafana 대시보드 패널 전체 데이터 표시
□ 알림 규칙 활성화 (지연·비용·오류율)
□ 로그 JSON 포맷 정상 출력
□ 에러 알림 수신 채널 테스트 (Slack, 이메일)
```

---

## 일일 점검 항목

```python
# scripts/daily_check.py
import httpx
import json
from datetime import date

def check_service_health(base_url: str) -> dict:
    results = {}
    
    # 1. 헬스체크
    try:
        r = httpx.get(f"{base_url}/health", timeout=5)
        results["health"] = r.status_code == 200
    except Exception:
        results["health"] = False
    
    # 2. 간단한 AI 응답 테스트
    try:
        r = httpx.post(f"{base_url}/chat",
            json={"query": "안녕", "session_id": "daily-check"},
            headers={"Authorization": f"Bearer {get_test_token()}"},
            timeout=15
        )
        results["ai_response"] = r.status_code == 200 and "answer" in r.json()
    except Exception:
        results["ai_response"] = False
    
    # 3. 비용 현황 확인
    try:
        r = httpx.get(f"{base_url}/admin/cost/today",
            headers={"Authorization": f"Bearer {get_admin_token()}"},
            timeout=5
        )
        data = r.json()
        results["daily_cost_usd"] = data.get("total_usd", -1)
        results["cost_ok"] = data.get("total_usd", 999) < 45  # $50 한도의 90%
    except Exception:
        results["cost_ok"] = None
    
    return results


if __name__ == "__main__":
    results = check_service_health("https://api.example.com")
    print(json.dumps(results, indent=2))
    
    # 문제 발견 시 알림
    failed = [k for k, v in results.items() if v is False]
    if failed:
        send_slack_alert(f"일일 점검 실패: {failed}")
```

---

## 장애 대응 런북

### LLM API 오류

```
증상: 503/429 오류 급증, 응답 시간 급등

1. 확인
   curl -X POST https://api.anthropic.com/v1/messages \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -d '{"model":"claude-haiku-4-5-20251001","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'
   
   상태 확인: https://status.anthropic.com

2. 즉시 조치
   - 캐시된 응답 비율 높이기 (TTL 연장)
   - 속도 제한 임계값 낮추기
   - 대기 중인 요청에 오류 메시지 반환

3. 복구 후
   - 원인 파악 및 문서화
   - 재시도 로직 검토
```

### 응답 시간 급등 (P95 > 5s)

```
증상: Grafana 지연 패널 빨간색

1. 확인
   - LLM API 지연인가? (ai_service 로그)
   - MCP 도구 지연인가? (tool_calls_total 비교)
   - DB 쿼리 지연인가? (DB slow query 로그)
   - RAG 검색 지연인가? (Chroma 응답 시간)

2. 원인별 조치
   LLM 지연: 더 빠른 모델로 임시 교체 (Opus → Haiku)
   DB 지연:  인덱스 확인, 연결 풀 크기 조정
   RAG 지연: Chroma 메모리 확인, 청크 수 줄이기

3. 근본 해결
   - 슬로우 쿼리 인덱스 추가
   - 모델 선택 로직 재검토
```

### 일일 비용 한도 도달

```
증상: cost_tracker 알림, 새 요청 차단됨

1. 즉시: 관리자에게 알림
2. 확인: 비정상 사용 패턴인가 (봇, 루프 등)
   SELECT user_id, COUNT(*) FROM audit_log
   WHERE created_at > NOW() - INTERVAL '1 hour'
   GROUP BY user_id ORDER BY COUNT(*) DESC LIMIT 10;
3. 대응
   - 비정상 사용자 차단
   - 일일 한도 임시 상향 (승인 필요)
   - 내일까지 서비스 제한 공지
```

---

## 모니터링 대시보드 읽는 법

```
패널 1: 요청 수 (requests/min)
  정상: 평일 피크 시간 기준선 ±30%
  이상: 갑작스런 0 또는 급등

패널 2: P95 응답 시간
  정상: < 3초
  경고: 3-5초
  위험: > 5초

패널 3: 오류율
  정상: < 1%
  경고: 1-5%
  위험: > 5%

패널 4: 일일 LLM 비용
  매 시간 $50/24 ≈ $2.1씩 소비가 정상 패턴
  갑작스런 급등은 루프 또는 이상 사용

패널 5: 캐시 히트율
  목표: > 20%
  낮으면: TTL 늘리기, 캐시 키 전략 검토

패널 6: 도구 호출 분포
  search_policy_docs 비율이 갑자기 낮으면 RAG 문제
```

---

## 성능 튜닝 포인트

```python
# 응답이 느릴 때 확인할 순서

# 1. 프로파일링
import cProfile
import pstats

with cProfile.Profile() as pr:
    result = asyncio.run(run_customer_support_agent("반품 방법"))

stats = pstats.Stats(pr)
stats.sort_stats('cumulative')
stats.print_stats(20)  # 상위 20개 함수


# 2. LLM 호출 횟수 최소화
# Bad: 같은 정보를 여러 도구 호출로 나눔
# → 주문 확인(1번) + 배송사 확인(2번) + 예상날짜(3번) = 3 LLM 턴

# Good: 도구 하나로 통합 반환
@mcp.tool()
def get_order_full_info(order_id: str) -> dict:
    """주문 + 배송 + 예상 도착 한 번에 반환."""
    ...


# 3. 청크 크기 최적화 (RAG)
# 청크가 너무 작으면: 컨텍스트 부족 → 재검색
# 청크가 너무 크면: 관련 없는 내용 포함 → 토큰 낭비
# 최적: 300-500 토큰, 오버랩 50-100 토큰
```

---

## 운영 자동화

```yaml
# 정기 작업 (cron)
jobs:
  # 매일 오전 9시: 전일 비용 리포트 슬랙 전송
  daily-cost-report:
    cron: "0 9 * * *"
    script: python scripts/cost_report.py --slack

  # 매주 월요일: 에이전트 평가 실행
  weekly-eval:
    cron: "0 10 * * 1"
    script: python evaluation/runner.py --notify-slack

  # 매일 오전 2시: 만료 세션 정리
  cleanup-sessions:
    cron: "0 2 * * *"
    script: python scripts/cleanup_sessions.py

  # 매월 1일: 벡터 DB 재인덱싱 (문서 업데이트 반영)
  monthly-reindex:
    cron: "0 3 1 * *"
    script: python data/build_index.py --full
```

---

## 20장 정리

```
구현 순서: 안에서 밖으로
  MCP 도구 → 에이전트 → FastAPI → Spring → React

테스트 계층:
  단위 테스트 (mock) → 통합 테스트 (실서버) → 평가 (LLM judge)

배포 파이프라인:
  테스트 → 평가 → 빌드 → 스테이징 → 승인 → 프로덕션

운영 핵심:
  일일 점검 자동화
  장애 런북 준비
  비용·지연·오류율 모니터링
```

> "운영은 배포 이후 시작된다 — 체크리스트 없이 야간 장애를 맞이하지 마라."
