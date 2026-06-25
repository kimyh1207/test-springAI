---
title: "18-1. 캡스톤 설계: 문제·도구·데이터·평가"
order: 181
tags: [capstone, agent-design, mcp, rag, system-design]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 18-1. 캡스톤 설계: 문제·도구·데이터·평가

## 무엇을 만드는가

이 챕터는 책 전체를 관통하는 기술 스택을 하나의 시스템으로 통합한다.

**목표**: 이커머스 고객 지원 AI 에이전트
- 고객 질문을 받아 주문/상품/정책 정보를 조회
- RAG로 FAQ·약관 문서에서 근거를 찾아 답변
- MCP 서버로 도구를 표준화하여 여러 클라이언트에서 재사용

```
┌─────────────────────────────────────────────────────────┐
│               이커머스 고객 지원 에이전트                  │
│                                                         │
│  사용자 질문                                             │
│      │                                                  │
│      ▼                                                  │
│  ┌──────────┐    ┌─────────────┐    ┌────────────────┐  │
│  │ Orchestr │───►│  MCP Server │───►│  실제 시스템    │  │
│  │  ator    │    │             │    │  - DB (주문)    │  │
│  │ (Claude) │◄───│  Tools:     │    │  - 상품 API     │  │
│  └──────────┘    │  - 주문조회  │    │  - 정책 문서    │  │
│      │           │  - 상품검색  │    └────────────────┘  │
│      │           │  - FAQ RAG  │                        │
│      │           └─────────────┘                        │
│      │                                                  │
│      ▼                                                  │
│  최종 답변 (근거 포함)                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 해결할 시나리오

구체적인 사용자 시나리오 5가지를 정의한다.

```python
TEST_SCENARIOS = [
    {
        "id": "S1",
        "query": "ORD-2025-001 주문이 언제 도착해?",
        "expected_tools": ["get_order_status"],
        "success_criteria": "배송 예정일 포함"
    },
    {
        "id": "S2",
        "query": "노트북 추천해줘. 예산은 150만원이야.",
        "expected_tools": ["search_products"],
        "success_criteria": "가격 범위 필터 적용, 3개 이상 추천"
    },
    {
        "id": "S3",
        "query": "반품 신청하려면 어떻게 해? 배송 받은 지 5일 됐어.",
        "expected_tools": ["search_policy_docs"],
        "success_criteria": "반품 정책 근거 인용"
    },
    {
        "id": "S4",
        "query": "쿠폰 SAVE20 아직 유효해?",
        "expected_tools": ["check_coupon"],
        "success_criteria": "유효/만료 여부 명시"
    },
    {
        "id": "S5",
        "query": "지난달에 산 에어팟 AS 받고 싶어.",
        "expected_tools": ["get_order_status", "search_policy_docs"],
        "success_criteria": "주문 확인 + AS 정책 안내"
    }
]
```

---

## 도구 설계

에이전트가 사용할 도구 5개를 설계한다.

```python
TOOL_SPECS = {
    "get_order_status": {
        "description": "주문 ID로 배송 현황 조회",
        "input": {"order_id": "string"},
        "output": "배송 단계, 추적 번호, 예상 도착일",
        "latency_sla": "200ms",
        "data_source": "주문 DB"
    },
    "search_products": {
        "description": "상품명/카테고리/가격 범위로 상품 검색",
        "input": {
            "query": "string",
            "max_price": "integer (optional)",
            "category": "string (optional)"
        },
        "output": "상품 목록 (이름, 가격, 평점, 재고)",
        "latency_sla": "300ms",
        "data_source": "상품 DB + 검색 인덱스"
    },
    "search_policy_docs": {
        "description": "FAQ, 반품/교환/AS 정책 문서 RAG 검색",
        "input": {
            "query": "string",
            "doc_type": "string (faq|return|warranty|shipping)"
        },
        "output": "관련 정책 텍스트 + 출처",
        "latency_sla": "500ms",
        "data_source": "벡터 DB (Chroma)"
    },
    "check_coupon": {
        "description": "쿠폰 코드 유효성 및 조건 확인",
        "input": {"coupon_code": "string"},
        "output": "유효 여부, 할인율, 만료일, 적용 조건",
        "latency_sla": "100ms",
        "data_source": "프로모션 DB"
    },
    "get_customer_profile": {
        "description": "인증된 고객의 구매 이력 및 등급 조회",
        "input": {"customer_id": "string"},
        "output": "등급, 포인트, 최근 구매 목록",
        "latency_sla": "150ms",
        "data_source": "CRM DB"
    }
}
```

---

## 데이터 준비

### 정책 문서 (RAG 대상)

```python
# data/prepare_docs.py
from pathlib import Path

POLICY_DOCS = {
    "return_policy.md": """
# 반품/교환 정책

## 반품 가능 기간
- 수령 후 7일 이내 반품 가능
- 단순 변심: 배송비 고객 부담
- 상품 하자: 배송비 회사 부담

## 반품 불가 상품
- 식품류, 소모품 개봉 후
- 고객 과실로 파손된 상품
- 주문 제작 상품

## 반품 신청 방법
1. 마이페이지 → 주문내역 → 반품 신청
2. 사유 선택 후 사진 첨부
3. 수거 일정 조율 (1-2 영업일 내)
""",
    "shipping_policy.md": """
# 배송 정책

## 기본 배송
- 무료 배송: 50,000원 이상
- 기본 배송비: 3,000원
- 도서산간: 추가 3,000원

## 배송 기간
- 일반 상품: 2-3 영업일
- 새벽 배송: 오후 11시 이전 주문 시 다음날 오전 7시 이전
- 예약 배송: 원하는 날짜 지정 가능
""",
    "warranty_policy.md": """
# AS/보증 정책

## 보증 기간
- 전자제품: 구매일로부터 1년
- 의류/잡화: 6개월
- 가구: 2년

## AS 신청 방법
1. 고객센터 1588-0000 (평일 9-18시)
2. 온라인: 마이페이지 → AS 신청
3. 방문: 전국 서비스센터

## AS 불가 사항
- 소비자 과실 (낙하, 침수, 임의 분해)
- 보증 기간 초과
"""
}

def prepare_policy_docs():
    docs_dir = Path("data/policy_docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    for filename, content in POLICY_DOCS.items():
        (docs_dir / filename).write_text(content, encoding="utf-8")
    
    print(f"정책 문서 {len(POLICY_DOCS)}개 생성 완료")

if __name__ == "__main__":
    prepare_policy_docs()
```

### 벡터 DB 인덱싱

```python
# data/build_index.py
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

def build_policy_index():
    loader = DirectoryLoader(
        "data/policy_docs",
        glob="*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    docs = loader.load()
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(docs)
    
    # 메타데이터 추가
    for chunk in chunks:
        source = chunk.metadata.get("source", "")
        if "return" in source:
            chunk.metadata["doc_type"] = "return"
        elif "shipping" in source:
            chunk.metadata["doc_type"] = "shipping"
        elif "warranty" in source:
            chunk.metadata["doc_type"] = "warranty"
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
        persist_directory="data/chroma_db",
        collection_name="policy_docs"
    )
    
    print(f"인덱싱 완료: {len(chunks)}개 청크")
    return vectorstore

if __name__ == "__main__":
    build_policy_index()
```

---

## 평가 기준

```python
# evaluation/criteria.py
from dataclasses import dataclass
from enum import Enum

class EvalDimension(Enum):
    TOOL_SELECTION = "tool_selection"    # 올바른 도구를 선택했는가
    ANSWER_ACCURACY = "answer_accuracy"  # 답변이 정확한가
    CITATION = "citation"               # 근거를 인용했는가
    CONCISENESS = "conciseness"         # 답변이 간결한가
    LATENCY = "latency"                 # 응답 시간이 SLA 내인가

@dataclass
class EvalResult:
    scenario_id: str
    tool_selection_score: float   # 0-1
    answer_accuracy_score: float  # 0-1 (LLM judge)
    has_citation: bool
    response_time_ms: float
    passed: bool
    
    @property
    def overall_score(self) -> float:
        weights = {
            "tool": 0.3,
            "accuracy": 0.4,
            "citation": 0.2,
            "latency": 0.1
        }
        latency_score = 1.0 if self.response_time_ms < 3000 else 0.5
        citation_score = 1.0 if self.has_citation else 0.0
        
        return (
            weights["tool"] * self.tool_selection_score +
            weights["accuracy"] * self.answer_accuracy_score +
            weights["citation"] * citation_score +
            weights["latency"] * latency_score
        )

# 통과 기준
PASS_THRESHOLD = 0.75
LATENCY_SLA_MS = 5000
```

---

## 프로젝트 구조

```
capstone/
├── data/
│   ├── policy_docs/       # 정책 문서 Markdown
│   ├── chroma_db/         # 벡터 DB
│   └── prepare_docs.py
│   └── build_index.py
├── mcp_server/
│   ├── server.py          # FastMCP 서버
│   └── tools/
│       ├── orders.py
│       ├── products.py
│       ├── policy_rag.py
│       └── coupons.py
├── agent/
│   ├── orchestrator.py    # 메인 에이전트 루프
│   └── prompts.py
├── evaluation/
│   ├── criteria.py
│   ├── runner.py
│   └── scenarios.py
├── api/
│   └── app.py             # FastAPI 엔드포인트
└── docker-compose.yml
```

> "설계가 절반이다 — 도구 경계를 명확히 그으면 구현은 따라온다."
