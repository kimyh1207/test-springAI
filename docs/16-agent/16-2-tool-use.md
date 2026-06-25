---
title: "16-2. 도구 사용(Tool Use)과 함수 호출"
order: 2
tags: [tool-use, function-calling, api, anthropic]
status: draft
author: vivace
---

# 16-2. 도구 사용(Tool Use)과 함수 호출

도구(Tool)는 LLM이 외부 시스템과 상호작용하는 인터페이스입니다. 검색, DB 조회, API 호출, 코드 실행 — 모두 도구로 표현됩니다.

---

## 도구 정의 원칙

좋은 도구 정의는 세 가지를 갖춥니다.

1. **명확한 이름**: 도구가 무엇을 하는지 한 번에 알 수 있어야 합니다
2. **정확한 설명**: LLM이 언제 이 도구를 써야 하는지 판단하는 근거
3. **완전한 스키마**: 파라미터 타입, 설명, 필수 여부

```python
# 나쁜 예
{"name": "do_thing", "description": "뭔가 합니다", "input_schema": {...}}

# 좋은 예
{
    "name": "get_customer_info",
    "description": "고객 ID로 고객 정보를 조회합니다. 이름, 이메일, 가입일, 구매 이력을 반환합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "string",
                "description": "고객 고유 ID (예: CUST-12345)"
            },
            "include_orders": {
                "type": "boolean",
                "description": "구매 이력 포함 여부 (기본값: false)"
            }
        },
        "required": ["customer_id"]
    }
}
```

---

## 실전 도구 모음 구현

```python
from anthropic import Anthropic
from datetime import datetime
import json
import sqlite3

client = Anthropic()

# ─── 도구 정의 ───
TOOLS = [
    {
        "name": "search_products",
        "description": "상품명이나 카테고리로 상품을 검색합니다. 가격, 재고, 설명을 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색어 (상품명 또는 카테고리)"},
                "max_price": {"type": "number", "description": "최대 가격 (원)"},
                "in_stock_only": {"type": "boolean", "description": "재고 있는 상품만 (기본: false)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_order_status",
        "description": "주문 ID로 배송 상태와 예상 도착일을 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "주문 번호 (예: ORD-20240315-001)"}
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "create_refund_request",
        "description": "환불 요청을 생성합니다. 환불 가능 여부를 먼저 확인하세요.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "reason": {
                    "type": "string",
                    "enum": ["상품불량", "오배송", "단순변심", "파손"],
                    "description": "환불 사유"
                },
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "환불할 상품 ID 목록"
                }
            },
            "required": ["order_id", "reason"]
        }
    },
    {
        "name": "check_refund_eligibility",
        "description": "주문이 환불 가능한지 확인합니다. create_refund_request 전에 반드시 호출하세요.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"}
            },
            "required": ["order_id"]
        }
    }
]

# ─── 도구 구현 ───
def search_products(query: str, max_price: float = None, in_stock_only: bool = False) -> dict:
    # 실제로는 DB 또는 검색 API
    products = [
        {"id": "P001", "name": "무선 마우스", "price": 35000, "stock": 15, "category": "컴퓨터"},
        {"id": "P002", "name": "기계식 키보드", "price": 89000, "stock": 0, "category": "컴퓨터"},
        {"id": "P003", "name": "모니터 암", "price": 45000, "stock": 7, "category": "컴퓨터"},
    ]
    
    results = [p for p in products if query.lower() in p["name"].lower()]
    if max_price:
        results = [p for p in results if p["price"] <= max_price]
    if in_stock_only:
        results = [p for p in results if p["stock"] > 0]
    
    return {"products": results, "count": len(results)}

def get_order_status(order_id: str) -> dict:
    orders = {
        "ORD-001": {"status": "배송완료", "delivered_at": "2024-03-14", "carrier": "CJ대한통운"},
        "ORD-002": {"status": "배송중", "estimated_arrival": "2024-03-17", "carrier": "한진택배"},
        "ORD-003": {"status": "상품준비중", "estimated_dispatch": "2024-03-16"},
    }
    return orders.get(order_id, {"error": f"주문 {order_id}를 찾을 수 없습니다"})

def check_refund_eligibility(order_id: str) -> dict:
    order = get_order_status(order_id)
    if "error" in order:
        return {"eligible": False, "reason": order["error"]}
    if order["status"] == "배송중":
        return {"eligible": False, "reason": "배송 중인 상품은 도착 후 환불 신청 가능합니다"}
    if order["status"] == "배송완료":
        return {"eligible": True, "deadline": "2024-04-13"}
    return {"eligible": False, "reason": "준비 중인 상품은 취소 신청을 이용하세요"}

def create_refund_request(order_id: str, reason: str, items: list = None) -> dict:
    return {
        "refund_id": f"REF-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "order_id": order_id,
        "reason": reason,
        "status": "접수완료",
        "expected_refund_date": "영업일 기준 3~5일"
    }

# 도구 디스패처
TOOL_MAP = {
    "search_products": search_products,
    "get_order_status": get_order_status,
    "check_refund_eligibility": check_refund_eligibility,
    "create_refund_request": create_refund_request,
}

def dispatch_tool(name: str, inputs: dict) -> str:
    fn = TOOL_MAP.get(name)
    if not fn:
        return json.dumps({"error": f"알 수 없는 도구: {name}"})
    try:
        result = fn(**inputs)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
```

---

## 병렬 도구 호출

Claude는 독립적인 도구를 동시에 호출할 수 있습니다.

```python
# 한 번의 응답에서 여러 도구를 동시에 호출
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    tools=TOOLS,
    messages=[{
        "role": "user",
        "content": "ORD-001과 ORD-002의 상태를 알려줘"
    }]
)

# response.content에 두 개의 tool_use 블록이 동시에 포함됨
tool_results = []
for block in response.content:
    if block.type == "tool_use":
        result = dispatch_tool(block.name, block.input)
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result
        })
```

---

## 도구 호출 강제

특정 도구를 반드시 호출하도록 지정합니다.

```python
# 특정 도구 강제 호출
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=TOOLS,
    tool_choice={"type": "tool", "name": "check_refund_eligibility"},
    messages=[{"role": "user", "content": "ORD-002 환불하고 싶어요"}]
)
```

---

> 도구 설명이 정확할수록 LLM이 올바른 도구를 올바른 타이밍에 씁니다. 도구 정의는 API 문서를 작성하는 것과 같습니다.
