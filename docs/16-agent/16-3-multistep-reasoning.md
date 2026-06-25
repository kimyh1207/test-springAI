---
title: "16-3. 멀티스텝 추론과 상태 관리"
order: 3
tags: [multistep, state-management, agent, planning]
status: draft
author: vivace
---

# 16-3. 멀티스텝 추론과 상태 관리

단일 도구 호출로 끝나는 작업은 단순합니다. 실제 업무는 여러 단계가 얽혀 있고, 이전 단계의 결과가 다음 단계에 영향을 줍니다.

---

## 멀티스텝 에이전트의 상태

에이전트가 작업을 수행하면서 추적해야 하는 것들입니다.

```python
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime

@dataclass
class AgentState:
    task: str                               # 원래 목표
    steps: list[dict] = field(default_factory=list)  # 수행한 단계 기록
    context: dict[str, Any] = field(default_factory=dict)  # 수집된 정보
    status: str = "running"                 # running / completed / failed
    started_at: datetime = field(default_factory=datetime.now)
    
    def add_step(self, action: str, result: Any):
        self.steps.append({
            "step": len(self.steps) + 1,
            "action": action,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    def to_summary(self) -> str:
        lines = [f"작업: {self.task}", f"상태: {self.status}", "수행 단계:"]
        for s in self.steps:
            lines.append(f"  {s['step']}. {s['action']} → {str(s['result'])[:100]}")
        return "\n".join(lines)
```

---

## 완성된 멀티스텝 에이전트

```python
from anthropic import Anthropic
import json

client = Anthropic()

SYSTEM_PROMPT = """당신은 이커머스 고객 지원 에이전트입니다.

작업 처리 원칙:
1. 환불 전 반드시 check_refund_eligibility를 먼저 호출하세요
2. 한 번에 하나씩 확인하고 진행하세요
3. 고객에게 각 단계를 명확히 설명하세요
4. 불가능한 요청은 이유를 설명하고 대안을 제시하세요"""

class CustomerServiceAgent:
    def __init__(self):
        self.tools = TOOLS  # 앞서 정의한 도구 목록
    
    def run(self, customer_request: str) -> str:
        state = AgentState(task=customer_request)
        messages = [{"role": "user", "content": customer_request}]
        
        max_steps = 10
        for step_num in range(max_steps):
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=self.tools,
                messages=messages
            )
            
            # 완료
            if response.stop_reason == "end_turn":
                state.status = "completed"
                final_answer = next(
                    (b.text for b in response.content if hasattr(b, "text")), ""
                )
                return final_answer
            
            # 도구 호출
            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                
                for block in response.content:
                    if block.type == "tool_use":
                        result = dispatch_tool(block.name, block.input)
                        state.add_step(
                            action=f"{block.name}({json.dumps(block.input, ensure_ascii=False)})",
                            result=result
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })
                
                messages.append({"role": "user", "content": tool_results})
            else:
                break
        
        state.status = "failed"
        return f"작업을 완료하지 못했습니다. {state.to_summary()}"

# 사용
agent = CustomerServiceAgent()
result = agent.run("ORD-001 주문을 환불하고 싶어요. 상품이 불량입니다.")
print(result)
```

---

## 체크포인트 — 긴 작업의 중단 지점

작업이 길어지면 중간에 저장하고 재개할 수 있어야 합니다.

```python
import json
from pathlib import Path

class CheckpointedAgent:
    def __init__(self, checkpoint_dir: str = ".checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
    
    def save_checkpoint(self, task_id: str, state: AgentState, messages: list):
        checkpoint = {
            "state": {
                "task": state.task,
                "steps": state.steps,
                "context": state.context,
                "status": state.status
            },
            "messages": messages
        }
        path = self.checkpoint_dir / f"{task_id}.json"
        with open(path, "w") as f:
            json.dump(checkpoint, f, ensure_ascii=False, default=str)
    
    def load_checkpoint(self, task_id: str) -> tuple[AgentState, list] | None:
        path = self.checkpoint_dir / f"{task_id}.json"
        if not path.exists():
            return None
        
        with open(path) as f:
            data = json.load(f)
        
        state = AgentState(task=data["state"]["task"])
        state.steps = data["state"]["steps"]
        state.context = data["state"]["context"]
        state.status = data["state"]["status"]
        
        return state, data["messages"]
    
    def run_with_checkpoint(self, task_id: str, request: str) -> str:
        # 체크포인트가 있으면 재개
        checkpoint = self.load_checkpoint(task_id)
        if checkpoint:
            state, messages = checkpoint
            print(f"체크포인트 재개: {len(state.steps)}단계까지 완료")
        else:
            state = AgentState(task=request)
            messages = [{"role": "user", "content": request}]
        
        # 이후 에이전트 루프 실행 (생략)
        return "..."
```

---

## 서브에이전트 패턴 — 복잡한 작업 분해

큰 작업을 작은 전문 에이전트에게 위임합니다.

```python
class OrchestratorAgent:
    """복잡한 작업을 분해하고 서브에이전트에게 위임"""
    
    def __init__(self):
        self.sub_agents = {
            "research": ResearchAgent(),
            "analysis": AnalysisAgent(),
            "report": ReportAgent()
        }
    
    def run(self, complex_task: str) -> str:
        # 1. 오케스트레이터가 작업 계획 수립
        plan = self._plan(complex_task)
        
        results = {}
        # 2. 각 서브태스크를 해당 에이전트에게 위임
        for subtask in plan["subtasks"]:
            agent_type = subtask["agent"]
            agent = self.sub_agents[agent_type]
            results[subtask["id"]] = agent.run(subtask["task"])
        
        # 3. 결과 통합
        return self._synthesize(complex_task, results)
    
    def _plan(self, task: str) -> dict:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"""다음 작업을 서브태스크로 분해하세요.
가용 에이전트: research(조사), analysis(분석), report(보고서 작성)

작업: {task}

JSON 형식:
{{"subtasks": [{{"id": "1", "agent": "research", "task": "..."}}]}}"""
            }]
        )
        return json.loads(response.content[0].text)
    
    def _synthesize(self, task: str, results: dict) -> str:
        context = "\n".join(f"서브태스크 {k}: {v}" for k, v in results.items())
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": f"원래 작업: {task}\n\n서브태스크 결과:\n{context}\n\n종합 결론:"
            }]
        )
        return response.content[0].text
```

---

> 멀티스텝 에이전트의 핵심은 상태 관리입니다. 어디까지 했는지, 무엇을 알게 됐는지를 추적해야 목표에 도달할 수 있습니다.
