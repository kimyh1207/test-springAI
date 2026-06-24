---
title: "6-2. 결측·이상치·스케일링 데이터 전처리"
order: 2
tags: [preprocessing, missing-values, scaling]
status: draft
author: vivace
---

# 6-2. 결측 · 이상치 · 스케일링 데이터 전처리

실제 데이터는 교과서처럼 깔끔하지 않습니다. 값이 빠져 있고, 극단값이 섞여 있고, 단위가 제각각입니다. 모델에 넣기 전에 이것을 정제하는 것이 전처리입니다. 좋은 모델보다 좋은 데이터가 더 중요합니다.

---

## 결측값 처리

### 결측값 파악

```python
import pandas as pd
import numpy as np

# 결측값 개수
print(df.isnull().sum())

# 결측값 비율
print(df.isnull().mean() * 100)  # 퍼센트

# 결측값이 있는 행만 확인
print(df[df.isnull().any(axis=1)])

# 시각화
import missingno as msno
msno.matrix(df)  # 결측 패턴 시각화
```

### 결측값 처리 전략

```python
# 1. 제거 — 결측 비율이 높거나 대체가 의미 없을 때
df.dropna()                          # 결측값 있는 행 제거
df.dropna(subset=['email', 'name'])  # 특정 컬럼 기준
df.dropna(thresh=5)                  # 유효값이 5개 미만인 행 제거

# 2. 수치형 — 통계값으로 대체
df['age'].fillna(df['age'].mean(),   inplace=True)  # 평균
df['age'].fillna(df['age'].median(), inplace=True)  # 중앙값 (이상값 있을 때 권장)
df['age'].fillna(df['age'].mode()[0], inplace=True) # 최빈값

# 3. 범주형 — 최빈값 또는 'Unknown'으로 대체
df['country'].fillna(df['country'].mode()[0], inplace=True)
df['country'].fillna('Unknown', inplace=True)

# 4. 시계열 — 앞뒤 값으로 보간
df['price'].fillna(method='ffill', inplace=True)  # 이전 값으로
df['price'].fillna(method='bfill', inplace=True)  # 이후 값으로
df['price'].interpolate(method='linear')           # 선형 보간

# 5. 그룹별 평균으로 대체 (더 정교한 방법)
df['age'] = df.groupby('country')['age'].transform(
    lambda x: x.fillna(x.median())
)
```

### 결측 메커니즘 이해

무작정 제거하기 전에 왜 결측이 생겼는지 파악합니다.

```
MCAR (완전 무작위 결측): 어떤 이유도 없이 랜덤하게 빠짐 → 제거 안전
MAR (무작위 결측): 다른 변수에 따라 빠짐 (예: 고연령층에서 소득 미입력)
MNAR (비무작위 결측): 결측값 자체가 패턴 (예: 불만족 고객이 평점 미입력)
```

MNAR은 단순 대체로 해결이 안 됩니다. 결측 여부 자체를 새 변수로 추가하는 것이 더 나을 수 있습니다.

```python
# 결측 여부를 새 변수로
df['income_missing'] = df['income'].isnull().astype(int)
```

---

## 이상치 탐지와 처리

### IQR 방법

```python
def remove_outliers_iqr(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR

    print(f"{column}: 정상 범위 [{lower:.1f}, {upper:.1f}]")
    print(f"이상치 개수: {((df[column] < lower) | (df[column] > upper)).sum()}")

    return df[(df[column] >= lower) & (df[column] <= upper)]

df = remove_outliers_iqr(df, 'purchase_amount')
```

### Z-score 방법

```python
from scipy import stats

z_scores = np.abs(stats.zscore(df['income']))
df = df[z_scores < 3]  # Z-score 3 초과는 이상치로 간주
```

### 이상치 처리 선택지

```python
# 제거 — 실제 오류이거나 모델에 악영향이 클 때
df = df[df['age'].between(0, 120)]

# 대체 (Winsorizing) — 극단값을 경계값으로 교체
lower, upper = df['price'].quantile([0.01, 0.99])
df['price'] = df['price'].clip(lower=lower, upper=upper)

# 로그 변환 — 분포를 압축해 이상치 영향 감소
df['log_price'] = np.log1p(df['price'])
```

이상치를 항상 제거하는 것은 옳지 않습니다. 사기 탐지에서는 이상치 자체가 탐지 대상입니다. 도메인 지식을 바탕으로 판단합니다.

---

## 스케일링 — 변수 간 단위 통일

키(cm)와 소득(만원)을 그대로 모델에 넣으면 소득의 숫자가 크다는 이유만으로 더 중요한 변수가 됩니다. 스케일링은 변수들의 단위를 맞춥니다.

### 표준화 (StandardScaler) — 평균 0, 표준편차 1

```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
df[['age', 'income']] = scaler.fit_transform(df[['age', 'income']])

# 결과: 평균 ≈ 0, 표준편차 ≈ 1
# 정규분포를 가정하는 모델(선형회귀, SVM 등)에 적합
```

### 정규화 (MinMaxScaler) — 0과 1 사이로

```python
from sklearn.preprocessing import MinMaxScaler

scaler = MinMaxScaler()
df[['age', 'income']] = scaler.fit_transform(df[['age', 'income']])

# 결과: 최솟값 = 0, 최댓값 = 1
# 범위가 중요한 경우, 신경망에 적합
# 이상값에 민감 (이상값이 있으면 표준화 권장)
```

### RobustScaler — 이상값에 강건

```python
from sklearn.preprocessing import RobustScaler

scaler = RobustScaler()  # 중앙값과 IQR 기반
df[['income']] = scaler.fit_transform(df[['income']])
# 이상값이 많을 때 선택
```

### 스케일링 주의사항

```python
# 반드시 train/test 분리 후 fit은 train에만
from sklearn.model_selection import train_test_split

X_train, X_test = train_test_split(X, test_size=0.2)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)  # fit + transform
X_test_scaled  = scaler.transform(X_test)        # transform만 (fit 금지)
# test에 fit하면 데이터 누수(Data Leakage) 발생
```

---

## 범주형 변수 인코딩

머신러닝 모델은 숫자만 입력받습니다. 'KR', 'US', 'JP' 같은 문자열을 숫자로 변환해야 합니다.

```python
# 레이블 인코딩 — 순서가 있는 범주형 (낮음/중간/높음)
from sklearn.preprocessing import LabelEncoder
le = LabelEncoder()
df['grade_encoded'] = le.fit_transform(df['grade'])  # 낮음→0, 중간→1, 높음→2

# 원-핫 인코딩 — 순서 없는 범주형 (KR, US, JP)
df_encoded = pd.get_dummies(df, columns=['country'], drop_first=True)
# drop_first=True: 다중공선성 방지 (k-1개의 컬럼 생성)

# 많은 범주 → Target Encoding (범주별 타겟 평균으로 대체)
target_mean = df.groupby('country')['purchase'].mean()
df['country_encoded'] = df['country'].map(target_mean)
```

---

> 쓰레기 데이터를 넣으면 쓰레기 결과가 나옵니다(Garbage In, Garbage Out). 전처리에 투자한 시간이 모델 튜닝 시간보다 훨씬 가치 있습니다.

---

## 실습

```python
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# 의도적으로 문제 있는 데이터 생성
np.random.seed(42)
n = 300
df = pd.DataFrame({
    'age':      np.where(np.random.rand(n) < 0.1, np.nan,
                         np.random.randint(18, 65, n)),
    'income':   np.random.exponential(50000, n),
    'country':  np.where(np.random.rand(n) < 0.05, np.nan,
                         np.random.choice(['KR', 'US', 'JP'], n)),
    'purchase': np.concatenate([np.random.normal(100, 30, n-10),
                                [5000, 8000, -50, -100, 10000,
                                 9000, 7000, 6000, 5500, 4500]])
})

# 1. 각 컬럼의 결측값 개수와 비율 출력
# 2. age → 중앙값으로, country → 최빈값으로 결측 처리
# 3. purchase의 이상치 탐지 (IQR 방법) 및 클리핑
# 4. age, income 표준화 (train/test 분리 후)
# 5. country 원-핫 인코딩
```
