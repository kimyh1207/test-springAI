---
title: "9-4. ★확장 — 평가 가능한 프롬프트: 테스트와 회귀 방지"
order: 4
tags: [prompt-evaluation, testing, regression, llmops]
status: draft
author: vivace
---

# 9-4. ★확장 — 평가 가능한 프롬프트: 테스트와 회귀 방지

프롬프트를 바꾸면 모든 케이스에 어떤 영향이 있는지 알기 어렵습니다. 코드처럼 테스트 케이스를 만들고 회귀를 감지해야 합니다.

---

## 왜 프롬프트를 테스트해야 하는가

프롬프트는 코드입니다. 코드가 바뀌면 테스트를 돌리듯, 프롬프트가 바뀌면 검증이 필요합니다.

흔히 겪는 문제들:
- 특정 케이스에서만 잘 되던 프롬프트가 다른 케이스에서 망가짐
- 모델 버전 업데이트 후 출력 형식이 바뀜
- 프롬프트를 "개선"했더니 이전에 잘 되던 것이 안 됨

---

## 평가 데이터셋 구축

프롬프트를 평가하려면 기준이 있어야 합니다. 입력-기대 출력 쌍을 정의합니다.

```python
# 감성 분석 프롬프트 평가 데이터셋
eval_dataset = [
    {
        "input": "정말 최고의 제품이에요! 강력 추천합니다.",
        "expected_sentiment": "positive",
        "expected_score_min": 4
    },
    {
        "input": "배송이 늦고 포장이 엉망이었어요.",
        "expected_sentiment": "negative",
        "expected_score_max": 2
    },
    {
        "input": "보통이에요. 딱히 좋지도 나쁘지도 않아요.",
        "expected_sentiment": "neutral",
    },
    {
        "input": "처음엔 별로였는데 써보니 괜찮네요.",
        "expected_sentiment": "positive",  # 최종 감성
    },
]
```

---

## 자동화된 프롬프트 테스트

```python
import json
from anthropic import Anthropic

client = Anthropic()

SYSTEM_PROMPT = """당신은 리뷰 감성 분석기입니다. 반드시 JSON 형식으로만 답하세요.
{"sentiment": "positive"|"negative"|"neutral", "score": 1~5}"""

def run_sentiment_analysis(review: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=128,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": review}]
    )
    return json.loads(response.content[0].text)

def evaluate_prompt(dataset: list[dict]) -> dict:
    results = []
    
    for case in dataset:
        try:
            output = run_sentiment_analysis(case["input"])
            
            passed = True
            failures = []
            
            if "expected_sentiment" in case:
                if output["sentiment"] != case["expected_sentiment"]:
                    passed = False
                    failures.append(
                        f"sentiment: expected={case['expected_sentiment']}, got={output['sentiment']}"
                    )
            
            if "expected_score_min" in case:
                if output["score"] < case["expected_score_min"]:
                    passed = False
                    failures.append(
                        f"score too low: expected>={case['expected_score_min']}, got={output['score']}"
                    )
            
            if "expected_score_max" in case:
                if output["score"] > case["expected_score_max"]:
                    passed = False
                    failures.append(
                        f"score too high: expected<={case['expected_score_max']}, got={output['score']}"
                    )
            
            results.append({
                "input": case["input"][:40] + "...",
                "passed": passed,
                "failures": failures,
                "output": output
            })
        
        except Exception as e:
            results.append({
                "input": case["input"][:40] + "...",
                "passed": False,
                "failures": [f"Exception: {str(e)}"],
                "output": None
            })
    
    pass_count = sum(1 for r in results if r["passed"])
    
    return {
        "total": len(results),
        "passed": pass_count,
        "failed": len(results) - pass_count,
        "pass_rate": pass_count / len(results),
        "details": results
    }

report = evaluate_prompt(eval_dataset)
print(f"통과: {report['passed']}/{report['total']} ({report['pass_rate']:.0%})")
for detail in report["details"]:
    status = "✓" if detail["passed"] else "✗"
    print(f"  {status} {detail['input']}")
    if detail["failures"]:
        for f in detail["failures"]:
            print(f"      → {f}")
```

---

## A/B 테스트 — 어느 프롬프트가 나은가

프롬프트 두 버전을 동일한 데이터셋으로 평가해 비교합니다.

```python
PROMPT_A = """리뷰를 분석하고 JSON으로 답하세요.
{"sentiment": "positive"|"negative"|"neutral", "score": 1~5}"""

PROMPT_B = """당신은 감성 분석 전문가입니다.
다음 리뷰의 감성을 분석하세요.

긍정적 표현, 부정적 표현, 전반적 어조를 고려해
{"sentiment": "positive"|"negative"|"neutral", "score": 1~5} 형식으로만 답하세요."""

def compare_prompts(dataset: list[dict], prompt_a: str, prompt_b: str):
    results_a = []
    results_b = []
    
    for case in dataset:
        for prompt, results in [(prompt_a, results_a), (prompt_b, results_b)]:
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=128,
                    temperature=0,
                    system=prompt,
                    messages=[{"role": "user", "content": case["input"]}]
                )
                output = json.loads(response.content[0].text)
                correct = output["sentiment"] == case.get("expected_sentiment")
                results.append(correct)
            except:
                results.append(False)
    
    acc_a = sum(results_a) / len(results_a)
    acc_b = sum(results_b) / len(results_b)
    
    print(f"Prompt A 정확도: {acc_a:.0%}")
    print(f"Prompt B 정확도: {acc_b:.0%}")
    print(f"승자: {'A' if acc_a >= acc_b else 'B'}")

compare_prompts(eval_dataset, PROMPT_A, PROMPT_B)
```

---

## CI 파이프라인에 통합

프롬프트를 변경할 때마다 자동으로 평가를 돌립니다.

```yaml
# .github/workflows/prompt-eval.yml
name: Prompt Evaluation

on:
  pull_request:
    paths:
      - 'prompts/**'
      - 'src/**/*prompt*'

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install anthropic pytest
      
      - name: Run prompt evaluation
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python eval/run_eval.py --min-pass-rate 0.85
      
      - name: Comment results on PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('eval/report.json'));
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## 프롬프트 평가 결과\n통과: ${report.passed}/${report.total} (${Math.round(report.pass_rate*100)}%)`
            });
```

---

## 평가 지표 정리

| 지표 | 설명 | 기준 |
|------|------|------|
| 정확도(Accuracy) | 기대 출력과 일치율 | ≥ 85% |
| 형식 준수율 | JSON 파싱 성공률 | ≥ 99% |
| 지연 시간(Latency) | 평균 응답 시간 | ≤ 3초 |
| 비용 | 케이스당 토큰 수 | 예산 내 |

---

> 프롬프트를 "한 번 쓰고 끝"으로 취급하지 마세요. 데이터셋을 쌓고, 테스트를 자동화하고, 변경할 때마다 검증하는 것이 프로덕션 수준의 LLM 개발입니다.
