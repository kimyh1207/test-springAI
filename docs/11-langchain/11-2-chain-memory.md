---
title: "11-2. 체인과 메모리, 도구 호출"
order: 2
tags: [langchain, memory, tools, chain]
status: draft
author: vivace
---

# 11-2. 체인과 메모리, 도구 호출

단순 질답을 넘어 여러 단계를 연결하고, 대화를 기억하고, 외부 시스템을 호출하는 것이 실용적인 AI 서비스의 핵심입니다.

---

## 순차 체인 — 출력이 다음 입력이 된다

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)

# 1단계: 리뷰에서 핵심 불만 추출
extract_chain = (
    ChatPromptTemplate.from_template(
        "다음 리뷰에서 핵심 불만 사항만 한 문장으로 추출하세요:\n{review}"
    )
    | llm
    | StrOutputParser()
)

# 2단계: 불만에 대한 고객 응대 문구 생성
reply_chain = (
    ChatPromptTemplate.from_template(
        "고객 불만: {complaint}\n\n공감적이고 해결책을 제시하는 응대 문구를 작성하세요."
    )
    | llm
    | StrOutputParser()
)

# 두 체인 연결
full_chain = extract_chain | (lambda complaint: reply_chain.invoke({"complaint": complaint}))

review = "주문한 지 2주가 넘었는데 아직도 배송이 안 됐어요. 너무 화가 나요."
response = full_chain.invoke({"review": review})
print(response)
```

### RunnableSequence로 명시적 연결

```python
from langchain_core.runnables import RunnablePassthrough

full_chain = (
    {"complaint": extract_chain}
    | reply_chain
)

result = full_chain.invoke({"review": review})
```

---

## 메모리 — 대화 히스토리 유지

```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# 세션별 히스토리 저장소
store = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

# 히스토리를 포함한 프롬프트
prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 친절한 어시스턴트입니다."),
    MessagesPlaceholder(variable_name="history"),
    ("user", "{input}")
])

chain = prompt | llm | StrOutputParser()

# 메모리 래핑
chain_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)

# 대화
config = {"configurable": {"session_id": "user-123"}}

print(chain_with_history.invoke({"input": "내 이름은 지수야"}, config=config))
print(chain_with_history.invoke({"input": "내 이름이 뭐야?"}, config=config))
# → "지수"라고 답함
```

### Redis 기반 영속성 히스토리

```python
from langchain_community.chat_message_histories import RedisChatMessageHistory

def get_redis_history(session_id: str):
    return RedisChatMessageHistory(
        session_id=session_id,
        url="redis://localhost:6379"
    )

chain_with_history = RunnableWithMessageHistory(
    chain,
    get_redis_history,
    input_messages_key="input",
    history_messages_key="history"
)
```

---

## 도구 호출(Tool Calling)

LLM이 외부 함수를 언제, 어떻게 호출할지 결정합니다.

### 도구 정의

```python
from langchain_core.tools import tool

@tool
def get_order_status(order_id: str) -> str:
    """주문 ID로 배송 상태를 조회합니다."""
    # 실제로는 DB나 API 호출
    status_map = {
        "ORD-001": "배송 완료 (2024-03-15)",
        "ORD-002": "배송 중 (예상: 2024-03-17)",
        "ORD-003": "상품 준비 중",
    }
    return status_map.get(order_id, f"주문 {order_id}를 찾을 수 없습니다.")

@tool
def get_product_info(product_name: str) -> str:
    """상품명으로 재고 및 가격 정보를 조회합니다."""
    products = {
        "에어팟": {"price": 359000, "stock": 15},
        "아이폰": {"price": 1500000, "stock": 3},
    }
    info = products.get(product_name)
    if info:
        return f"{product_name}: {info['price']:,}원, 재고 {info['stock']}개"
    return f"{product_name} 정보를 찾을 수 없습니다."
```

### 모델에 도구 바인딩

```python
tools = [get_order_status, get_product_info]
llm_with_tools = llm.bind_tools(tools)

# 모델이 도구 호출 여부를 스스로 판단
response = llm_with_tools.invoke("ORD-002 주문 상태 알려줘")
print(response.tool_calls)
# [{'name': 'get_order_status', 'args': {'order_id': 'ORD-002'}, 'id': '...'}]
```

### 도구 실행 포함 전체 루프

```python
from langchain_core.messages import ToolMessage

def run_with_tools(user_input: str) -> str:
    messages = [HumanMessage(content=user_input)]
    
    # 1회차: 모델이 도구 호출 결정
    response = llm_with_tools.invoke(messages)
    messages.append(response)
    
    # 도구 호출이 있으면 실행
    while response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            # 도구 실행
            tool_fn = {"get_order_status": get_order_status,
                       "get_product_info": get_product_info}[tool_name]
            tool_result = tool_fn.invoke(tool_args)
            
            messages.append(ToolMessage(
                content=str(tool_result),
                tool_call_id=tool_call["id"]
            ))
        
        # 도구 결과를 바탕으로 최종 답변 생성
        response = llm_with_tools.invoke(messages)
        messages.append(response)
    
    return response.content

print(run_with_tools("ORD-002 주문 언제 와?"))
# → "ORD-002 주문은 현재 배송 중이며, 2024년 3월 17일 도착 예정입니다."
```

---

## 병렬 체인 — 여러 작업을 동시에

```python
from langchain_core.runnables import RunnableParallel

# 같은 입력으로 두 가지 분석을 병렬 실행
parallel_chain = RunnableParallel(
    sentiment=sentiment_chain,
    summary=summary_chain
)

result = parallel_chain.invoke({"review": "배송 빠르고 품질 좋아요!"})
print(result["sentiment"])  # positive
print(result["summary"])    # 빠른 배송과 품질 만족
```

---

> 메모리와 도구 호출은 LLM을 단순 질답기에서 실제 업무를 처리하는 에이전트로 바꾸는 핵심 요소입니다.
