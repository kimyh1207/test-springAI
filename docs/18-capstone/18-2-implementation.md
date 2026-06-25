---
title: "18-2. RAG + 도구 + MCP를 묶은 에이전트 구현"
order: 182
tags: [capstone, rag, mcp, agent, fastmcp, anthropic]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 18-2. RAG + 도구 + MCP를 묶은 에이전트 구현

## MCP 서버 구현

```python
# mcp_server/server.py
from fastmcp import FastMCP
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
import sqlite3
import json
from pathlib import Path

mcp = FastMCP(
    name="이커머스-고객지원",
    instructions="""
    이커머스 고객 지원 전용 MCP 서버입니다.
    주문 조회, 상품 검색, 정책 문서 RAG, 쿠폰 확인 기능을 제공합니다.
    """
)

# 벡터 스토어 초기화 (서버 시작 시 1회)
_vectorstore = None

def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            persist_directory="data/chroma_db",
            embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
            collection_name="policy_docs"
        )
    return _vectorstore


# ── 주문 조회 ─────────────────────────────────────────

@mcp.tool()
def get_order_status(order_id: str) -> dict:
    """
    주문 ID로 배송 현황과 상품 목록을 조회합니다.
    
    Args:
        order_id: 주문 번호 (예: ORD-2025-001234)
    """
    conn = sqlite3.connect("data/shop.db")
    conn.row_factory = sqlite3.Row
    
    order = conn.execute(
        "SELECT * FROM orders WHERE id = ?", [order_id]
    ).fetchone()
    
    if not order:
        return {"found": False, "message": f"주문 {order_id}를 찾을 수 없습니다."}
    
    items = conn.execute(
        """SELECT p.name, oi.quantity, oi.price
           FROM order_items oi JOIN products p ON oi.product_id = p.id
           WHERE oi.order_id = ?""",
        [order_id]
    ).fetchall()
    conn.close()
    
    return {
        "found": True,
        "order_id": order["id"],
        "status": order["status"],           # 결제완료/상품준비중/배송중/배송완료
        "tracking_number": order["tracking_number"],
        "estimated_delivery": order["estimated_delivery"],
        "total_amount": f"{order['total_amount']:,}원",
        "order_date": order["created_at"][:10],
        "items": [
            {"name": i["name"], "qty": i["quantity"], "price": f"{i['price']:,}원"}
            for i in items
        ]
    }


# ── 상품 검색 ─────────────────────────────────────────

@mcp.tool()
def search_products(
    query: str,
    max_price: int | None = None,
    category: str | None = None,
    limit: int = 5
) -> list[dict]:
    """
    상품을 검색합니다.
    
    Args:
        query: 검색어 (상품명, 브랜드, 특징)
        max_price: 최대 가격 (원). 예산 제한이 있을 때 사용
        category: 카테고리 (전자제품/의류/식품/가구)
        limit: 반환할 최대 결과 수 (기본 5)
    """
    conn = sqlite3.connect("data/shop.db")
    conn.row_factory = sqlite3.Row
    
    conditions = ["(name LIKE ? OR brand LIKE ? OR description LIKE ?)"]
    params = [f"%{query}%", f"%{query}%", f"%{query}%"]
    
    if max_price:
        conditions.append("price <= ?")
        params.append(max_price)
    if category:
        conditions.append("category = ?")
        params.append(category)
    
    sql = f"""
        SELECT id, name, brand, category, price, stock, rating, description
        FROM products
        WHERE {' AND '.join(conditions)} AND stock > 0
        ORDER BY rating DESC, review_count DESC
        LIMIT ?
    """
    params.append(limit)
    
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    
    if not rows:
        return [{"message": f"'{query}' 검색 결과가 없습니다."}]
    
    return [
        {
            "name": r["name"],
            "brand": r["brand"],
            "category": r["category"],
            "price": f"{r['price']:,}원",
            "rating": r["rating"],
            "stock": "재고 있음" if r["stock"] > 0 else "품절",
            "summary": r["description"][:80] + "..." if r["description"] else ""
        }
        for r in rows
    ]


# ── 정책 문서 RAG ─────────────────────────────────────

@mcp.tool()
def search_policy_docs(
    query: str,
    doc_type: str | None = None
) -> dict:
    """
    반품, 배송, AS, FAQ 정책 문서에서 관련 내용을 검색합니다.
    RAG 기반으로 가장 관련성 높은 정책 청크를 반환합니다.
    
    Args:
        query: 검색할 질문 또는 키워드
        doc_type: 문서 유형 필터 (return/shipping/warranty/faq). 없으면 전체 검색
    """
    vs = get_vectorstore()
    
    search_kwargs = {"k": 4}
    if doc_type:
        search_kwargs["filter"] = {"doc_type": doc_type}
    
    retriever = vs.as_retriever(search_kwargs=search_kwargs)
    docs = retriever.invoke(query)
    
    if not docs:
        return {
            "found": False,
            "message": "관련 정책을 찾지 못했습니다. 고객센터(1588-0000)로 문의해 주세요."
        }
    
    results = []
    for doc in docs:
        results.append({
            "content": doc.page_content,
            "source": Path(doc.metadata.get("source", "")).name,
            "doc_type": doc.metadata.get("doc_type", "general")
        })
    
    return {
        "found": True,
        "query": query,
        "results": results,
        "top_content": docs[0].page_content  # 가장 관련성 높은 청크
    }


# ── 쿠폰 확인 ─────────────────────────────────────────

@mcp.tool()
def check_coupon(coupon_code: str) -> dict:
    """
    쿠폰 코드의 유효성, 할인 내용, 사용 조건을 확인합니다.
    
    Args:
        coupon_code: 쿠폰 코드 (대소문자 무관)
    """
    conn = sqlite3.connect("data/shop.db")
    conn.row_factory = sqlite3.Row
    
    coupon = conn.execute(
        "SELECT * FROM coupons WHERE UPPER(code) = UPPER(?)",
        [coupon_code]
    ).fetchone()
    conn.close()
    
    if not coupon:
        return {"valid": False, "message": f"쿠폰 코드 '{coupon_code}'를 찾을 수 없습니다."}
    
    from datetime import date
    is_expired = coupon["expires_at"] < str(date.today())
    
    return {
        "valid": not is_expired,
        "code": coupon["code"],
        "discount": f"{coupon['discount_rate']}% 할인" if coupon["type"] == "rate" 
                    else f"{coupon['discount_amount']:,}원 할인",
        "expires_at": coupon["expires_at"],
        "min_order_amount": f"{coupon['min_order_amount']:,}원 이상 주문 시",
        "status": "만료됨" if is_expired else "사용 가능"
    }


if __name__ == "__main__":
    mcp.run()
```

---

## 에이전트 오케스트레이터

```python
# agent/orchestrator.py
import anthropic
import asyncio
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResponse:
    answer: str
    tools_called: list[str]
    tool_results: list[dict]
    response_time_ms: float
    citations: list[str] = field(default_factory=list)


async def run_customer_support_agent(
    user_query: str,
    customer_id: str | None = None
) -> AgentResponse:
    """고객 지원 에이전트 실행."""
    
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server/server.py"]
    )
    
    start_time = time.time()
    tools_called = []
    tool_results = []
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # MCP 도구 목록 → Anthropic 형식 변환
            mcp_tools = await session.list_tools()
            anthropic_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in mcp_tools.tools
            ]
            
            client = anthropic.Anthropic()
            
            system_prompt = """당신은 이커머스 플랫폼의 고객 지원 AI입니다.

역할:
- 고객의 질문에 정확하고 친절하게 답변
- 도구를 활용해 실제 데이터를 조회한 뒤 답변
- 정책 관련 답변 시 반드시 근거 문서를 인용

답변 형식:
- 핵심 내용 먼저, 세부 사항은 그 다음
- 정책 인용 시: "정책에 따르면 ..." 형식
- 불확실한 사항은 고객센터(1588-0000) 안내
"""
            
            if customer_id:
                system_prompt += f"\n현재 고객 ID: {customer_id}"
            
            messages = [{"role": "user", "content": user_query}]
            
            # 에이전트 루프
            while True:
                response = client.messages.create(
                    model="claude-opus-4-8",
                    max_tokens=2048,
                    system=system_prompt,
                    tools=anthropic_tools,
                    messages=messages
                )
                
                if response.stop_reason == "end_turn":
                    answer = next(
                        (b.text for b in response.content if hasattr(b, "text")),
                        ""
                    )
                    break
                
                if response.stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": response.content})
                    tool_result_blocks = []
                    
                    for block in response.content:
                        if block.type != "tool_use":
                            continue
                        
                        tools_called.append(block.name)
                        print(f"  → {block.name}({json_pretty(block.input)})")
                        
                        # MCP 도구 실행
                        mcp_result = await session.call_tool(block.name, block.input)
                        result_text = (
                            mcp_result.content[0].text
                            if mcp_result.content
                            else "결과 없음"
                        )
                        
                        tool_results.append({
                            "tool": block.name,
                            "input": block.input,
                            "output": result_text
                        })
                        
                        tool_result_blocks.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text
                        })
                    
                    messages.append({"role": "user", "content": tool_result_blocks})
    
    elapsed_ms = (time.time() - start_time) * 1000
    
    # 정책 인용 추출
    citations = extract_citations(answer)
    
    return AgentResponse(
        answer=answer,
        tools_called=tools_called,
        tool_results=tool_results,
        response_time_ms=elapsed_ms,
        citations=citations
    )


def json_pretty(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=None)


def extract_citations(text: str) -> list[str]:
    """'정책에 따르면' 패턴으로 인용 추출."""
    import re
    patterns = [
        r'정책에 따르면[^.。]*[.。]',
        r'약관에 의하면[^.。]*[.。]',
        r'\[출처:[^\]]+\]'
    ]
    citations = []
    for pattern in patterns:
        citations.extend(re.findall(pattern, text))
    return citations
```

---

## FastAPI 엔드포인트

```python
# api/app.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agent.orchestrator import run_customer_support_agent
import asyncio
import json

app = FastAPI(title="이커머스 고객 지원 AI API")


class ChatRequest(BaseModel):
    query: str
    customer_id: str | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    tools_called: list[str]
    response_time_ms: float
    citations: list[str]


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """고객 질문에 에이전트가 답변."""
    try:
        result = await run_customer_support_agent(
            user_query=req.query,
            customer_id=req.customer_id
        )
        return ChatResponse(
            answer=result.answer,
            tools_called=result.tools_called,
            response_time_ms=result.response_time_ms,
            citations=result.citations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## 실행 및 테스트

```bash
# 1. 데이터 준비
python data/prepare_docs.py
python data/build_index.py

# 2. API 서버 실행
uvicorn api.app:app --reload --port 8080

# 3. 테스트
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "ORD-2025-001 주문 언제 와?", "customer_id": "USR-001"}'
```

```python
# 통합 테스트
import asyncio
from agent.orchestrator import run_customer_support_agent

async def run_all_scenarios():
    scenarios = [
        "ORD-2025-001 주문이 언제 도착해?",
        "노트북 추천해줘. 예산은 150만원.",
        "반품 어떻게 해? 배송 받은 지 5일 됐어.",
        "쿠폰 SAVE20 아직 유효해?",
    ]
    
    for query in scenarios:
        print(f"\n질문: {query}")
        result = await run_customer_support_agent(query)
        print(f"도구: {result.tools_called}")
        print(f"시간: {result.response_time_ms:.0f}ms")
        print(f"답변: {result.answer[:200]}...")

asyncio.run(run_all_scenarios())
```

---

## 평가 실행

```python
# evaluation/runner.py
import asyncio
import anthropic
from agent.orchestrator import run_customer_support_agent
from evaluation.criteria import TEST_SCENARIOS, EvalResult, PASS_THRESHOLD


async def llm_judge_accuracy(
    query: str,
    answer: str,
    expected_keywords: list[str]
) -> float:
    """LLM으로 답변 정확도 평가."""
    client = anthropic.Anthropic()
    
    prompt = f"""다음 고객 지원 답변을 평가하세요.

고객 질문: {query}
AI 답변: {answer}
기대 키워드: {', '.join(expected_keywords)}

평가 기준:
- 질문에 정확히 답하는가? (0-1)
- 기대 정보가 포함되어 있는가? (0-1)

JSON 형식으로만 응답: {{"score": 0.0-1.0, "reason": "이유"}}"""
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    
    import json, re
    text = response.content[0].text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        result = json.loads(match.group())
        return result.get("score", 0.0)
    return 0.0


async def run_evaluation() -> list[EvalResult]:
    results = []
    
    for scenario in TEST_SCENARIOS:
        print(f"\n[{scenario['id']}] {scenario['query'][:50]}...")
        
        agent_result = await run_customer_support_agent(scenario["query"])
        
        # 도구 선택 정확도
        expected = set(scenario["expected_tools"])
        actual = set(agent_result.tools_called)
        tool_score = len(expected & actual) / len(expected) if expected else 1.0
        
        # 답변 정확도 (LLM judge)
        accuracy = await llm_judge_accuracy(
            scenario["query"],
            agent_result.answer,
            scenario.get("expected_keywords", [scenario["success_criteria"]])
        )
        
        eval_result = EvalResult(
            scenario_id=scenario["id"],
            tool_selection_score=tool_score,
            answer_accuracy_score=accuracy,
            has_citation=len(agent_result.citations) > 0,
            response_time_ms=agent_result.response_time_ms,
            passed=tool_score >= 0.8 and accuracy >= 0.7
        )
        
        results.append(eval_result)
        print(f"  도구 선택: {tool_score:.0%}, 정확도: {accuracy:.0%}, "
              f"시간: {agent_result.response_time_ms:.0f}ms, "
              f"{'✓ 통과' if eval_result.passed else '✗ 실패'}")
    
    passed = sum(1 for r in results if r.passed)
    avg_score = sum(r.overall_score for r in results) / len(results)
    print(f"\n최종: {passed}/{len(results)} 통과, 평균 점수: {avg_score:.0%}")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_evaluation())
```

---

## 샘플 출력

```
질문: 반품 어떻게 해? 배송 받은 지 5일 됐어.
  → search_policy_docs({"query": "반품 신청 방법", "doc_type": "return"})

답변:
반품 신청 방법을 안내드리겠습니다.

정책에 따르면 수령 후 7일 이내 반품이 가능합니다.
현재 5일이 경과하셨으므로 아직 반품 신청이 가능합니다.

반품 신청 방법:
1. 마이페이지 → 주문내역 → 반품 신청
2. 반품 사유 선택 및 사진 첨부
3. 수거 일정 조율 (1-2 영업일 내)

단순 변심의 경우 배송비(3,000원)는 고객 부담입니다.
상품 하자라면 배송비 무료로 처리됩니다.

도구: ['search_policy_docs']
시간: 1847ms
인용: ['정책에 따르면 수령 후 7일 이내 반품이 가능합니다.']
```

> "RAG와 도구와 MCP를 묶으면 LLM은 진짜 업무를 처리하는 에이전트가 된다."
