---
title: "15-4. ★확장 — RAG 평가(정확도·환각·근거 추적)"
order: 4
tags: [rag-evaluation, hallucination, ragas, faithfulness]
status: draft
author: vivace
---

# 15-4. ★확장 — RAG 평가(정확도·환각·근거 추적)

RAG 파이프라인이 잘 작동하는지 어떻게 알 수 있을까요? "그럴듯한 답변"이 나오는 것은 평가가 아닙니다. 정량적 지표가 필요합니다.

---

## RAG 실패 유형

| 실패 유형 | 원인 | 증상 |
|----------|------|------|
| **검색 실패** | 관련 문서를 못 찾음 | 답변이 질문과 무관 |
| **환각** | 문서에 없는 내용을 생성 | 그럴듯하지만 틀린 답변 |
| **불완전한 답변** | top-k가 너무 작음 | 일부 정보만 포함 |
| **컨텍스트 오염** | 무관한 문서가 포함됨 | 혼재된 정보 |

---

## 평가 지표

### 1. Faithfulness (충실도)

답변이 검색된 문서 내용에 근거하는가.

```python
from anthropic import Anthropic

client = Anthropic()

def check_faithfulness(answer: str, context_docs: list[str]) -> float:
    context = "\n\n".join(context_docs)
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        temperature=0,
        messages=[{
            "role": "user",
            "content": f"""다음 답변의 각 주장이 참고 문서에 근거하는지 평가하세요.

[참고 문서]
{context}

[답변]
{answer}

평가 방법:
1. 답변의 핵심 주장을 목록으로 추출
2. 각 주장이 문서에 근거하는지 확인
3. 근거 있는 주장 수 / 전체 주장 수를 충실도 점수로 계산

JSON으로만 반환:
{{"claims": [{{"claim": "...", "supported": true/false}}], "faithfulness_score": 0.0~1.0}}"""
        }]
    )
    
    import json
    result = json.loads(response.content[0].text)
    return result["faithfulness_score"]
```

### 2. Answer Relevance (답변 관련성)

답변이 실제로 질문에 답하는가.

```python
def check_answer_relevance(question: str, answer: str) -> float:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        temperature=0,
        messages=[{
            "role": "user",
            "content": f"""다음 답변이 질문에 얼마나 관련성이 있는지 0~1 점수를 매기세요.

질문: {question}
답변: {answer}

기준:
- 1.0: 질문에 완전히 답함
- 0.5: 부분적으로 답함
- 0.0: 질문과 무관

JSON으로만 반환: {{"score": 0.0~1.0, "reason": "..."}}"""
        }]
    )
    
    import json
    result = json.loads(response.content[0].text)
    return result["score"]
```

### 3. Context Recall (컨텍스트 재현율)

정답에 필요한 정보가 검색된 문서에 포함되어 있는가.

```python
def check_context_recall(question: str, expected_answer: str, 
                          retrieved_docs: list[str]) -> float:
    context = "\n\n".join(retrieved_docs)
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        temperature=0,
        messages=[{
            "role": "user",
            "content": f"""예상 답변의 핵심 정보가 검색된 문서에 포함되어 있는지 평가하세요.

질문: {question}
예상 답변: {expected_answer}

[검색된 문서]
{context}

예상 답변의 각 핵심 정보가 문서에 있는 비율을 계산하세요.
JSON으로만 반환: {{"recall_score": 0.0~1.0}}"""
        }]
    )
    
    import json
    result = json.loads(response.content[0].text)
    return result["recall_score"]
```

---

## RAGAS — RAG 평가 프레임워크

```bash
pip install ragas langchain-openai
```

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision
)
from datasets import Dataset

# 평가 데이터셋
eval_data = {
    "question": [
        "환불 신청 기간은 얼마나 되나요?",
        "배송은 얼마나 걸리나요?",
        "포인트는 어떻게 적립되나요?"
    ],
    "answer": [
        "환불 신청은 구매 후 30일 이내에 가능합니다.",
        "결제 완료 후 2~3일 이내에 출발합니다.",
        "구매금액의 1%가 포인트로 적립됩니다."
    ],
    "contexts": [
        ["환불 신청은 구매 후 30일 이내에 가능합니다. 신청은 마이페이지에서..."],
        ["배송은 결제 완료 후 2~3일 이내 출발합니다. 도서 산간 지역은..."],
        ["포인트는 구매금액의 1%가 적립됩니다. 유효기간은 1년입니다."]
    ],
    "ground_truth": [
        "30일",
        "2~3일",
        "구매금액의 1%"
    ]
}

dataset = Dataset.from_dict(eval_data)

result = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy, context_recall, context_precision]
)

print(result)
# {'faithfulness': 0.92, 'answer_relevancy': 0.88, 
#  'context_recall': 0.95, 'context_precision': 0.83}
```

---

## 환각 감지 — 근거 추적

답변에서 각 문장의 근거 문서를 추적합니다.

```python
def generate_answer_with_citations(question: str, docs: list[Document]) -> dict:
    numbered_context = "\n\n".join(
        f"[{i+1}] {doc.page_content}" for i, doc in enumerate(docs)
    )
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        temperature=0,
        messages=[{
            "role": "user",
            "content": f"""다음 문서들을 참고해 질문에 답하세요.
각 주장 뒤에 출처 번호를 [1], [2] 형식으로 표시하세요.
문서에 없는 내용은 절대 포함하지 마세요.

[참고 문서]
{numbered_context}

질문: {question}

답변 (각 문장에 출처 번호 필수):"""
        }]
    )
    
    answer = response.content[0].text
    
    # 출처 파싱
    import re
    citations = re.findall(r'\[(\d+)\]', answer)
    cited_docs = [docs[int(c)-1] for c in set(citations) if int(c) <= len(docs)]
    
    return {
        "answer": answer,
        "cited_sources": [d.metadata.get("source", "?") for d in cited_docs],
        "uncited": len(cited_docs) == 0  # 출처 없이 생성된 경우
    }
```

---

## 지속적 평가 파이프라인

```python
import json
from datetime import datetime

def run_weekly_eval(chain, eval_questions: list[dict]) -> dict:
    scores = {"faithfulness": [], "relevance": []}
    
    for item in eval_questions:
        docs = chain.retriever.invoke(item["question"])
        answer = chain.invoke(item["question"])
        
        scores["faithfulness"].append(
            check_faithfulness(answer, [d.page_content for d in docs])
        )
        scores["relevance"].append(
            check_answer_relevance(item["question"], answer)
        )
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "faithfulness": sum(scores["faithfulness"]) / len(scores["faithfulness"]),
        "relevance": sum(scores["relevance"]) / len(scores["relevance"]),
        "sample_size": len(eval_questions)
    }
    
    # 임계값 이하 시 알림
    if report["faithfulness"] < 0.80:
        print(f"⚠️  환각 증가 감지: faithfulness={report['faithfulness']:.2f}")
    
    return report
```

---

## 평가 기준 요약

| 지표 | 목표 | 낮을 때 조치 |
|------|------|------------|
| Faithfulness | ≥ 0.85 | 프롬프트 강화, 청크 품질 개선 |
| Answer Relevance | ≥ 0.80 | 쿼리 변환, 검색 전략 수정 |
| Context Recall | ≥ 0.80 | top-k 증가, 청킹 전략 수정 |
| Context Precision | ≥ 0.75 | 리랭킹 추가, 메타데이터 필터 |

---

> 환각은 LLM이 자신 있게 틀리는 것입니다. Faithfulness를 측정하고 출처를 추적하면 환각을 구조적으로 줄일 수 있습니다.
