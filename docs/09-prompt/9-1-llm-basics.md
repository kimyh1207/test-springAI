---
title: "9-1. LLM의 동작 원리(토큰·컨텍스트 윈도우)"
order: 1
tags: [llm, token, context-window, transformer]
status: draft
author: vivace
---

# 9-1. LLM의 동작 원리(토큰·컨텍스트 윈도우)

프롬프트를 잘 쓰려면 모델이 어떻게 작동하는지 알아야 합니다. 마법처럼 느껴지지만 구체적인 동작 원리가 있습니다.

---

## 토큰이란

LLM은 텍스트를 문자 단위가 아니라 **토큰(token)** 단위로 처리합니다. 토큰은 단어, 단어의 일부, 또는 구두점입니다.

```
"Hello, world!"  →  ["Hello", ",", " world", "!"]  →  4 tokens
"안녕하세요"     →  ["안", "녕", "하", "세", "요"]  →  약 5~7 tokens
```

영어는 단어당 약 0.75 토큰, 한국어는 음절당 1~2 토큰으로 계산하면 근사치를 구할 수 있습니다.

토큰이 중요한 이유:
- **비용**: API 요금은 입력+출력 토큰 수로 계산됩니다
- **속도**: 토큰이 많을수록 응답이 느립니다
- **한계**: 컨텍스트 윈도우에 들어갈 수 있는 최대 토큰 수가 있습니다

---

## 컨텍스트 윈도우

모델이 한 번에 처리할 수 있는 텍스트의 최대 길이입니다. 이 범위 안의 내용만 "기억"합니다.

| 모델 | 컨텍스트 윈도우 |
|------|---------------|
| GPT-3.5 | 16K tokens |
| GPT-4o | 128K tokens |
| Claude 3.5 Sonnet | 200K tokens |
| Gemini 1.5 Pro | 1M tokens |

컨텍스트 윈도우에 들어가는 것들:
- 시스템 프롬프트
- 지금까지의 대화 전체 (멀티턴의 경우)
- 사용자 입력
- 모델의 출력 (다음 턴에 포함)

대화가 길어지면 초기 내용이 윈도우에서 벗어납니다. 오래된 대화를 기억하지 못하는 이유입니다.

---

## LLM이 출력을 생성하는 방식

LLM은 다음 토큰을 하나씩 예측합니다. 모든 텍스트 생성이 이 방식으로 이루어집니다.

```
입력: "서울의 수도는"
→ 다음 토큰 예측: " 서울" (높은 확률), " 부산" (낮은 확률), ...
→ " 서울" 선택
→ 다음 토큰 예측: "입니다" (높은 확률), ...
→ 반복
```

**Temperature**: 다음 토큰을 선택할 때의 무작위성을 조절합니다.
- `temperature=0`: 항상 가장 확률이 높은 토큰 선택 → 결정적, 재현 가능
- `temperature=1`: 확률 분포에 따라 샘플링 → 창의적, 다양성 있음

```python
from anthropic import Anthropic

client = Anthropic()

# 결정적 출력 (코드 생성, 데이터 추출에 적합)
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    temperature=0,
    messages=[{"role": "user", "content": "1+1=?"}]
)

# 창의적 출력 (글쓰기, 브레인스토밍에 적합)
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    temperature=0.9,
    messages=[{"role": "user", "content": "여름 캠페인 슬로건 5개를 제안해줘"}]
)
```

---

## 시스템 프롬프트와 사용자 메시지

대부분의 LLM API는 두 가지 역할을 구분합니다.

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="당신은 이커머스 고객 서비스 전문가입니다. 항상 한국어로 답하고, 공감적인 어조를 유지하세요.",
    messages=[
        {"role": "user", "content": "주문한 상품이 아직 안 왔어요."}
    ]
)
```

**시스템 프롬프트**: 모델의 역할, 행동 방식, 제약을 정의합니다. 사용자 메시지보다 높은 우선순위를 가집니다.

**사용자 메시지**: 실제 요청입니다. 매 호출마다 달라집니다.

---

## 멀티턴 대화

대화 히스토리를 직접 관리해서 전달해야 합니다. 모델 자체는 상태가 없습니다(stateless).

```python
conversation_history = []

def chat(user_message: str) -> str:
    conversation_history.append({"role": "user", "content": user_message})
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="당신은 친절한 어시스턴트입니다.",
        messages=conversation_history
    )
    
    assistant_message = response.content[0].text
    conversation_history.append({"role": "assistant", "content": assistant_message})
    
    return assistant_message

print(chat("내 이름은 지수야"))
print(chat("내 이름이 뭐라고 했지?"))  # 히스토리가 있으므로 "지수"라고 답함
```

---

> 토큰을 줄이고, 컨텍스트를 잘 관리하는 것이 LLM 애플리케이션 최적화의 핵심입니다. 비용과 성능 모두 여기서 결정됩니다.
