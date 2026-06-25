---
title: "17-1. MCP가 푸는 문제와 표준의 의미"
order: 171
tags: [mcp, model-context-protocol, tool-integration, anthropic]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 17-1. MCP가 푸는 문제와 표준의 의미

## AI 도구 통합의 혼돈

LLM이 외부 도구를 호출하는 방법은 모델마다, 프레임워크마다 달랐다.

```
OpenAI Function Calling  → JSON Schema 정의
Anthropic Tool Use       → input_schema 정의
LangChain Tools          → @tool 데코레이터
AutoGPT Plugins          → 독자 플러그인 포맷
```

결과: 도구 하나를 만들면 플랫폼별로 4번 구현해야 했다.

MCP(Model Context Protocol)는 이 문제를 해결하기 위해 Anthropic이 2024년 공개한 **개방형 표준**이다.

> "MCP는 AI 모델과 외부 시스템 사이의 USB-C 포트다."

---

## MCP가 정의하는 것

MCP는 세 가지 핵심 개념을 표준화한다.

| 개념 | 설명 | 예시 |
|------|------|------|
| **Tools** | 모델이 호출할 수 있는 함수 | `search_web`, `read_file` |
| **Resources** | 모델이 읽을 수 있는 데이터 | `file://`, `db://` URI |
| **Prompts** | 재사용 가능한 프롬프트 템플릿 | 코드 리뷰 템플릿 |

```
┌─────────────────────────────────────────────────┐
│                   MCP 아키텍처                   │
│                                                 │
│  ┌──────────┐    MCP 프로토콜    ┌────────────┐  │
│  │  LLM     │◄──────────────────►│ MCP Server │  │
│  │  Client  │                   │            │  │
│  │(Claude,  │    JSON-RPC 2.0   │ - Tools    │  │
│  │ GPT-4o)  │                   │ - Resources│  │
│  └──────────┘                   │ - Prompts  │  │
│                                 └─────┬──────┘  │
│                                       │          │
│                              ┌────────▼───────┐  │
│                              │  실제 시스템    │  │
│                              │ DB, API, FS    │  │
│                              └────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## 프로토콜 통신 방식

MCP는 **JSON-RPC 2.0** 위에서 동작한다.

```json
// 클라이언트 → 서버: 도구 목록 요청
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 1
}

// 서버 → 클라이언트: 도구 목록 응답
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [
      {
        "name": "search_products",
        "description": "상품 데이터베이스 검색",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 10}
          },
          "required": ["query"]
        }
      }
    ]
  },
  "id": 1
}

// 클라이언트 → 서버: 도구 실행
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_products",
    "arguments": {"query": "노트북", "limit": 5}
  },
  "id": 2
}
```

---

## 전송 레이어

MCP는 두 가지 전송 방식을 지원한다.

### stdio (로컬 프로세스)
```
LLM Client
    │
    │ stdin/stdout
    │
MCP Server Process
    (로컬 파일, DB 접근)
```

```python
# stdio 서버 실행 예시
import subprocess

process = subprocess.Popen(
    ["python", "my_mcp_server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
```

### SSE (HTTP Server-Sent Events, 원격)
```
LLM Client
    │
    │ HTTP POST /message
    │ GET /sse (event stream)
    │
Remote MCP Server
    (클라우드 API, 원격 DB)
```

```python
# FastAPI SSE 엔드포인트 패턴
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/sse")
async def sse_endpoint():
    async def event_stream():
        while True:
            data = await get_mcp_event()
            yield f"data: {data}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

---

## MCP vs 기존 방식 비교

```python
# 기존: 플랫폼별 도구 정의 (OpenAI)
openai_tool = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}
    }
}

# 기존: 플랫폼별 도구 정의 (Anthropic)
anthropic_tool = {
    "name": "get_weather",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"]
    }
}

# MCP: 한 번 정의, 어디서나 사용
# (서버에서 tools/list로 자동 노출)
```

| 항목 | 기존 방식 | MCP |
|------|-----------|-----|
| 도구 정의 | 플랫폼별 | 표준 JSON Schema |
| 재사용성 | 낮음 | 높음 |
| 인증 | 구현마다 다름 | 서버 레벨 통일 |
| 생태계 | 파편화 | 공유 가능한 서버 |

---

## 현재 MCP 생태계

2025년 기준으로 공식·커뮤니티 MCP 서버가 존재한다.

```
공식 서버 (Anthropic 관리):
- filesystem   : 로컬 파일 읽기/쓰기
- github       : GitHub API 연동
- postgres     : PostgreSQL 쿼리
- brave-search : 웹 검색
- slack        : Slack 메시지

커뮤니티 서버:
- notion, jira, linear (프로젝트 관리)
- aws, gcp (클라우드)
- puppeteer (브라우저 자동화)
```

```bash
# Claude Desktop에서 MCP 서버 설정
# ~/.config/claude/claude_desktop_config.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/docs"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

---

## 표준화의 가치

MCP가 단순한 API 래퍼와 다른 이유는 **발견(discovery)**이다.

```python
# MCP 없이: 도구를 코드에 하드코딩
tools = [get_weather_tool, search_web_tool, read_file_tool]

# MCP 있을 때: 런타임에 서버 탐색
async def discover_tools(server_url: str) -> list:
    """서버에 연결하면 사용 가능한 도구가 자동으로 보인다."""
    client = MCPClient(server_url)
    response = await client.list_tools()
    return response.tools  # 서버가 바뀌어도 코드 수정 없음
```

새 도구를 추가할 때 LLM 클라이언트 코드를 수정할 필요가 없다. 서버에 도구를 추가하면 클라이언트가 자동으로 인식한다.

> "표준이 있을 때, 도구는 제품이 된다 — 한 번 만들어 모든 곳에 판다."
