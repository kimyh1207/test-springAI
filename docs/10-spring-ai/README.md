---
title: "10장. Spring AI로 만드는 생성형 AI 백엔드"
order: 10
tags: [spring-ai, java, llm, backend]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 10장. Spring AI로 만드는 생성형 AI 백엔드

## 들어가며

프롬프트 설계를 배웠으니, 이제 그것을 실제 Java 백엔드에 통합할 차례입니다. Spring AI는 OpenAI, Anthropic, Google 등 다양한 LLM을 하나의 인터페이스로 추상화합니다. 모델을 교체해도 코드는 바뀌지 않습니다.

---

## 이 챕터에서 배울 것

- **[10-1. Spring AI 개요와 모델 추상화](./10-1-spring-ai-overview.md)** — ChatClient 하나로 여러 모델을 같은 방식으로 다루는 구조
- **[10-2. ChatClient · 프롬프트 템플릿 · 구조화 출력](./10-2-chatclient.md)** — 프롬프트를 코드에서 안전하게 관리하고, 응답을 객체로 받는 방법
- **[10-3. ★ 엔터프라이즈 백엔드에 LLM 통합하기](./10-3-enterprise-integration.md)** — 비용·속도·신뢰성을 고려한 프로덕션 수준의 통합 패턴

---

> Spring AI는 LLM을 외부 서비스가 아니라 스프링 빈처럼 다룹니다. 나머지 스프링 생태계와 자연스럽게 연결됩니다.

이 챕터를 마치면 Spring Boot 애플리케이션에 LLM 기능을 통합하고, 프롬프트를 체계적으로 관리하며, 구조화된 응답을 Java 객체로 바로 받을 수 있습니다.
