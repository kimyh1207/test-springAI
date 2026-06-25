---
title: "21-1. 프로젝트를 문서/데모로 정리하는 법"
order: 211
tags: [portfolio, documentation, demo, readme, presentation]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 21-1. 프로젝트를 문서/데모로 정리하는 법

## 왜 문서가 코드만큼 중요한가

코드는 무엇을 했는지 보여준다. 문서는 왜 했는지를 설명한다. 채용 담당자와 동료는 대부분 문서를 먼저 본다.

```
채용 담당자가 보는 순서:
1. README (30초 이내 결정)
2. 데모 영상 또는 라이브 데모
3. 코드 구조 (디렉토리 구성)
4. 커밋 히스토리 (성장 과정)
5. 기술 상세 문서
```

---

## README 작성 원칙

좋은 README는 5분 안에 "이게 무엇인지, 어떻게 쓰는지, 왜 이 기술을 썼는지"를 전달한다.

```markdown
# 이커머스 고객 지원 AI 에이전트

> MCP + RAG + Claude를 결합한 풀스택 AI 고객 지원 시스템

[![CI](https://github.com/vivace/ecommerce-ai/actions/workflows/ci-cd.yml/badge.svg)](...)
[![Coverage](https://codecov.io/gh/vivace/ecommerce-ai/badge.svg)](...)

## 데모

[라이브 데모](https://demo.example.com) | [데모 영상 (3분)](https://youtube.com/...)

![데모 스크린샷](docs/images/demo.gif)

## 무엇을 해결하는가

이커머스 고객 문의의 70%는 반복적인 패턴(배송 조회, 반품 방법, 쿠폰 확인)이다.
이 시스템은 자연어로 들어오는 고객 문의를 AI 에이전트가 자동으로 처리한다.

## 핵심 기술

| 컴포넌트 | 기술 | 선택 이유 |
|----------|------|-----------|
| AI 모델 | Anthropic Claude | 도구 호출 정확도 최고 |
| 도구 표준화 | MCP (FastMCP) | 플랫폼 독립적 도구 재사용 |
| 문서 검색 | RAG (Chroma + LangChain) | 정책 문서 근거 기반 답변 |
| API 게이트웨이 | Spring Boot | 인증/속도 제한 안정성 |
| AI 서비스 | FastAPI | LLM SDK 생태계 |

## 시작하기

\`\`\`bash
# 1. 환경 설정
cp .env.example .env
# .env에 ANTHROPIC_API_KEY, OPENAI_API_KEY 입력

# 2. 실행
docker compose up -d

# 3. 데이터 초기화
docker compose exec ai-service python data/prepare_docs.py
docker compose exec ai-service python data/build_index.py

# 4. 확인
curl http://localhost:8080/actuator/health
\`\`\`

## 아키텍처

\`\`\`
React UI → Spring Boot → FastAPI → MCP Server → DB/벡터DB
\`\`\`

자세한 내용: [아키텍처 문서](docs/19-project-design/)

## 결과

- 반복 문의 자동 처리율: 78%
- 평균 응답 시간: 1.8초
- 에이전트 정확도: 84% (LLM judge 기준)
- 일일 API 비용: $3-5 (캐싱 적용 후)

## 라이선스

MIT
```

---

## 데모 준비

### 라이브 데모 시나리오

```
데모 3분 구성:

[0:00-0:30] 문제 소개
"고객 문의 담당자가 하루 200건 반복 질문을 받는다면?"

[0:30-1:30] 핵심 기능 시연
1. "ORD-2025-001 주문 어디 있어?" → 주문 조회 도구 호출 → 답변
2. "반품하고 싶은데 5일 됐어." → RAG 정책 검색 → 근거 포함 답변
3. "노트북 150만원 이하 추천해줘." → 상품 검색 → 필터된 결과

[1:30-2:30] 기술 구조 1슬라이드
"MCP로 도구를 표준화해서 Claude가 상황에 맞게 선택한다"

[2:30-3:00] 수치 결과
"78% 자동화, P95 2.1초, 일 $4 비용"
```

### 데모 영상 녹화 팁

```bash
# 터미널 세션 녹화 (asciinema)
asciinema rec demo.cast
# ... 데모 진행 ...
# Ctrl+D로 종료

# GIF 변환
agg demo.cast demo.gif --theme monokai

# 스크린 녹화 (OBS Studio 권장)
# 해상도: 1920x1080, 30fps, mp4
# 자막: 영어/한국어 두 버전
```

---

## 기술 블로그 포스트 구조

블로그는 "왜 이 선택을 했는가"를 중심으로 쓴다. 코드 설명보다 의사결정 과정이 독자에게 더 가치 있다.

```markdown
# MCP로 이커머스 AI 에이전트 만든 후기

## 문제 정의 (1단락)
반복 문의 자동화를 위해 AI 에이전트를 만들었다.
가장 큰 도전은 "도구를 어떻게 표준화할 것인가"였다.

## 핵심 기술 선택 (각 200자 이내)
- MCP를 선택한 이유: 도구를 한 번 만들어 여러 AI 클라이언트에서 재사용
- RAG를 선택한 이유: 정책 문서가 자주 바뀌므로 fine-tuning 대신 검색

## 실제로 어려웠던 것 (구체적 사례)
청크 크기를 잘못 설정했을 때 RAG가 엉뚱한 정책을 반환한 경험...

## 수치로 본 결과
Before/After 비교표

## 다음에 한다면 다르게 할 것
솔직한 회고

## 코드/레포 링크
```

---

## 포트폴리오 페이지 구성

```
포트폴리오 사이트 구성 예시:

프로젝트 카드:
┌─────────────────────────────┐
│  이커머스 AI 고객 지원       │
│  [이미지/GIF]                │
│  Python · Spring · Claude   │
│  [GitHub] [Demo] [블로그]   │
└─────────────────────────────┘

각 프로젝트에 반드시 포함:
  □ 한 줄 설명 (무엇을, 왜)
  □ 기술 스택 태그
  □ 핵심 수치 1-2개
  □ 링크 (코드, 데모, 글)
```

---

## GitHub 프로필 최적화

```markdown
<!-- README.md (github.com/username) -->
## vivace

풀스택 AI 에이전트를 만듭니다.
Python · Spring Boot · LLM · MCP

**최근 프로젝트:**
- [이커머스 AI 지원](링크) — MCP + RAG + Claude
- [ML 서빙 파이프라인](링크) — FastAPI + MLflow + Docker

**블로그:** [기술 블로그 링크]
```

```
커밋 히스토리가 보여주는 것:
  - 꾸준한 기여 (잔디밭)
  - 의미 있는 커밋 메시지
  - 점진적 개선 과정 (큰 커밋 하나보다 작은 커밋 여러 개)
```

> "코드는 당신이 할 수 있는 것을 보여주고, 문서는 당신이 생각하는 방식을 보여준다."
