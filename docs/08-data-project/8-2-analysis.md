---
title: "8-2. 전처리 → 분석 → 인사이트 도출"
order: 2
tags: [preprocessing, eda, insight, data-analysis]
status: draft
author: vivace
---

# 8-2. 전처리 → 분석 → 인사이트 도출

계획이 있으면 실행입니다. 데이터를 정제하고, 패턴을 찾고, 그것을 이야기로 만드는 과정을 단계별로 따라갑니다.

---

## 1단계: 데이터 정제

### 결측값 처리

```python
import pandas as pd
import numpy as np

df = pd.read_csv('E Commerce.csv')

# 결측값 현황 파악
print(df.isnull().sum()[df.isnull().sum() > 0])
# Tenure                   264
# WarehouseToHome           251
# HoursSpentOnApp           255
# OrderAmountHikeFromlastYear  265
# CouponUsed               256
# OrderCount               258
# DaySinceLastOrder        307

# 수치형 결측값: 중앙값으로 대체
numeric_cols_with_na = [
    'Tenure', 'WarehouseToHome', 'HoursSpentOnApp',
    'OrderAmountHikeFromlastYear', 'CouponUsed', 'OrderCount', 'DaySinceLastOrder'
]
for col in numeric_cols_with_na:
    df[col] = df[col].fillna(df[col].median())

print(df.isnull().sum().sum())  # 0
```

### 이상치 확인

```python
fig, axes = plt.subplots(2, 3, figsize=(15, 8))
cols_to_check = ['Tenure', 'WarehouseToHome', 'CashbackAmount', 'OrderCount', 'DaySinceLastOrder', 'NumberOfAddress']

for ax, col in zip(axes.flat, cols_to_check):
    ax.boxplot(df[col])
    ax.set_title(col)

plt.tight_layout()
plt.show()
```

```python
# WarehouseToHome 극단값 확인
print(df['WarehouseToHome'].describe())
# 127km같은 극단값 존재 → IQR 방법으로 상한 처리

Q1 = df['WarehouseToHome'].quantile(0.25)
Q3 = df['WarehouseToHome'].quantile(0.75)
IQR = Q3 - Q1
upper = Q3 + 3 * IQR

df['WarehouseToHome'] = df['WarehouseToHome'].clip(upper=upper)
```

### 데이터 타입 정리

```python
# 범주형 컬럼 확인
cat_cols = df.select_dtypes(include='object').columns
for col in cat_cols:
    print(f'{col}: {df[col].unique()}')

# PreferredLoginDevice: ['Mobile Phone', 'Phone', 'Computer']
# 'Phone'과 'Mobile Phone'이 동일한 값 → 통일
df['PreferredLoginDevice'] = df['PreferredLoginDevice'].replace('Phone', 'Mobile Phone')
```

---

## 2단계: 탐색적 분석 — 이탈 그룹과 잔류 그룹 비교

### 타깃 분포

```python
churn_rate = df['Churn'].mean()
print(f'이탈률: {churn_rate:.1%}')  # 16.8%

# 클래스 불균형 확인
df['Churn'].value_counts().plot(kind='bar')
plt.title('이탈 여부 분포')
plt.xticks([0, 1], ['잔류', '이탈'], rotation=0)
plt.show()
```

### 수치형 변수: 이탈 그룹별 분포 비교

```python
numeric_features = ['Tenure', 'CashbackAmount', 'WarehouseToHome',
                    'NumberOfDeviceRegistered', 'DaySinceLastOrder', 'OrderCount']

fig, axes = plt.subplots(2, 3, figsize=(16, 10))
for ax, col in zip(axes.flat, numeric_features):
    df[df['Churn'] == 0][col].hist(ax=ax, alpha=0.6, label='잔류', bins=30, color='steelblue')
    df[df['Churn'] == 1][col].hist(ax=ax, alpha=0.6, label='이탈', bins=30, color='salmon')
    ax.set_title(col)
    ax.legend()
plt.tight_layout()
plt.show()
```

### 범주형 변수: 이탈률 비교

```python
cat_features = ['PreferredLoginDevice', 'PreferredPaymentMode', 'Gender',
                'PreferedOrderCat', 'MaritalStatus']

fig, axes = plt.subplots(2, 3, figsize=(16, 10))
for ax, col in zip(axes.flat, cat_features):
    churn_by_cat = df.groupby(col)['Churn'].mean().sort_values(ascending=False)
    churn_by_cat.plot(kind='bar', ax=ax, color='coral', edgecolor='black')
    ax.set_title(f'{col}별 이탈률')
    ax.set_ylabel('이탈률')
    ax.axhline(churn_rate, color='steelblue', linestyle='--', label=f'전체 평균 {churn_rate:.1%}')
    ax.legend()
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30)

plt.tight_layout()
plt.show()
```

---

## 3단계: 상관관계 분석

```python
# 수치형 피처 간 상관관계
corr_matrix = df[numeric_features + ['Churn']].corr()

plt.figure(figsize=(10, 8))
sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', center=0)
plt.title('피처 간 상관관계')
plt.show()

# Churn과의 상관계수
print(corr_matrix['Churn'].sort_values(ascending=False))
```

---

## 4단계: 피처 엔지니어링

```python
# 거래 충성도 점수 (Tenure × OrderCount)
df['loyalty_score'] = df['Tenure'] * df['OrderCount']

# 재구매 여부 (complain이 있는데도 재구매)
df['repeat_despite_complain'] = ((df['Complain'] == 1) & (df['OrderCount'] > 1)).astype(int)

# 캐시백 의존도
df['cashback_per_order'] = df['CashbackAmount'] / (df['OrderCount'] + 1)
```

---

## 5단계: 인사이트 정리

분석 결과를 데이터로 끝내지 않고 이야기로 만듭니다.

```
[발견 1] 재직 기간이 짧을수록 이탈률이 높다
- Tenure 1개월 미만 고객의 이탈률: 42%
- Tenure 12개월 이상 고객의 이탈률: 7%
→ 온보딩 초기 3개월이 이탈 방지의 핵심 구간

[발견 2] 불만(Complain)이 이탈의 가장 강한 신호다
- 불만 고객의 이탈률: 32%
- 불만 없는 고객의 이탈률: 14%
→ CS 대응 속도와 품질이 이탈률 직결

[발견 3] 모바일 앱보다 PC 사용 고객의 이탈률이 낮다
- PC 고객의 이탈률: 12%
- 모바일 고객의 이탈률: 21%
→ 모바일 UX 개선 우선순위 상향 필요

[발견 4] 캐시백 금액이 높을수록 잔류율이 높다
- 상위 25% 캐시백 고객의 이탈률: 8%
→ 이탈 위험군 대상 캐시백 강화 캠페인 검토
```

---

## 인사이트를 숫자로 검증

직관적으로 발견한 패턴을 통계로 뒷받침합니다.

```python
from scipy import stats

# 불만 고객 vs 잔류 고객: 이탈률 차이가 통계적으로 유의한가?
complain_churn = df[df['Complain'] == 1]['Churn']
no_complain_churn = df[df['Complain'] == 0]['Churn']

stat, p_value = stats.ttest_ind(complain_churn, no_complain_churn)
print(f'p-value: {p_value:.6f}')
# p < 0.05 이면 통계적으로 유의미한 차이
```

---

> 인사이트는 그래프가 아닙니다. "그러므로 우리는 이것을 해야 한다"는 문장입니다. 그 문장이 나올 때까지 분석은 끝나지 않습니다.
