---
title: "11장. LangChain 기반 생성형 AI 서비스"
order: 11
tags: [langchain, python, llm, chain]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 11장. LangChain 기반 생성형 AI 서비스

## 들어가며

Spring AI가 Java 백엔드에서 LLM을 다루는 도구라면, LangChain은 Python 생태계의 표준입니다. 빠른 프로토타이핑, 복잡한 체인 구성, 다양한 도구 통합에서 강점을 가집니다. AI 서비스를 만들 때 두 가지를 모두 알면 상황에 맞게 선택할 수 있습니다.

---

## 이 챕터에서 배울 것

- **[11-1. LangChain 구성요소(Model · Prompt · Chain)](./11-1-components.md)** — LangChain의 핵심 빌딩 블록과 LCEL 파이프라인
- **[11-2. 체인과 메모리, 도구 호출](./11-2-chain-memory.md)** — 여러 단계를 연결하고, 대화를 기억하고, 외부 도구를 쓰는 방법
- **[11-3. ★ 프로토타입을 안정적 서비스로 다듬기](./11-3-productionize.md)** — LangServe로 API 제공, 관찰 가능성, 비용 최적화

---

> LangChain은 빠르게 만들고 빠르게 검증하는 도구입니다. 프로덕션으로 가져가기 전에 무엇을 추가해야 하는지도 함께 배웁니다.

이 챕터를 마치면 Python으로 LLM 기반 서비스를 설계하고, Spring Boot 백엔드와 연결하는 전체 구조를 이해할 수 있습니다.
