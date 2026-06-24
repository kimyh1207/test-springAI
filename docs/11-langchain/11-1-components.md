---
title: "11-1. LangChain 구성요소(Model · Prompt · Chain)"
order: 1
tags: [langchain, lcel, prompt-template, model]
status: draft
author: vivace
---

# 11-1. LangChain 구성요소(Model · Prompt · Chain)

LangChain은 세 가지 핵심 추상화로 이루어집니다. Model, Prompt, Chain. 이 세 가지를 파이프라인으로 연결하는 것이 LCEL(LangChain Expression Language)입니다.

---

## 설치

```bash
pip install langchain langchain-openai langchain-anthropic python-dotenv
```

```python
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Model — LLM 호출 추상화

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# OpenAI
gpt = ChatOpenAI(model="gpt-4o", temperature=0.7)

# Anthropic
claude = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=2048)

# 직접 호출 (단순 테스트용)
from langchain_core.messages import HumanMessage, SystemMessage

response = gpt.invoke([
    SystemMessage(content="당신은 한국어 전문 번역가입니다."),
    HumanMessage(content="Translate: 'The quick brown fox'")
])
print(response.content)
```

---

## Prompt — 재사용 가능한 템플릿

```python
from langchain_core.prompts import ChatPromptTemplate

# 시스템 + 사용자 메시지 템플릿
prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 {domain} 전문가입니다. 항상 한국어로 답하세요."),
    ("user", "{question}")
])

# 변수 채우기
filled = prompt.format_messages(
    domain="Python 백엔드 개발",
    question="FastAPI와 Django의 차이점은 무엇인가요?"
)
print(filled)
```

### 멀티턴 히스토리 포함

```python
from langchain_core.prompts import MessagesPlaceholder

prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 친절한 어시스턴트입니다."),
    MessagesPlaceholder(variable_name="history"),
    ("user", "{input}")
])
```

---

## LCEL — 파이프라인으로 연결

`|` 연산자로 컴포넌트를 연결합니다. Unix 파이프와 같은 개념입니다.

```python
from langchain_core.output_parsers import StrOutputParser

# prompt | model | output_parser
chain = prompt | gpt | StrOutputParser()

result = chain.invoke({
    "domain": "데이터 분석",
    "question": "pandas groupby와 pivot_table의 차이는?"
})
print(result)  # 문자열로 바로 받음
```

### 각 단계의 역할

```
ChatPromptTemplate  →  ChatOpenAI  →  StrOutputParser
    (입력 포맷팅)      (LLM 호출)      (AIMessage → str)
```

---

## 구조화된 출력

Pydantic 모델로 출력 형태를 강제합니다.

```python
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

class ReviewAnalysis(BaseModel):
    sentiment: str = Field(description="positive, negative, or neutral")
    score: int = Field(description="1~5 rating", ge=1, le=5)
    keywords: list[str] = Field(description="key topics mentioned")
    summary: str = Field(description="one-sentence summary")

llm = ChatOpenAI(model="gpt-4o", temperature=0)
structured_llm = llm.with_structured_output(ReviewAnalysis)

result = structured_llm.invoke("배송이 빠르고 상품 품질도 훌륭했어요!")
print(result.sentiment)  # positive
print(result.score)      # 5
print(result.keywords)   # ['빠른배송', '품질']
```

---

## 배치 처리

여러 입력을 병렬로 처리합니다.

```python
reviews = [
    {"domain": "감성분석", "question": "배송이 느려요"},
    {"domain": "감성분석", "question": "정말 좋은 상품이에요"},
    {"domain": "감성분석", "question": "그냥 그래요"},
]

results = chain.batch(reviews)
for r in results:
    print(r)
```

---

## 스트리밍

```python
for chunk in chain.stream({"domain": "AI", "question": "LangChain이란?"}):
    print(chunk, end="", flush=True)
```

---

## 체인 디버깅 — 중간 단계 확인

```python
from langchain_core.runnables import RunnableLambda

def log_step(input_data):
    print(f"[LOG] input: {input_data}")
    return input_data

debug_chain = (
    prompt
    | RunnableLambda(log_step)  # 프롬프트 출력 확인
    | gpt
    | StrOutputParser()
)

result = debug_chain.invoke({"domain": "테스트", "question": "안녕?"})
```

---

> LCEL의 `|` 연산자는 단순해 보이지만, 내부적으로 스트리밍·배치·비동기를 모두 지원합니다. 파이프라인을 한 번 정의하면 모든 실행 모드에 쓸 수 있습니다.
