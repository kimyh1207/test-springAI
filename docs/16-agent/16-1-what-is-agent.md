---
title: "16-1. 에이전트란 무엇인가(계획·도구·관찰·반복)"
order: 1
tags: [ai-agent, react, planning, observation]
status: draft
author: vivace
---

# 16-1. 에이전트란 무엇인가(계획·도구·관찰·반복)

LLM 하나로 처리할 수 없는 작업이 있습니다. 여러 단계가 필요하거나, 외부 정보를 가져와야 하거나, 결과를 보고 방향을 바꿔야 하는 작업입니다. 에이전트는 이런 작업을 위한 구조입니다.

---

## 에이전트의 핵심 루프

```
사용자 목표
    ↓
[생각] — 지금 무엇을 해야 하는가?
    ↓
[행동] — 도구를 호출한다
    ↓
[관찰] — 도구의 결과를 본다
    ↓
[생각] — 결과를 바탕으로 다음을 결정한다
    ↓
반복 또는 완료
```

LLM은 이 루프에서 두 가지 역할을 합니다. **계획자**(무엇을 해야 하는지 결정)이자 **실행자**(어떤 도구를 어떻게 쓸지 결정).

---

## ReAct 패턴

ReAct(Reasoning + Acting)는 가장 널리 쓰이는 에이전트 패턴입니다. 생각(Thought)과 행동(Action)을 번갈아 기록합니다.

```
질문: 서울의 현재 기온과 내일 날씨를 알려줘

Thought: 서울의 현재 날씨 정보가 필요하다. 날씨 API를 호출해야겠다.
Action: get_weather(city="서울", forecast=False)
Observation: {"temperature": 18, "condition": "맑음", "humidity": 45}

Thought: 현재 날씨는 확인했다. 이제 내일 예보가 필요하다.
Action: get_weather(city="서울", forecast=True)
Observation: {"tomorrow": {"high": 22, "low": 14, "condition": "구름 조금"}}

Thought: 두 정보를 모두 얻었다. 답변을 생성할 수 있다.
Answer: 서울의 현재 기온은 18°C로 맑습니다. 내일은 최고 22°C, 최저 14°C로 구름이 조금 있을 예정입니다.
```

---

## 간단한 ReAct 에이전트 구현

```python
from anthropic import Anthropic
import json

client = Anthropic()

# 도구 정의
tools = [
    {
        "name": "web_search",
        "description": "인터넷에서 정보를 검색합니다",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색 쿼리"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "calculator",
        "description": "수학 계산을 수행합니다",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "계산식 (예: 2 + 3 * 4)"}
            },
            "required": ["expression"]
        }
    }
]

# 도구 실행 함수
def execute_tool(name: str, inputs: dict) -> str:
    if name == "web_search":
        # 실제로는 검색 API 호출
        return f"'{inputs['query']}' 검색 결과: [예시 결과]"
    
    elif name == "calculator":
        try:
            result = eval(inputs["expression"])
            return str(result)
        except Exception as e:
            return f"계산 오류: {e}"
    
    return f"알 수 없는 도구: {name}"

# 에이전트 루프
def run_agent(user_message: str, max_steps: int = 10) -> str:
    messages = [{"role": "user", "content": user_message}]
    
    for step in range(max_steps):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )
        
        # 완료: 텍스트 답변
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
        
        # 도구 호출 필요
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  → 도구 호출: {block.name}({block.input})")
                    result = execute_tool(block.name, block.input)
                    print(f"  ← 결과: {result}")
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            
            messages.append({"role": "user", "content": tool_results})
        else:
            break
    
    return "최대 단계 수 초과"

# 실행
result = run_agent("파이썬의 현재 최신 버전은 무엇이고, 3.10에서 3.12까지 몇 버전이 나왔나요?")
print(result)
```

---

## 에이전트 vs 체인 vs RAG

| 구조 | 흐름 | 적합한 작업 |
|------|------|------------|
| **체인** | 고정된 순서 | 항상 같은 단계를 거치는 작업 |
| **RAG** | 검색 → 생성 | 문서 기반 질답 |
| **에이전트** | 동적, 반복 | 도구가 필요하고 단계가 예측 불가한 작업 |

에이전트는 유연하지만 예측하기 어렵고 비용이 높습니다. 체인으로 해결될 문제를 에이전트로 만들지 마세요.

---

> 에이전트의 핵심은 루프입니다. 각 루프에서 LLM은 지금까지의 관찰을 바탕으로 다음 행동을 결정합니다. 이 루프가 목표에 도달하면 멈춥니다.
