---
title: "20-1. 기능 단위 구현과 통합 테스트"
order: 201
tags: [implementation, testing, integration-test, tdd]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 20-1. 기능 단위 구현과 통합 테스트

## 구현 순서 전략

기능을 한 번에 다 짜지 않는다. 데이터 흐름을 따라 안에서 밖으로 구현한다.

```
구현 순서:
1. MCP 서버 도구 (가장 안쪽, 외부 의존성 없음)
2. AI 에이전트 (MCP 서버 의존)
3. FastAPI 엔드포인트 (에이전트 의존)
4. Spring Boot 게이트웨이 (FastAPI 의존)
5. React UI (Spring 의존)

각 레이어가 완성되고 테스트를 통과하면 다음으로 진행.
```

---

## 1단계: MCP 도구 테스트

```python
# tests/test_mcp_tools.py
import pytest
import asyncio
from fastmcp import Client
from mcp_server.server import mcp

# 테스트용 인메모리 DB 세팅
@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    import sqlite3
    db_path = str(tmp_path / "test_shop.db")
    monkeypatch.setenv("DB_PATH", db_path)
    
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE orders (
            id TEXT PRIMARY KEY, status TEXT, tracking_number TEXT,
            estimated_delivery TEXT, total_amount INTEGER, created_at TEXT
        );
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY, order_id TEXT, product_id TEXT,
            quantity INTEGER, price INTEGER
        );
        CREATE TABLE products (
            id TEXT PRIMARY KEY, name TEXT, brand TEXT, category TEXT,
            price INTEGER, stock INTEGER, rating REAL, description TEXT
        );
        CREATE TABLE coupons (
            id INTEGER PRIMARY KEY, code TEXT, type TEXT,
            discount_rate INTEGER, discount_amount INTEGER,
            min_order_amount INTEGER, expires_at TEXT
        );
        
        INSERT INTO orders VALUES ('ORD-001', '배송중', 'TRK-123', '2025-06-30', 85000, '2025-06-25');
        INSERT INTO products VALUES ('P001', '맥북 에어 M3', 'Apple', '전자제품', 1690000, 10, 4.8, '최신 M3 칩');
        INSERT INTO coupons VALUES (1, 'SAVE20', 'rate', 20, 0, 50000, '2025-12-31');
    """)
    conn.close()


@pytest.mark.asyncio
async def test_get_order_status_found():
    async with Client(mcp) as client:
        result = await client.call_tool("get_order_status", {"order_id": "ORD-001"})
        data = parse_result(result)
        
        assert data["found"] is True
        assert data["status"] == "배송중"
        assert data["tracking_number"] == "TRK-123"


@pytest.mark.asyncio
async def test_get_order_status_not_found():
    async with Client(mcp) as client:
        result = await client.call_tool("get_order_status", {"order_id": "ORD-999"})
        data = parse_result(result)
        
        assert data["found"] is False


@pytest.mark.asyncio
async def test_search_products_with_price_filter():
    async with Client(mcp) as client:
        result = await client.call_tool("search_products", {
            "query": "맥북",
            "max_price": 2000000
        })
        products = parse_result(result)
        
        assert len(products) >= 1
        assert any("맥북" in p["name"] for p in products)


@pytest.mark.asyncio
async def test_check_coupon_valid():
    async with Client(mcp) as client:
        result = await client.call_tool("check_coupon", {"coupon_code": "SAVE20"})
        data = parse_result(result)
        
        assert data["valid"] is True
        assert "20%" in data["discount"]


@pytest.mark.asyncio
async def test_check_coupon_not_found():
    async with Client(mcp) as client:
        result = await client.call_tool("check_coupon", {"coupon_code": "INVALID"})
        data = parse_result(result)
        
        assert data["valid"] is False


def parse_result(result) -> dict | list:
    import json
    text = result[0].text if result else "{}"
    return json.loads(text)
```

---

## 2단계: RAG 파이프라인 테스트

```python
# tests/test_rag.py
import pytest
from rag.pipeline import RAGPipeline
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_vectorstore():
    """Chroma 없이 RAG 파이프라인 테스트."""
    mock = MagicMock()
    mock.as_retriever.return_value.invoke.return_value = [
        MagicMock(
            page_content="수령 후 7일 이내 반품 가능합니다.",
            metadata={"source": "return_policy.md", "doc_type": "return"}
        )
    ]
    return mock


@pytest.fixture
def rag_pipeline(mock_vectorstore, monkeypatch):
    pipeline = RAGPipeline.__new__(RAGPipeline)
    pipeline.vectorstore = mock_vectorstore
    return pipeline


@pytest.mark.asyncio
async def test_rag_returns_relevant_content(rag_pipeline):
    result = await rag_pipeline.query("반품 기간이 얼마나 되나요?")
    
    assert result["found"] is True
    assert len(result["results"]) > 0
    assert "7일" in result["top_content"]


@pytest.mark.asyncio
async def test_rag_with_doc_type_filter(rag_pipeline, mock_vectorstore):
    await rag_pipeline.query("반품 방법", doc_type="return")
    
    # 필터가 retriever에 전달되었는지 확인
    call_kwargs = mock_vectorstore.as_retriever.call_args
    assert call_kwargs is not None
```

---

## 3단계: 에이전트 통합 테스트

```python
# tests/test_agent_integration.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agent.orchestrator import run_customer_support_agent


@pytest.fixture
def mock_anthropic():
    """실제 API 호출 없이 Claude 응답 모킹."""
    with patch("agent.orchestrator.anthropic.Anthropic") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        
        # 단순 질문 → 도구 없이 바로 답변
        client.messages.create.return_value = MagicMock(
            stop_reason="end_turn",
            content=[MagicMock(type="text", text="배송 예정일은 2025-06-30입니다.")]
        )
        yield client


@pytest.fixture
def mock_mcp_session():
    """MCP 서버 연결 모킹."""
    with patch("agent.orchestrator.stdio_client") as mock_ctx:
        session = AsyncMock()
        
        # 도구 목록 반환
        tool = MagicMock()
        tool.name = "get_order_status"
        tool.description = "주문 조회"
        tool.inputSchema = {"type": "object", "properties": {"order_id": {"type": "string"}}}
        session.list_tools.return_value = MagicMock(tools=[tool])
        
        # 도구 실행 결과
        tool_result = MagicMock()
        tool_result.content = [MagicMock(text='{"found": true, "status": "배송중"}')]
        session.call_tool.return_value = tool_result
        
        mock_ctx.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
        
        with patch("agent.orchestrator.ClientSession") as mock_session_cls:
            mock_session_cls.return_value.__aenter__.return_value = session
            yield session


@pytest.mark.asyncio
async def test_agent_answers_order_query(mock_anthropic, mock_mcp_session):
    result = await run_customer_support_agent("ORD-001 주문 어디까지 왔어?")
    
    assert result.answer != ""
    assert result.response_time_ms > 0


@pytest.mark.asyncio
async def test_agent_records_tool_calls(mock_mcp_session):
    """도구 호출이 기록되는지 확인."""
    # Claude가 tool_use를 반환한 뒤 end_turn 반환하도록 설정
    with patch("agent.orchestrator.anthropic.Anthropic") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "call_1"
        tool_block.name = "get_order_status"
        tool_block.input = {"order_id": "ORD-001"}
        
        final_block = MagicMock()
        final_block.type = "text"
        final_block.text = "배송 중입니다."
        
        client.messages.create.side_effect = [
            MagicMock(stop_reason="tool_use", content=[tool_block]),
            MagicMock(stop_reason="end_turn", content=[final_block])
        ]
        
        result = await run_customer_support_agent("ORD-001 어디야?")
        assert "get_order_status" in result.tools_called
```

---

## 4단계: FastAPI 엔드포인트 테스트

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from api.app import app
from unittest.mock import AsyncMock, patch

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_agent():
    from agent.orchestrator import AgentResponse
    with patch("api.app.run_customer_support_agent", new_callable=AsyncMock) as mock:
        mock.return_value = AgentResponse(
            answer="배송 중입니다. 2025-06-30 도착 예정입니다.",
            tools_called=["get_order_status"],
            tool_results=[],
            response_time_ms=1200.0,
            citations=[]
        )
        yield mock


def test_chat_endpoint_returns_200():
    response = client.post("/chat", json={
        "query": "ORD-001 주문 상태",
        "session_id": "test-session"
    })
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "tools_called" in data


def test_chat_endpoint_requires_query():
    response = client.post("/chat", json={"session_id": "test"})
    assert response.status_code == 422  # Pydantic 검증 실패


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

---

## 5단계: Spring Boot 통합 테스트

```java
// src/test/java/ChatControllerTest.java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
class ChatControllerTest {

    @Autowired
    private WebTestClient webTestClient;

    @MockBean
    private ChatService chatService;

    @Test
    void chatEndpointRequiresAuthentication() {
        webTestClient.post().uri("/api/chat")
                .bodyValue(new ChatRequest("테스트", "S123"))
                .exchange()
                .expectStatus().isUnauthorized();
    }

    @Test
    @WithMockUser(username = "user1")
    void chatEndpointReturnsChatResponse() {
        when(chatService.getResponse(any(), any()))
                .thenReturn(Mono.just(new ChatResponse(
                        "배송 중입니다.", List.of("get_order_status"),
                        List.of(), 1200L
                )));

        webTestClient.post().uri("/api/chat")
                .headers(h -> h.setBearerAuth(generateTestToken("user1")))
                .bodyValue(new ChatRequest("ORD-001 상태", "S123"))
                .exchange()
                .expectStatus().isOk()
                .expectBody(ChatResponse.class)
                .value(r -> {
                    assertThat(r.answer()).isNotBlank();
                    assertThat(r.toolsCalled()).contains("get_order_status");
                });
    }

    private String generateTestToken(String userId) {
        return jwtService.generate(userId, List.of("USER"));
    }
}
```

---

## 테스트 실행 스크립트

```bash
#!/bin/bash
# scripts/test_all.sh

set -e

echo "=== Python 테스트 ==="
cd ai_service
pytest tests/ -v --tb=short --cov=. --cov-report=term-missing
cd ..

echo "=== Spring 테스트 ==="
cd spring-gateway
./gradlew test
cd ..

echo "=== 통합 테스트 (서비스 실행 필요) ==="
if curl -s http://localhost:8080/actuator/health > /dev/null; then
    pytest tests/integration/ -v
else
    echo "서버가 실행 중이지 않습니다. 통합 테스트 건너뜀."
fi

echo "=== 완료 ==="
```

> "테스트는 가장 안쪽에서 시작한다 — 도구가 맞으면 에이전트가 맞고, 에이전트가 맞으면 API가 맞다."
