---
title: "17-3. ★확장 — 나만의 MCP 서버 만들기(FastMCP)"
order: 173
tags: [mcp, fastmcp, custom-server, python, production]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 17-3. ★확장 — 나만의 MCP 서버 만들기(FastMCP)

## FastMCP란

FastMCP는 MCP 서버를 **데코레이터 기반**으로 빠르게 만드는 라이브러리다. FastAPI가 Flask를 단순화한 것처럼, FastMCP는 MCP SDK의 보일러플레이트를 제거한다.

```bash
pip install fastmcp

# 확인
python -c "import fastmcp; print(fastmcp.__version__)"
```

---

## 최소 FastMCP 서버

```python
# minimal_server.py
from fastmcp import FastMCP

mcp = FastMCP("계산기 서버")


@mcp.tool()
def add(a: float, b: float) -> float:
    """두 수를 더합니다."""
    return a + b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """두 수를 곱합니다."""
    return a * b


if __name__ == "__main__":
    mcp.run()  # stdio 모드로 실행
```

타입 힌트가 자동으로 JSON Schema로 변환된다. description은 docstring에서 가져온다.

---

## 실전 프로젝트: 이커머스 MCP 서버

```python
# ecommerce_mcp/server.py
from fastmcp import FastMCP
from fastmcp.resources import FileResource
import httpx
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import json

mcp = FastMCP(
    name="이커머스 어시스턴트",
    instructions="""
    이커머스 플랫폼의 상품, 주문, 고객 데이터에 접근하는 MCP 서버입니다.
    상품 검색, 주문 조회, 매출 분석 기능을 제공합니다.
    """
)

DB_PATH = "shop.db"


# ── 데이터베이스 초기화 ──────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── 상품 도구 ────────────────────────────────────────

@mcp.tool()
def search_products(
    query: str,
    category: str | None = None,
    min_price: int = 0,
    max_price: int = 10_000_000,
    limit: int = 10
) -> list[dict]:
    """
    상품을 검색합니다.
    
    Args:
        query: 검색어 (상품명, 브랜드)
        category: 카테고리 필터 (전자제품/의류/식품)
        min_price: 최소 가격 (원)
        max_price: 최대 가격 (원)
        limit: 최대 결과 수 (기본 10)
    """
    conn = get_db()
    
    sql = """
        SELECT id, name, category, price, stock, rating
        FROM products
        WHERE (name LIKE ? OR brand LIKE ?)
          AND price BETWEEN ? AND ?
    """
    params = [f"%{query}%", f"%{query}%", min_price, max_price]
    
    if category:
        sql += " AND category = ?"
        params.append(category)
    
    sql += " ORDER BY rating DESC LIMIT ?"
    params.append(limit)
    
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "price": f"{row['price']:,}원",
            "stock": row["stock"],
            "rating": row["rating"]
        }
        for row in rows
    ]


@mcp.tool()
def get_product_detail(product_id: str) -> dict:
    """상품 상세 정보와 리뷰 요약을 반환합니다."""
    conn = get_db()
    
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?", [product_id]
    ).fetchone()
    
    if not product:
        return {"error": f"상품 {product_id}을 찾을 수 없습니다."}
    
    reviews = conn.execute(
        "SELECT rating, content FROM reviews WHERE product_id = ? LIMIT 5",
        [product_id]
    ).fetchall()
    conn.close()
    
    return {
        "id": product["id"],
        "name": product["name"],
        "price": f"{product['price']:,}원",
        "description": product["description"],
        "stock": product["stock"],
        "avg_rating": product["rating"],
        "recent_reviews": [
            {"rating": r["rating"], "content": r["content"]}
            for r in reviews
        ]
    }


# ── 주문 도구 ────────────────────────────────────────

@mcp.tool()
def get_order_status(order_id: str) -> dict:
    """
    주문 현황과 배송 추적 정보를 반환합니다.
    
    Args:
        order_id: 주문 ID (예: ORD-2025-001234)
    """
    conn = get_db()
    
    order = conn.execute(
        """
        SELECT o.*, u.name as customer_name, u.email
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id = ?
        """,
        [order_id]
    ).fetchone()
    
    if not order:
        return {"error": f"주문 {order_id}을 찾을 수 없습니다."}
    
    items = conn.execute(
        """
        SELECT p.name, oi.quantity, oi.price
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
        """,
        [order_id]
    ).fetchall()
    conn.close()
    
    return {
        "order_id": order["id"],
        "customer": order["customer_name"],
        "status": order["status"],
        "tracking_number": order["tracking_number"],
        "estimated_delivery": order["estimated_delivery"],
        "total": f"{order['total_amount']:,}원",
        "items": [
            {
                "name": item["name"],
                "quantity": item["quantity"],
                "price": f"{item['price']:,}원"
            }
            for item in items
        ]
    }


# ── 분석 도구 ────────────────────────────────────────

@mcp.tool()
def get_sales_summary(
    days: int = 7,
    group_by: str = "day"
) -> dict:
    """
    매출 요약 통계를 반환합니다.
    
    Args:
        days: 조회 기간 (일 수, 기본 7)
        group_by: 집계 단위 (day/week/category)
    """
    conn = get_db()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    
    if group_by == "category":
        rows = conn.execute(
            """
            SELECT p.category, 
                   COUNT(oi.id) as order_count,
                   SUM(oi.price * oi.quantity) as revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.created_at >= ?
            GROUP BY p.category
            ORDER BY revenue DESC
            """,
            [since]
        ).fetchall()
        breakdown = [
            {"category": r["category"], "orders": r["order_count"],
             "revenue": f"{r['revenue']:,}원"}
            for r in rows
        ]
    else:  # day
        rows = conn.execute(
            """
            SELECT DATE(created_at) as date,
                   COUNT(*) as order_count,
                   SUM(total_amount) as revenue
            FROM orders
            WHERE created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date
            """,
            [since]
        ).fetchall()
        breakdown = [
            {"date": r["date"], "orders": r["order_count"],
             "revenue": f"{r['revenue']:,}원"}
            for r in rows
        ]
    
    total = conn.execute(
        "SELECT SUM(total_amount) as total FROM orders WHERE created_at >= ?",
        [since]
    ).fetchone()
    conn.close()
    
    return {
        "period": f"최근 {days}일",
        "total_revenue": f"{total['total'] or 0:,}원",
        "breakdown": breakdown
    }


# ── 리소스 ───────────────────────────────────────────

@mcp.resource("report://daily-summary")
def daily_report() -> str:
    """오늘의 일일 매출 요약 리포트."""
    summary = get_sales_summary(days=1, group_by="category")
    lines = [
        f"# 일일 매출 리포트 — {datetime.now().strftime('%Y-%m-%d')}",
        f"총 매출: {summary['total_revenue']}",
        "",
        "## 카테고리별 매출",
    ]
    for item in summary["breakdown"]:
        lines.append(f"- {item['category']}: {item['revenue']} ({item['orders']}건)")
    return "\n".join(lines)


@mcp.resource("file://catalog.json")
def product_catalog() -> str:
    """전체 상품 카탈로그 (JSON)."""
    conn = get_db()
    products = conn.execute(
        "SELECT id, name, category, price FROM products WHERE stock > 0"
    ).fetchall()
    conn.close()
    return json.dumps(
        [dict(p) for p in products], ensure_ascii=False, indent=2
    )


# ── 프롬프트 ─────────────────────────────────────────

@mcp.prompt()
def customer_complaint_handler(
    order_id: str,
    complaint: str
) -> str:
    """고객 불만 처리를 위한 표준 프롬프트."""
    return f"""
고객 불만 사항을 처리해야 합니다.

주문 ID: {order_id}
불만 내용: {complaint}

다음 절차로 처리해주세요:
1. get_order_status 도구로 주문 현황 확인
2. 불만 유형 분류 (배송 지연 / 상품 불량 / 환불 요청)
3. 해당 유형에 맞는 해결책 제안
4. 고객에게 보낼 응답 메시지 초안 작성

응답은 공감적이고 구체적이어야 합니다.
"""


if __name__ == "__main__":
    mcp.run()
```

---

## 프로젝트 구조

```
ecommerce_mcp/
├── server.py          # FastMCP 서버
├── database.py        # DB 헬퍼 (실제 프로덕션에서 분리)
├── tools/
│   ├── products.py    # 상품 도구
│   ├── orders.py      # 주문 도구
│   └── analytics.py   # 분석 도구
├── pyproject.toml
└── README.md
```

```toml
# pyproject.toml
[project]
name = "ecommerce-mcp"
version = "1.0.0"
dependencies = [
    "fastmcp>=0.4.0",
    "httpx",
]

[project.scripts]
ecommerce-mcp = "ecommerce_mcp.server:main"
```

```python
# 모듈화 예시: tools/products.py
from fastmcp import FastMCP

def register_product_tools(mcp: FastMCP):
    @mcp.tool()
    def search_products(query: str, limit: int = 10) -> list[dict]:
        """상품 검색."""
        ...
    
    @mcp.tool()
    def get_product_detail(product_id: str) -> dict:
        """상품 상세."""
        ...

# server.py에서
from tools.products import register_product_tools
mcp = FastMCP("이커머스")
register_product_tools(mcp)
```

---

## HTTP 모드 배포

원격 클라이언트를 위해 SSE HTTP 서버로 실행한다.

```python
# server.py
if __name__ == "__main__":
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    
    if mode == "http":
        mcp.run(
            transport="sse",
            host="0.0.0.0",
            port=8000
        )
    else:
        mcp.run()  # stdio
```

```bash
# 로컬 stdio 실행
python server.py

# HTTP 서버 실행
python server.py http

# Docker 실행
docker run -p 8000:8000 ecommerce-mcp python server.py http
```

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -e .
EXPOSE 8000
CMD ["python", "server.py", "http"]
```

---

## 테스트

```python
# tests/test_server.py
import pytest
from fastmcp import Client
from server import mcp


@pytest.mark.asyncio
async def test_search_products():
    """FastMCP 인메모리 테스트."""
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_products",
            {"query": "노트북", "limit": 5}
        )
        assert result is not None
        # 결과가 리스트 형태여야 함
        content = result[0].text
        assert "노트북" in content or len(content) > 0


@pytest.mark.asyncio
async def test_list_tools():
    """등록된 도구 목록 확인."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        
        assert "search_products" in tool_names
        assert "get_order_status" in tool_names
        assert "get_sales_summary" in tool_names


@pytest.mark.asyncio
async def test_daily_report_resource():
    """리소스 접근 테스트."""
    async with Client(mcp) as client:
        content = await client.read_resource("report://daily-summary")
        assert "일일 매출 리포트" in content
```

```bash
pytest tests/ -v
```

---

## Claude Desktop에 등록

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "ecommerce": {
      "command": "python",
      "args": ["/path/to/ecommerce_mcp/server.py"],
      "env": {
        "DATABASE_URL": "sqlite:///shop.db",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

등록 후 Claude Desktop에서 바로 사용 가능하다.
```
사용자: "지난 7일 카테고리별 매출 알려줘"
Claude: [get_sales_summary 도구 호출 → 결과 분석 → 자연어 응답]
```

---

## MCP vs REST API 선택 기준

| 상황 | 선택 |
|------|------|
| 사람이 직접 호출하는 API | REST API |
| LLM이 동적으로 결정해서 호출 | MCP |
| 여러 AI 클라이언트에 공유 | MCP |
| 단일 앱 내부 로직 | 직접 함수 호출 |
| 외부 파트너에게 제공 | REST API (MCP 래핑 가능) |

MCP는 AI 에이전트를 위한 인터페이스다. 사람이 직접 쓰는 API는 여전히 REST가 맞다.

---

## 17장 정리

```
MCP 핵심 개념:
├── Tools     → 모델이 실행하는 함수
├── Resources → 모델이 읽는 데이터
└── Prompts   → 팀이 공유하는 템플릿

전송 방식:
├── stdio → 로컬 프로세스 (Claude Desktop)
└── SSE   → 원격 HTTP 서버

FastMCP:
├── @mcp.tool()     → 도구 등록
├── @mcp.resource() → 리소스 등록
└── @mcp.prompt()   → 프롬프트 등록

테스트: Client(mcp) 인메모리 테스트
배포: stdio 로컬 or SSE HTTP or Docker
```

> "MCP 서버를 만드는 건 AI를 위한 API를 설계하는 것이다 — 도구를 잘 정의하면 에이전트가 알아서 조합한다."
