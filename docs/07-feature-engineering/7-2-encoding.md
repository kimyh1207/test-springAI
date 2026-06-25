---
title: "7-2. 인코딩 · 파생변수 · 시간/텍스트 피처"
order: 2
tags: [encoding, feature-engineering, datetime, text]
status: draft
author: vivace
---

# 7-2. 인코딩 · 파생변수 · 시간/텍스트 피처

범주형 변수를 숫자로 바꾸고, 기존 컬럼에서 새로운 정보를 뽑아내는 것이 이 절의 핵심입니다.

---

## 범주형 인코딩

### Label Encoding — 순서형에만

각 카테고리에 정수를 부여합니다. 순서가 있는 경우에 적합합니다.

```python
from sklearn.preprocessing import LabelEncoder

le = LabelEncoder()
df['grade_encoded'] = le.fit_transform(df['grade'])  # A→0, B→1, C→2

# 순서를 직접 지정할 때
grade_map = {'C': 0, 'B': 1, 'A': 2, 'S': 3}
df['grade_encoded'] = df['grade'].map(grade_map)
```

**주의**: 명목형(순서 없는) 변수에 Label Encoding을 쓰면 안 됩니다. 서울=0, 부산=1, 대전=2라고 했을 때 모델은 대전이 서울+부산이라고 해석할 수 있습니다.

### One-Hot Encoding — 명목형의 표준

카테고리마다 0/1 컬럼을 만듭니다.

```python
df = pd.get_dummies(df, columns=['city'], drop_first=True)
# drop_first=True: 다중공선성 방지 (k개 카테고리 → k-1개 컬럼)
```

카테고리가 많으면(수백 개 이상) 컬럼이 폭발합니다. 이때는 Target Encoding이나 Embedding을 고려합니다.

### Target Encoding — 고카디널리티에 유용

각 카테고리를 해당 카테고리의 타깃 평균으로 대체합니다.

```python
# 직접 구현
target_mean = df.groupby('city')['churn'].mean()
df['city_encoded'] = df['city'].map(target_mean)
```

**반드시 훈련 데이터만으로 인코딩 테이블을 만들고, 검증/테스트에 적용해야 합니다.** 전체 데이터로 만들면 누수입니다.

```python
# 안전한 방법
train_target_mean = X_train.assign(target=y_train).groupby('city')['target'].mean()
X_train['city_encoded'] = X_train['city'].map(train_target_mean)
X_test['city_encoded'] = X_test['city'].map(train_target_mean)
```

---

## 파생변수(Derived Features)

기존 컬럼을 조합하거나 변환해서 새로운 피처를 만듭니다.

### 사칙연산 조합

```python
df['bmi'] = df['weight'] / (df['height'] / 100) ** 2
df['revenue_per_user'] = df['total_revenue'] / df['user_count']
df['inventory_turnover'] = df['sales'] / df['avg_inventory']
```

### 상호작용 피처(Interaction Features)

두 피처를 곱해서 비선형 관계를 포착합니다.

```python
df['age_x_income'] = df['age'] * df['income']
df['is_premium_x_tenure'] = df['is_premium'].astype(int) * df['tenure_months']
```

선형 모델(로지스틱 회귀, 선형 회귀)은 변수 간 상호작용을 자동으로 학습하지 못합니다. 트리 기반 모델은 학습합니다.

---

## 시간 피처

날짜/시간 데이터는 그 자체로는 쓸 수 없습니다. 의미 있는 단위로 쪼개야 합니다.

```python
df['created_at'] = pd.to_datetime(df['created_at'])

# 기본 추출
df['year']    = df['created_at'].dt.year
df['month']   = df['created_at'].dt.month
df['day']     = df['created_at'].dt.day
df['hour']    = df['created_at'].dt.hour
df['weekday'] = df['created_at'].dt.dayofweek  # 0=월요일, 6=일요일

# 비즈니스 관점 파생
df['is_weekend']  = df['weekday'].isin([5, 6]).astype(int)
df['is_business_hour'] = df['hour'].between(9, 18).astype(int)
df['quarter']     = df['created_at'].dt.quarter
```

### 기간(Elapsed Time) 피처

```python
reference_date = pd.Timestamp('2024-01-01')

df['days_since_signup'] = (df['created_at'] - df['signup_date']).dt.days
df['days_to_deadline']  = (df['deadline'] - reference_date).dt.days
```

### 주기성 인코딩 — 월·요일은 원형이다

12월 다음은 1월입니다. 단순 숫자로 표현하면 1월(1)과 12월(12)이 멀어 보이지만 실제로는 연속입니다. 사인/코사인 변환으로 주기성을 보존합니다.

```python
import numpy as np

df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
```

---

## 텍스트 피처

자연어 처리의 전체를 다루지는 않습니다. 정형 데이터에 섞여 있는 텍스트 컬럼을 처리하는 실용적인 방법만 다룹니다.

### 기본 통계 피처

```python
df['text_length']    = df['review'].str.len()
df['word_count']     = df['review'].str.split().str.len()
df['sentence_count'] = df['review'].str.count('[.!?]') + 1
df['has_exclamation']= df['review'].str.contains('!').astype(int)
```

### TF-IDF — 단어의 중요도

단어가 문서에서 얼마나 중요한지를 수치화합니다. 자주 등장하지만 전체 문서에서 희귀한 단어일수록 높은 점수를 받습니다.

```python
from sklearn.feature_extraction.text import TfidfVectorizer

tfidf = TfidfVectorizer(max_features=100, ngram_range=(1, 2))
tfidf_matrix = tfidf.fit_transform(X_train['review'])

# DataFrame으로 변환하여 병합
tfidf_df = pd.DataFrame(
    tfidf_matrix.toarray(),
    columns=[f'tfidf_{w}' for w in tfidf.get_feature_names_out()]
)
X_train = pd.concat([X_train.reset_index(drop=True), tfidf_df], axis=1)
```

---

## 실전: 타이타닉 피처 엔지니어링

```python
import pandas as pd
import numpy as np

df = pd.read_csv('titanic.csv')

# 1. 이름에서 호칭 추출
df['title'] = df['Name'].str.extract(r' ([A-Za-z]+)\.', expand=False)
df['title'] = df['title'].replace(
    ['Lady', 'Countess', 'Capt', 'Col', 'Don', 'Dr', 'Major', 'Rev', 'Sir', 'Jonkheer', 'Dona'],
    'Rare'
)
df['title'] = df['title'].replace({'Mlle': 'Miss', 'Ms': 'Miss', 'Mme': 'Mrs'})

# 2. 가족 크기
df['family_size'] = df['SibSp'] + df['Parch'] + 1
df['is_alone'] = (df['family_size'] == 1).astype(int)

# 3. 나이 구간화 (결측값 중앙값으로 대체 후)
df['Age'] = df['Age'].fillna(df['Age'].median())
df['age_group'] = pd.cut(df['Age'], bins=[0, 12, 18, 35, 60, 100],
                          labels=['child', 'teen', 'adult', 'middle', 'senior'])

# 4. 요금 로그 변환
df['log_fare'] = np.log1p(df['Fare'])

# 5. 객실 번호에서 갑판 추출
df['deck'] = df['Cabin'].str[0].fillna('Unknown')

print(df[['title', 'family_size', 'is_alone', 'age_group', 'log_fare', 'deck']].head())
```

---

> 피처 엔지니어링의 절반은 도메인 지식이고, 나머지 절반은 데이터를 탐색하면서 발견하는 패턴입니다. 코드보다 먼저 데이터를 이해해야 합니다.
