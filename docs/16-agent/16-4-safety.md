---
title: "16-4. ★확장 — 에이전트의 안전장치와 실패 복구"
order: 4
tags: [agent-safety, guardrails, human-in-the-loop, error-recovery]
status: draft
author: vivace
---

# 16-4. ★확장 — 에이전트의 안전장치와 실패 복구

에이전트는 자율적으로 행동합니다. 그만큼 잘못된 방향으로 갈 위험도 있습니다. 취소할 수 없는 행동을 하거나, 무한 루프에 빠지거나, 비용을 폭발적으로 쓸 수 있습니다. 안전장치가 필수입니다.

---

## 위험한 행동 분류

| 위험도 | 예시 | 대응 |
|--------|------|------|
| **낮음** | 읽기 전용 조회 | 자동 실행 허용 |
| **중간** | 이메일 발송, 주문 생성 | 확인 후 실행 |
| **높음** | 결제, 계정 삭제, 대량 수정 | 반드시 사람 승인 |

---

## Human-in-the-Loop — 사람 승인 게이트

위험한 행동 전에 사람의 확인을 받습니다.

```python
from enum import Enum

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

# 도구별 위험도 분류
TOOL_RISK = {
    "search_products": RiskLevel.LOW,
    "get_order_status": RiskLevel.LOW,
    "check_refund_eligibility": RiskLevel.LOW,
    "create_refund_request": RiskLevel.MEDIUM,
    "process_payment": RiskLevel.HIGH,
    "delete_account": RiskLevel.HIGH,
    "bulk_update_prices": RiskLevel.HIGH,
}

def requires_approval(tool_name: str, inputs: dict) -> bool:
    risk = TOOL_RISK.get(tool_name, RiskLevel.HIGH)
    return risk == RiskLevel.HIGH

def request_human_approval(tool_name: str, inputs: dict) -> bool:
    print(f"\n⚠️  승인 필요: {tool_name}")
    print(f"   입력: {inputs}")
    answer = input("   승인하시겠습니까? (y/n): ").strip().lower()
    return answer == 'y'

def safe_dispatch_tool(name: str, inputs: dict) -> str:
    if requires_approval(name, inputs):
        approved = request_human_approval(name, inputs)
        if not approved:
            return json.dumps({
                "status": "cancelled",
                "reason": "사용자가 승인하지 않았습니다"
            })
    return dispatch_tool(name, inputs)
```

---

## 가드레일 — 실행 전 검증

```python
class AgentGuardrails:
    def __init__(self):
        self.max_steps = 15
        self.max_cost_usd = 1.0
        self.step_count = 0
        self.estimated_cost = 0.0
        self.forbidden_actions = set()
    
    def check_step_limit(self) -> bool:
        self.step_count += 1
        if self.step_count > self.max_steps:
            raise RuntimeError(f"최대 단계 수({self.max_steps}) 초과")
        return True
    
    def check_cost(self, input_tokens: int, output_tokens: int):
        # claude-sonnet-4-6 기준 근사값
        cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000
        self.estimated_cost += cost
        if self.estimated_cost > self.max_cost_usd:
            raise RuntimeError(f"비용 한도(${self.max_cost_usd}) 초과")
    
    def check_forbidden(self, tool_name: str):
        if tool_name in self.forbidden_actions:
            raise ValueError(f"금지된 도구: {tool_name}")
    
    def validate_tool_call(self, tool_name: str, inputs: dict):
        self.check_step_limit()
        self.check_forbidden(tool_name)
        
        # 입력값 검증
        if tool_name == "create_refund_request":
            if "order_id" not in inputs:
                raise ValueError("order_id가 필요합니다")
```

---

## 루프 탐지 — 무한 반복 방지

```python
from collections import Counter

class LoopDetector:
    def __init__(self, window: int = 5, threshold: int = 3):
        self.window = window       # 최근 N개 행동 확인
        self.threshold = threshold  # 같은 행동이 N번 이상이면 루프
        self.recent_actions = []
    
    def record(self, tool_name: str, inputs: dict) -> bool:
        action_key = f"{tool_name}:{json.dumps(inputs, sort_keys=True)}"
        self.recent_actions.append(action_key)
        
        if len(self.recent_actions) > self.window:
            self.recent_actions.pop(0)
        
        counts = Counter(self.recent_actions)
        max_count = max(counts.values()) if counts else 0
        
        if max_count >= self.threshold:
            return True  # 루프 감지
        return False
```

---

## 오류 복구 전략

```python
class ResilientAgent:
    def __init__(self):
        self.guardrails = AgentGuardrails()
        self.loop_detector = LoopDetector()
        self.error_history = []
    
    def run_with_recovery(self, request: str) -> str:
        messages = [{"role": "user", "content": request}]
        
        for _ in range(self.guardrails.max_steps):
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=4096,
                    tools=TOOLS,
                    messages=messages
                )
                
                self.guardrails.check_cost(
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )
                
                if response.stop_reason == "end_turn":
                    return next(b.text for b in response.content if hasattr(b, "text"))
                
                if response.stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": response.content})
                    tool_results = []
                    
                    for block in response.content:
                        if block.type != "tool_use":
                            continue
                        
                        # 루프 탐지
                        if self.loop_detector.record(block.name, block.input):
                            return "반복 패턴 감지: 작업을 완료할 수 없습니다. 다시 시도해 주세요."
                        
                        try:
                            self.guardrails.validate_tool_call(block.name, block.input)
                            result = safe_dispatch_tool(block.name, block.input)
                        except ValueError as e:
                            result = json.dumps({"error": str(e)})
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })
                    
                    messages.append({"role": "user", "content": tool_results})
            
            except RuntimeError as e:
                return f"에이전트 중단: {e}"
        
        return "최대 단계 수에 도달했습니다."
```

---

## 에이전트 안전 체크리스트

```
설계 단계:
[ ] 취소 불가 행동(결제, 삭제)에 반드시 승인 게이트 추가
[ ] 최대 단계 수 제한 설정
[ ] 비용 한도 설정
[ ] 루프 탐지 로직 추가

운영 단계:
[ ] 모든 도구 호출을 로그로 기록
[ ] 에이전트 실행 타임아웃 설정
[ ] 실패 시 부분 완료 상태 저장
[ ] 비정상 종료 알림 설정

모니터링:
[ ] 평균 단계 수 추적 (비정상적으로 높으면 루프 의심)
[ ] 도구별 실패율 모니터링
[ ] 비용 일일 집계 및 이상값 알림
```

---

> 에이전트를 믿되 검증하세요. 자율성이 높을수록 안전장치도 견고해야 합니다. 취소할 수 없는 행동에는 항상 사람이 개입해야 합니다.
