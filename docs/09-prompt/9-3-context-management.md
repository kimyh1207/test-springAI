---
title: "9-3. Context 관리와 구조화된 출력"
order: 3
tags: [context, structured-output, json, rag]
status: draft
author: vivace
---

# 9-3. Context 관리와 구조화된 출력

LLM 애플리케이션에서 두 가지가 실무의 핵심입니다. 긴 대화에서 컨텍스트를 잃지 않는 것, 그리고 출력을 프로그램이 파싱할 수 있는 형태로 받는 것입니다.

---

## 컨텍스트 관리 전략

### 문제: 컨텍스트 윈도우 초과

대화가 길어지면 전체 히스토리를 넣을 수 없습니다. 비용도 급증합니다.

```python
# 히스토리 토큰 추정
def estimate_tokens(messages: list[dict]) -> int:
    total = sum(len(m['content']) for m in messages)
    return total // 4  # 영어 기준 근사치, 한국어는 // 2 ~ // 3

# 컨텍스트 윈도우 초과 방지
MAX_TOKENS = 100_000

def trim_history(messages: list[dict]) -> list[dict]:
    while estimate_tokens(messages) > MAX_TOKENS and len(messages) > 2:
        messages.pop(1)  # 가장 오래된 메시지부터 제거 (index 0은 시스템)
    return messages
```

### 전략 1: 슬라이딩 윈도우

최근 N개 메시지만 유지합니다.

```python
MAX_HISTORY = 10  # 최근 10개 메시지만 유지

def chat_with_window(user_message: str, history: list) -> tuple[str, list]:
    history.append({"role": "user", "content": user_message})
    
    # 최근 N개만 전송
    recent_history = history[-MAX_HISTORY:]
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=recent_history
    )
    
    reply = response.content[0].text
    history.append({"role": "assistant", "content": reply})
    return reply, history
```

### 전략 2: 요약 압축

오래된 대화를 요약해서 보존합니다.

```python
def summarize_history(old_messages: list[dict]) -> str:
    summary_prompt = f"""다음 대화 내용을 핵심 정보만 남겨 3~5문장으로 요약하세요.
    
대화:
{chr(10).join(f"{m['role']}: {m['content']}" for m in old_messages)}

요약:"""
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # 요약은 빠른 모델로
        max_tokens=256,
        messages=[{"role": "user", "content": summary_prompt}]
    )
    return response.content[0].text

def compress_history(messages: list[dict], keep_recent: int = 6) -> list[dict]:
    if len(messages) <= keep_recent:
        return messages
    
    old = messages[:-keep_recent]
    recent = messages[-keep_recent:]
    
    summary = summarize_history(old)
    summary_message = {
        "role": "user",
        "content": f"[이전 대화 요약]\n{summary}"
    }
    
    return [summary_message] + recent
```

---

## 구조화된 출력

LLM 출력을 자유 텍스트로 받으면 파싱이 불안정합니다. JSON 등 구조화된 형태로 강제하면 신뢰할 수 있는 파싱이 가능합니다.

### JSON 출력 강제

```python
import json

def analyze_review(review_text: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        temperature=0,  # 결정적 출력
        messages=[{
            "role": "user",
            "content": f"""다음 리뷰를 분석하고 반드시 아래 JSON 형식으로만 답하세요.
다른 텍스트는 절대 포함하지 마세요.

JSON 형식:
{{
  "sentiment": "positive" | "negative" | "neutral",
  "score": 1~5,
  "keywords": ["키워드1", "키워드2"],
  "summary": "한 문장 요약",
  "action_required": true | false
}}

리뷰: {review_text}"""
        }]
    )
    
    raw = response.content[0].text.strip()
    
    # 마크다운 코드블록 제거 (모델이 ```json ... ``` 로 감쌀 때)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    
    return json.loads(raw)

result = analyze_review("배송이 빠르고 좋아요! 근데 포장이 좀 아쉽네요.")
print(result)
# {"sentiment": "positive", "score": 4, "keywords": ["빠른배송", "포장아쉬움"], ...}
```

### Pydantic으로 검증

```python
from pydantic import BaseModel, field_validator
from typing import Literal

class ReviewAnalysis(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"]
    score: int
    keywords: list[str]
    summary: str
    action_required: bool
    
    @field_validator('score')
    @classmethod
    def score_range(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('score must be between 1 and 5')
        return v

def analyze_and_validate(review_text: str) -> ReviewAnalysis:
    raw = analyze_review(review_text)
    return ReviewAnalysis(**raw)

result = analyze_and_validate("최악의 서비스입니다. 환불 요청합니다.")
print(result.sentiment)    # negative
print(result.action_required)  # True
```

---

## RAG 패턴 — 외부 지식 주입

LLM은 훈련 데이터 이후의 정보나 내부 문서를 모릅니다. 관련 정보를 컨텍스트에 직접 주입하면 해결됩니다.

```python
def rag_query(user_question: str, knowledge_base: list[str]) -> str:
    # 실제로는 벡터 검색으로 관련 문서만 선택
    # 여기서는 단순화를 위해 전체 전달
    context = "\n---\n".join(knowledge_base)
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="""당신은 사내 문서를 기반으로 답하는 어시스턴트입니다.
반드시 제공된 문서 내용만을 근거로 답하세요.
문서에 없는 내용은 "제공된 문서에서 찾을 수 없습니다."라고 답하세요.""",
        messages=[{
            "role": "user",
            "content": f"""[참고 문서]
{context}

[질문]
{user_question}"""
        }]
    )
    
    return response.content[0].text

# 사용 예
docs = [
    "연차 휴가는 입사 1년 후 15일 발생합니다. 매년 1일씩 추가되며 최대 25일입니다.",
    "병가는 연간 60일까지 사용 가능합니다. 의사 소견서 제출이 필요합니다.",
]

answer = rag_query("연차 최대 며칠까지 쓸 수 있나요?", docs)
print(answer)  # 25일
```

---

## 스트리밍 응답

긴 응답을 기다리지 않고 실시간으로 받아 사용자에게 표시합니다.

```python
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Spring Boot에 대해 설명해줘"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

Spring AI에서는 `StreamingChatClient`가 같은 역할을 합니다(11장에서 다룹니다).

---

> 컨텍스트 관리와 구조화된 출력은 LLM 애플리케이션을 "작동하는 데모"에서 "신뢰할 수 있는 서비스"로 만드는 두 기둥입니다.
