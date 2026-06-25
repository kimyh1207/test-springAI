---
title: "7-1. 피처의 종류와 생성 전략"
order: 1
tags: [feature-engineering, feature-types, machine-learning]
status: draft
author: vivace
---

# 7-1. 피처의 종류와 생성 전략

피처(feature)는 모델이 학습에 사용하는 입력 변수입니다. 원시 데이터에 있는 컬럼 그대로 쓰는 경우는 드뭅니다. 대부분은 가공이 필요합니다.

---

## 피처의 종류

### 수치형(Numerical)

연속값 또는 이산값을 가집니다.

| 유형 | 예 | 특징 |
|------|-----|------|
| 연속형 | 나이, 소득, 온도 | 실수, 범위 무한 |
| 이산형 | 구매 횟수, 리뷰 수 | 정수, 셀 수 있음 |

수치형은 스케일이 다를 경우 정규화가 필요합니다. 나이(0~100)와 소득(0~10,000만)을 그대로 넣으면 소득이 학습을 지배합니다.

### 범주형(Categorical)

고정된 집합 중 하나의 값을 가집니다.

| 유형 | 예 | 특징 |
|------|-----|------|
| 명목형(Nominal) | 성별, 도시, 색상 | 순서 없음 |
| 순서형(Ordinal) | 학력, 등급(S/A/B/C) | 순서 있음 |

범주형은 모델이 직접 처리할 수 없습니다. 숫자로 변환해야 합니다(다음 절에서 다룹니다).

### 불리언(Boolean)

True/False, 0/1. 이진 분류 레이블이나 플래그 변수에 자주 쓰입니다.

```python
df['is_premium'] = df['plan'] == 'premium'  # bool
df['has_discount'] = df['discount_rate'] > 0
```

---

## 좋은 피처의 조건

피처를 만들기 전에 이 세 가지를 물어보세요.

1. **예측과 관련 있는가?** — 무관한 피처는 노이즈입니다. 모델의 일반화를 방해합니다.
2. **누수(leakage)가 없는가?** — 정답이 피처 안에 포함되어 있으면 훈련 시에는 완벽하지만 실전에서는 작동하지 않습니다.
3. **훈련-서빙 시점이 동일한가?** — 모델을 훈련할 때와 실제 예측할 때 피처를 같은 방식으로 계산할 수 있어야 합니다.

---

## 피처 중요도 — 어떤 피처가 효과적인가

피처가 너무 많으면 모델이 과적합됩니다. 중요도가 낮은 피처를 제거하면 성능과 속도 모두 개선됩니다.

```python
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
import matplotlib.pyplot as plt

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

importances = pd.Series(model.feature_importances_, index=X_train.columns)
importances.sort_values(ascending=False).head(10).plot(kind='bar')
plt.title('Feature Importances')
plt.tight_layout()
plt.show()
```

상위 피처가 무엇인지 확인하면 도메인 이해도 깊어집니다. 예상과 다른 피처가 상위에 있다면 누수를 의심해야 합니다.

---

## 피처 생성 전략

### 1. 도메인 지식 기반

"이 업무를 잘 아는 사람이라면 어떤 정보를 볼까?"에서 시작합니다.

```python
# 전자상거래: 최근성(Recency), 빈도(Frequency), 금액(Monetary) — RFM
df['days_since_last_purchase'] = (today - df['last_purchase_date']).dt.days
df['purchase_frequency'] = df['total_orders'] / df['customer_age_days']
df['avg_order_value'] = df['total_revenue'] / df['total_orders']
```

### 2. 통계 기반 집계

그룹별 집계값을 새 피처로 추가합니다.

```python
# 사용자별 평균 구매금액을 상품 데이터에 조인
user_stats = df.groupby('user_id')['order_amount'].agg(['mean', 'std', 'count'])
user_stats.columns = ['user_avg_amount', 'user_std_amount', 'user_order_count']
df = df.merge(user_stats, on='user_id', how='left')
```

### 3. 비율 · 차이

절대값보다 비율이 더 유용한 경우가 많습니다.

```python
df['ctr'] = df['clicks'] / df['impressions']          # 클릭률
df['conversion_rate'] = df['purchases'] / df['clicks'] # 전환율
df['price_discount_ratio'] = df['discount'] / df['original_price']
```

---

## 수치형 피처 변환

### 로그 변환 — 극단값과 왜도 완화

소득, 거래금액처럼 오른쪽으로 치우친 분포는 로그를 취하면 정규분포에 가까워집니다.

```python
import numpy as np

df['log_income'] = np.log1p(df['income'])  # log(1 + x): 0값 안전 처리
```

### 구간화(Binning) — 연속값을 범주로

나이를 10대/20대/30대로 나누는 것처럼, 연속값을 구간으로 묶으면 비선형 관계를 포착하기 쉽습니다.

```python
df['age_group'] = pd.cut(
    df['age'],
    bins=[0, 20, 30, 40, 50, 100],
    labels=['10대이하', '20대', '30대', '40대', '50대이상']
)
```

---

## 피처 선택

피처를 무한정 만들어도 의미 없습니다. 선택이 중요합니다.

```python
from sklearn.feature_selection import SelectKBest, f_classif

# 분류 문제에서 ANOVA F-통계량 기반으로 상위 K개 선택
selector = SelectKBest(score_func=f_classif, k=10)
X_selected = selector.fit_transform(X_train, y_train)

# 선택된 피처 이름 확인
selected_cols = X_train.columns[selector.get_support()]
print(selected_cols.tolist())
```

---

> 피처 엔지니어링에서 가장 흔한 실수는 너무 많이 만드는 것입니다. 10개의 좋은 피처가 100개의 무관한 피처보다 낫습니다.
