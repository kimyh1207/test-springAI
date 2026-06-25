---
title: "17-2. MCP 서버 연결과 도구 노출 구조"
order: 172
tags: [mcp, mcp-server, tool-exposure, python-sdk]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 17-2. MCP 서버 연결과 도구 노출 구조

## MCP Python SDK 설치

```bash
pip install mcp anthropic

# 또는 uv 사용 (권장)
uv add mcp anthropic
```

---

## 기본 MCP 서버 구조

MCP 서버의 최소 구현이다.

```python
# server.py
import asyncio
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types

# 서버 인스턴스 생성
app = Server("my-ecommerce-server")


# 도구 목록 핸들러
@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_products",
            description="상품명 또는 카테고리로 상품을 검색합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색어 (상품명, 카테고리, 브랜드)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "반환할 최대 결과 수",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_order_status",
            description="주문 번호로 배송 상태를 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "주문 ID (예: ORD-2025-001)"
                    }
                },
                "required": ["order_id"]
            }
        )
    ]


# 도구 실행 핸들러
@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent]:
    
    if name == "search_products":
        results = await search_product_db(
            query=arguments["query"],
            limit=arguments.get("limit", 10)
        )
        return [types.TextContent(
            type="text",
            text=f"검색 결과 {len(results)}건:\n" + 
                 "\n".join(f"- {r['name']}: {r['price']:,}원" for r in results)
        )]
    
    elif name == "get_order_status":
        status = await fetch_order_status(arguments["order_id"])
        return [types.TextContent(
            type="text",
            text=f"주문 {arguments['order_id']} 상태: {status['stage']}\n"
                 f"예상 도착: {status['eta']}"
        )]
    
    else:
        raise ValueError(f"알 수 없는 도구: {name}")


# 비즈니스 로직 (실제 DB/API 연동)
async def search_product_db(query: str, limit: int) -> list[dict]:
    # 실제 구현에서는 DB 쿼리
    return [
        {"name": f"{query} 관련 상품 {i+1}", "price": 50000 * (i+1)}
        for i in range(min(limit, 3))
    ]


async def fetch_order_status(order_id: str) -> dict:
    # 실제 구현에서는 주문 API 호출
    return {"stage": "배송 중", "eta": "2025-06-27"}


# 서버 실행 진입점
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="my-ecommerce-server",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Anthropic Claude와 MCP 연동

Claude API에서 MCP 서버를 직접 연결하는 패턴이다.

```python
# client.py
import anthropic
import subprocess
import json
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_with_mcp():
    """MCP 서버를 시작하고 Claude와 연결한다."""
    
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 서버 초기화
            await session.initialize()
            
            # 사용 가능한 도구 목록 가져오기
            tools_response = await session.list_tools()
            
            # Anthropic API 형식으로 변환
            anthropic_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in tools_response.tools
            ]
            
            client = anthropic.Anthropic()
            messages = [
                {"role": "user", "content": "노트북 검색해줘, 그리고 ORD-2025-001 주문 상태도 알려줘"}
            ]
            
            # 에이전트 루프
            while True:
                response = client.messages.create(
                    model="claude-opus-4-8",
                    max_tokens=4096,
                    tools=anthropic_tools,
                    messages=messages
                )
                
                if response.stop_reason == "end_turn":
                    # 최종 텍스트 응답 출력
                    for block in response.content:
                        if hasattr(block, "text"):
                            print(block.text)
                    break
                
                if response.stop_reason == "tool_use":
                    # 도구 호출 처리
                    messages.append({"role": "assistant", "content": response.content})
                    tool_results = []
                    
                    for block in response.content:
                        if block.type == "tool_use":
                            print(f"→ 도구 호출: {block.name}({block.input})")
                            
                            # MCP 서버에서 도구 실행
                            result = await session.call_tool(block.name, block.input)
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result.content[0].text if result.content else ""
                            })
                    
                    messages.append({"role": "user", "content": tool_results})


asyncio.run(run_with_mcp())
```

---

## 리소스(Resource) 노출

MCP는 도구 외에도 파일이나 DB 레코드 같은 **리소스**를 노출할 수 있다.

```python
from mcp import types

@app.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """서버가 제공하는 리소스 목록."""
    return [
        types.Resource(
            uri="file:///reports/daily_sales.csv",
            name="일별 매출 리포트",
            description="최근 30일 매출 데이터",
            mimeType="text/csv"
        ),
        types.Resource(
            uri="db://products/catalog",
            name="상품 카탈로그",
            description="전체 상품 목록 및 재고",
            mimeType="application/json"
        )
    ]


@app.read_resource()
async def handle_read_resource(uri: str) -> str:
    """URI로 리소스 내용을 반환."""
    if uri == "file:///reports/daily_sales.csv":
        with open("/reports/daily_sales.csv", "r") as f:
            return f.read()
    
    elif uri == "db://products/catalog":
        products = await get_all_products()
        return json.dumps(products, ensure_ascii=False)
    
    raise ValueError(f"알 수 없는 리소스: {uri}")
```

---

## 프롬프트 템플릿 노출

팀이 공유하는 프롬프트를 서버에서 관리할 수 있다.

```python
@app.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="analyze_sales",
            description="매출 데이터 분석 및 인사이트 추출",
            arguments=[
                types.PromptArgument(
                    name="period",
                    description="분석 기간 (예: 2025년 1분기)",
                    required=True
                ),
                types.PromptArgument(
                    name="focus",
                    description="분석 초점 (growth/churn/product)",
                    required=False
                )
            ]
        )
    ]


@app.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict | None
) -> types.GetPromptResult:
    if name == "analyze_sales":
        period = arguments.get("period", "이번 달") if arguments else "이번 달"
        focus = arguments.get("focus", "전반적") if arguments else "전반적"
        
        return types.GetPromptResult(
            description="매출 분석 프롬프트",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"{period} 매출 데이터를 {focus} 관점에서 분석해줘. "
                             f"핵심 지표, 이상 패턴, 개선 기회를 포함해서."
                    )
                )
            ]
        )
    raise ValueError(f"알 수 없는 프롬프트: {name}")
```

---

## Claude Desktop 연동 설정

로컬 서버를 Claude Desktop에 등록하는 설정이다.

```json
// ~/.config/claude/claude_desktop_config.json (Linux/Mac)
// %APPDATA%\Claude\claude_desktop_config.json (Windows)
{
  "mcpServers": {
    "ecommerce": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "DATABASE_URL": "postgresql://localhost/shop",
        "API_KEY": "your-api-key"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/workspace"]
    }
  }
}
```

재시작하면 Claude Desktop 사이드바에 서버 도구들이 나타난다.

---

## 에러 처리와 로깅

```python
import logging
from mcp.types import McpError, ErrorCode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    logger.info(f"도구 호출: {name}, 인자: {arguments}")
    
    try:
        if name == "search_products":
            results = await search_product_db(**arguments)
            logger.info(f"검색 완료: {len(results)}건")
            return [types.TextContent(type="text", text=format_results(results))]
        
        else:
            raise McpError(
                ErrorCode.MethodNotFound,
                f"도구를 찾을 수 없습니다: {name}"
            )
    
    except ConnectionError as e:
        logger.error(f"DB 연결 실패: {e}")
        raise McpError(
            ErrorCode.InternalError,
            f"데이터베이스 연결 오류: {str(e)}"
        )
    except ValueError as e:
        raise McpError(ErrorCode.InvalidParams, str(e))
```

---

## 서버 배포 체크리스트

```
로컬 stdio 서버:
□ python server.py 단독 실행 테스트
□ claude_desktop_config.json 등록
□ Claude Desktop 재시작 후 도구 목록 확인
□ 실제 대화로 도구 호출 테스트

원격 SSE 서버:
□ FastAPI/uvicorn으로 배포
□ HTTPS 인증서 설정
□ 인증 토큰/API Key 환경변수 처리
□ /sse 엔드포인트 헬스체크
□ 방화벽 포트 허용
```

> "MCP 서버는 AI가 읽을 수 있는 API다 — 사람을 위한 Swagger처럼 모델을 위한 도구 명세를 노출한다."
