---
title: "5-2. 기술통계 · 분포 · 상관"
order: 2
tags: [statistics, distribution]
status: draft
author: vivace
---

# 5-2. 기술통계 · 분포 · 상관

데이터를 처음 받았을 때 무엇을 먼저 봐야 할까요. 기술통계입니다. 평균, 분산, 분포. 이 세 가지가 데이터의 전체 그림을 그려줍니다.

---

## 기술통계 — 데이터를 숫자로 요약하기

### 중심 경향값

데이터가 어디에 몰려 있는지 나타냅니다.

| 지표 | 정의 | 특징 |
|------|------|------|
| **평균(Mean)** | 전체 합 ÷ 개수 | 이상값에 민감 |
| **중앙값(Median)** | 정렬 후 가운데 값 | 이상값에 강건 |
| **최빈값(Mode)** | 가장 자주 나오는 값 | 범주형 데이터에 유용 |

```python
import pandas as pd
import numpy as np

data = [10, 12, 13, 14, 15, 15, 16, 18, 100]  # 100은 이상값

print(f"평균: {np.mean(data):.1f}")      # 23.7  ← 이상값에 끌려감
print(f"중앙값: {np.median(data):.1f}")  # 15.0  ← 이상값 영향 적음
```

연봉 데이터에서 "평균 연봉 5,000만 원"이 왜 체감과 다른지. 극소수의 고연봉이 평균을 끌어올리기 때문입니다. 이런 경우 중앙값이 더 대표성 있습니다.

### 산포도 — 데이터가 얼마나 퍼져 있는가

```python
data = pd.Series([10, 12, 13, 14, 15, 15, 16, 18, 20])

print(f"범위(Range): {data.max() - data.min()}")  # 10
print(f"분산(Variance): {data.var():.2f}")         # 9.25
print(f"표준편차(Std): {data.std():.2f}")          # 3.04
print(f"IQR: {data.quantile(0.75) - data.quantile(0.25)}")  # 3.5
```

**표준편차**는 "평균으로부터 평균적으로 얼마나 떨어져 있는가"입니다. 표준편차가 크면 데이터가 넓게 퍼져 있고, 작으면 평균 근처에 몰려 있습니다.

**IQR(사분위 범위)** 은 하위 25%~상위 75% 구간의 폭입니다. 이상값에 강건합니다. 이상값 탐지에 주로 씁니다.

---

## 분포 — 데이터의 형태 읽기

### 정규분포

자연에서 가장 흔하게 나타나는 분포입니다. 평균을 중심으로 좌우 대칭인 종 모양입니다.

```
       ┌─────┐
      ┌┘     └┐
     ┌┘       └┐
    ┌┘         └┐
───┘─────────────└───
  -3σ -2σ -1σ μ 1σ 2σ 3σ

μ ± 1σ : 약 68% 포함
μ ± 2σ : 약 95% 포함
μ ± 3σ : 약 99.7% 포함
```

정규분포의 이 성질을 **68-95-99.7 규칙**이라 합니다. 머신러닝에서 정규화, 이상값 탐지 등에 활용합니다.

### 왜도(Skewness) — 분포의 치우침

```python
import scipy.stats as stats

right_skewed = [1, 1, 2, 2, 2, 3, 3, 5, 10, 50]  # 오른쪽 꼬리
print(f"왜도: {stats.skew(right_skewed):.2f}")     # 양수 → 오른쪽 꼬리

# 왜도 > 0: 오른쪽 꼬리 (연봉, 집값 등)
# 왜도 < 0: 왼쪽 꼬리
# 왜도 ≈ 0: 대칭
```

왜도가 크면 로그 변환을 통해 정규분포에 가깝게 만들 수 있습니다. 머신러닝 모델의 성능이 올라가는 경우가 많습니다.

```python
import numpy as np
df['log_price'] = np.log1p(df['price'])  # log(1+x): 0값 처리 포함
```

---

## 상관 — 두 변수가 함께 움직이는가

상관계수(r)는 두 변수의 선형 관계 강도를 -1에서 1 사이로 나타냅니다.

```
r =  1.0 : 완전 양의 상관 (한 쪽 오르면 다른 쪽도 오름)
r =  0.7 : 강한 양의 상관
r =  0.3 : 약한 양의 상관
r =  0.0 : 상관 없음
r = -0.3 : 약한 음의 상관
r = -0.7 : 강한 음의 상관
r = -1.0 : 완전 음의 상관
```

```python
import seaborn as sns
import matplotlib.pyplot as plt

# 상관계수 계산
correlation = df[['age', 'income', 'purchase_amount']].corr()
print(correlation)

# 히트맵으로 시각화
sns.heatmap(correlation, annot=True, cmap='coolwarm', vmin=-1, vmax=1)
plt.title('변수 간 상관관계')
plt.show()
```

### 상관과 인과를 구별해야 한다

상관관계는 인과관계가 아닙니다.

```
아이스크림 판매량 ↑  →  익사 사고 ↑

상관관계: 있음
인과관계: 없음 (둘 다 여름에 올라가는 것, 서로 원인이 아님)
```

데이터에서 상관을 발견했을 때 "A가 B를 유발한다"고 단정하면 안 됩니다. 제3의 변수(교란변수)가 있을 수 있습니다.

---

## pandas로 기술통계 한번에

```python
df = pd.read_csv('sales.csv')

# 수치형 컬럼 전체 요약
print(df.describe())
#        age    income  purchase
# count  1000    1000      1000
# mean   34.2   52000     128.5
# std    10.1   25000      89.3
# min    18.0   15000       0.0
# 25%    26.0   35000      55.0
# 50%    33.0   48000     102.0
# 75%    42.0   65000     178.0
# max    65.0  250000     999.0

# 범주형 컬럼 요약
print(df['country'].value_counts())
print(df['country'].value_counts(normalize=True))  # 비율로
```

`describe()`의 출력 하나만 봐도 이상값(max가 mean보다 훨씬 크면), 결측값(count가 작으면), 분포의 치우침(mean과 50%가 많이 다르면)을 빠르게 파악할 수 있습니다.

---

> 평균만 보는 것은 지도 없이 목적지를 찾는 것과 같습니다. 분포를 봐야 데이터가 어디에 있는지 보입니다.

---

## 실습

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 실습 데이터 생성 (또는 Titanic, Housing 등 공개 데이터 활용)
np.random.seed(42)
df = pd.DataFrame({
    'age': np.random.normal(35, 10, 1000).clip(18, 70),
    'income': np.random.exponential(50000, 1000),
    'score': np.random.normal(70, 15, 1000).clip(0, 100)
})

# 1. describe()로 전체 요약
print(df.describe())

# 2. 각 컬럼의 히스토그램
df.hist(bins=30, figsize=(12, 4))
plt.tight_layout()
plt.show()

# 3. income의 왜도 확인 후 로그 변환
print(f"income 왜도: {df['income'].skew():.2f}")
df['log_income'] = np.log1p(df['income'])
print(f"log_income 왜도: {df['log_income'].skew():.2f}")

# 4. 상관 히트맵
import seaborn as sns
sns.heatmap(df.corr(), annot=True, cmap='coolwarm')
plt.show()
```
