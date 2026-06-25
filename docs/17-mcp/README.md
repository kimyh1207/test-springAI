---
title: "17장. MCP(Model Context Protocol) 깊이 이해"
order: 17
tags: [mcp, model-context-protocol, tool-integration]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 17장. MCP(Model Context Protocol) 깊이 이해

## 들어가며

16장에서 도구를 직접 코드로 정의했습니다. 그런데 모든 팀이 모든 도구를 직접 구현해야 할까요? MCP는 "도구 제공자"와 "도구 사용자"를 표준 프로토콜로 분리합니다. 한번 만든 MCP 서버는 Claude, Cursor, 어떤 MCP 클라이언트에서든 쓸 수 있습니다.

---

## 이 챕터에서 배울 것

- **[17-1. MCP가 푸는 문제와 표준의 의미](./17-1-mcp-overview.md)** — 왜 MCP가 필요한가, 어떻게 작동하는가
- **[17-2. MCP 서버 연결과 도구 노출 구조](./17-2-mcp-server.md)** — 기존 MCP 서버를 연결하고 사용하는 방법
- **[17-3. ★ 나만의 MCP 서버 만들기(FastMCP)](./17-3-custom-mcp.md)** — 사내 시스템을 MCP 서버로 노출하는 방법

---

> MCP는 AI와 도구 사이의 USB-C 표준입니다. 한 번 만들면 어디서든 연결됩니다.

이 챕터를 마치면 기존 MCP 서버를 활용하고, 직접 MCP 서버를 만들어 LLM 에이전트에 연결할 수 있습니다.
