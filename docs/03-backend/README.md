---
title: "3장. 백엔드: Java · Spring Boot · REST API"
order: 3
tags: [java, spring-boot, rest-api]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 3장. 백엔드: Java · Spring Boot · REST API

## 들어가며

백엔드는 사용자가 보지 못하는 곳에서 서비스를 움직이는 엔진입니다. 데이터를 저장하고, 요청을 처리하고, 결과를 돌려줍니다. Spring Boot는 그 엔진을 빠르게 만드는 도구입니다.

Java와 Spring Boot는 여전히 국내 기업 백엔드의 주류입니다. 배우는 데 시간이 걸리지만, 한 번 익히면 어떤 규모의 서비스도 다룰 수 있습니다.

---

## 이 챕터에서 배울 것

- **[3-1. Spring Boot 프로젝트 구조와 의존성 관리](./3-1-project-structure.md)** — 프로젝트가 어떻게 구성되는지 알아야 길을 잃지 않는다
- **[3-2. 계층형 아키텍처(Controller · Service · Repository)](./3-2-layered-architecture.md)** — 역할을 나누는 것이 유지보수의 시작이다
- **[3-3. REST API 설계 원칙과 DTO/엔티티 분리](./3-3-rest-api.md)** — 좋은 API는 사용하는 사람이 문서 없이도 예측할 수 있다
- **[3-4. 데이터 영속성(JPA)과 트랜잭션](./3-4-jpa.md)** — SQL 없이 객체로 데이터베이스를 다루는 방법
- **[3-5. 예외 처리 · 검증 · API 문서화(Swagger)](./3-5-exception-swagger.md)** — 오류도 API의 일부다. 일관되게 처리해야 한다
- **[3-6. ★ 인증/인가(JWT) · 테스트 코드 · 환경 분리](./3-6-jwt-test.md)** — 실무 서비스가 갖춰야 할 세 가지 기반

---

> 좋은 백엔드는 프론트엔드가 고민할 필요 없게 만드는 백엔드입니다. 명확한 API, 일관된 오류 응답, 예측 가능한 동작.

이 챕터를 마치면 회원가입·로그인·데이터 조회가 가능한 REST API 서버를 혼자 만들 수 있습니다. 이후 AI 기능을 붙이는 것도 이 위에서 시작됩니다.
