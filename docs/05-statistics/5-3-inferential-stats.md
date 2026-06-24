---
title: "5-3. 추론통계의 직관(표본·가설·검정)"
order: 3
tags: [statistics, hypothesis-testing]
status: draft
author: vivace
---

# 5-3. 추론통계의 직관(표본 · 가설 · 검정)

전체를 다 보는 것은 불가능할 때가 많습니다. 설문을 전 국민에게 할 수 없고, A/B 테스트를 모든 사용자에게 할 수 없습니다. **일부(표본)를 보고 전체(모집단)에 대해 말하는 것**이 추론통계입니다.

---

## 표본과 모집단

**모집단(Population)** — 관심 대상 전체. 전 국민, 모든 사용자.

**표본(Sample)** — 모집단에서 뽑은 일부. 1,000명 설문, 10% 사용자 A/B 테스트.

표본이 모집단을 잘 대표하려면 **무작위 추출**이 필요합니다. 특정 그룹에 편향된 표본으로 내린 결론은 모집단에 적용할 수 없습니다.

```
잘못된 표본의 예:
  "서비스 만족도 조사" → 적극적으로 답변하는 사람만 응답
  → 불만족 사용자는 대부분 무응답 → 결과가 편향됨
```

---

## 가설 검정의 논리

가설 검정은 "이 차이가 우연인가, 진짜인가"를 판단합니다.

### 귀무가설과 대립가설

```
귀무가설(H₀): 차이가 없다 / 효과가 없다
대립가설(H₁): 차이가 있다 / 효과가 있다
```

예시: 버튼 색상 변경이 클릭률에 영향을 주는가?
```
H₀: 빨간 버튼과 파란 버튼의 클릭률은 같다
H₁: 두 버튼의 클릭률은 다르다
```

---

## p값 — 가장 많이 오해되는 통계 개념

**p값**은 "귀무가설이 사실일 때, 이 정도 또는 더 극단적인 결과가 나올 확률"입니다.

```
p값이 작다 (p < 0.05):
  귀무가설이 사실이라면 이런 결과는 매우 드물다
  → 귀무가설을 기각: 차이가 있다고 판단

p값이 크다 (p ≥ 0.05):
  이 결과는 우연으로도 충분히 나올 수 있다
  → 귀무가설 기각 실패: 차이가 있다고 말할 수 없다
```

**흔한 오해**: p < 0.05면 "차이가 크다"는 뜻이 아닙니다. 표본이 충분히 크면 아주 작은 차이도 통계적으로 유의미해집니다. **통계적 유의미함 ≠ 실질적 유의미함**.

---

## A/B 테스트 — 실무에서 가장 많이 쓰는 가설 검정

A/B 테스트는 두 버전을 동시에 테스트해 어느 쪽이 나은지 판단합니다.

```python
import scipy.stats as stats
import numpy as np

# A 그룹: 기존 버튼 (파란색)
# B 그룹: 새 버튼 (빨간색)
a_clicks = 234   # A 그룹 클릭 수
a_total  = 2000  # A 그룹 노출 수
b_clicks = 267   # B 그룹 클릭 수
b_total  = 2000  # B 그룹 노출 수

a_rate = a_clicks / a_total  # 0.117 (11.7%)
b_rate = b_clicks / b_total  # 0.134 (13.4%)

print(f"A 클릭률: {a_rate:.1%}")
print(f"B 클릭률: {b_rate:.1%}")
print(f"상대적 개선: {(b_rate - a_rate) / a_rate:.1%}")

# 카이제곱 검정
from scipy.stats import chi2_contingency

table = [[a_clicks, a_total - a_clicks],
         [b_clicks, b_total - b_clicks]]
chi2, p, dof, expected = chi2_contingency(table)

print(f"\np값: {p:.4f}")
if p < 0.05:
    print("결론: 두 버전의 클릭률 차이는 통계적으로 유의미합니다.")
    print("B 버전(빨간 버튼)이 더 효과적입니다.")
else:
    print("결론: 차이가 우연일 가능성이 높습니다. 계속 관찰이 필요합니다.")
```

### A/B 테스트 주의사항

```
□ 동시에 실행: A를 월요일, B를 화요일에 테스트하면 요일 효과가 섞임
□ 충분한 표본: 표본이 작으면 p값이 신뢰할 수 없음
□ 하나만 바꾸기: 버튼 색상 + 문구를 동시에 바꾸면 무엇이 효과인지 모름
□ 조기 종료 금지: p < 0.05가 되는 순간 종료하면 거짓 양성 위험
□ 실질적 효과 확인: 클릭률 0.1% 차이가 비즈니스에 의미 있는가
```

---

## t검정 — 두 그룹의 평균 비교

두 그룹의 평균이 통계적으로 다른지 검정합니다.

```python
# 두 그룹의 구매금액 비교
group_a = [45, 52, 38, 61, 48, 55, 42, 58, 49, 51]  # 기존 UI
group_b = [58, 67, 54, 72, 63, 69, 55, 74, 61, 68]  # 새 UI

t_stat, p_value = stats.ttest_ind(group_a, group_b)

print(f"A 평균: {np.mean(group_a):.1f}원")
print(f"B 평균: {np.mean(group_b):.1f}원")
print(f"p값: {p_value:.4f}")

if p_value < 0.05:
    print("두 그룹의 평균 구매금액은 유의미하게 다릅니다.")
```

---

## 신뢰구간 — 범위로 불확실성을 표현

점 추정(하나의 숫자)보다 신뢰구간이 더 정직합니다.

```python
import scipy.stats as stats

sample = [45, 52, 38, 61, 48, 55, 42, 58, 49, 51]
n = len(sample)
mean = np.mean(sample)
se = stats.sem(sample)  # 표준 오차

# 95% 신뢰구간
ci = stats.t.interval(0.95, df=n-1, loc=mean, scale=se)
print(f"평균: {mean:.1f}")
print(f"95% 신뢰구간: {ci[0]:.1f} ~ {ci[1]:.1f}")
# 평균: 49.9
# 95% 신뢰구간: 44.2 ~ 55.6
```

"평균 구매금액은 49.9원입니다"보다 "44~56원 사이일 가능성이 95%입니다"가 더 정직한 표현입니다.

---

> 통계는 확실성을 주는 도구가 아닙니다. 불확실성을 정량화하는 도구입니다. "모른다"를 얼마나 정밀하게 말할 수 있는가가 통계의 가치입니다.

---

## 실습

```python
# 온라인 쇼핑몰 A/B 테스트 시뮬레이션

import numpy as np
from scipy.stats import chi2_contingency
np.random.seed(42)

# 가상 데이터: 기존 상품 페이지(A) vs 개선된 상품 페이지(B)
n = 5000
a_converted = np.random.binomial(n, 0.032)  # 기존 전환율 3.2%
b_converted = np.random.binomial(n, 0.038)  # 개선 전환율 3.8%

print(f"A 전환율: {a_converted/n:.1%}")
print(f"B 전환율: {b_converted/n:.1%}")

table = [[a_converted, n - a_converted],
         [b_converted, n - b_converted]]
_, p, _, _ = chi2_contingency(table)

print(f"p값: {p:.4f}")
print("유의미한 차이?" , "예" if p < 0.05 else "아니오")

# 도전: n을 500으로 줄이면 같은 결론이 나오는가?
# 표본 크기가 결론에 어떤 영향을 미치는지 확인해보세요.
```
