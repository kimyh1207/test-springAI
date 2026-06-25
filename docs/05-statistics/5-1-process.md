---
title: "5-1. 데이터 분석 프로세스와 문제 정의"
order: 1
tags: [data-analysis, process]
status: draft
author: vivace
---

# 5-1. 데이터 분석 프로세스와 문제 정의

데이터 분석에서 가장 흔한 실수는 데이터부터 보는 것입니다. 질문 없이 데이터를 보면 무엇을 찾는지 모른 채 헤맵니다. 좋은 분석은 **좋은 질문**에서 시작합니다.

---

## 데이터 분석 프로세스

```
1. 문제 정의      → 무엇을 알고 싶은가
       ↓
2. 데이터 수집    → 어떤 데이터가 필요한가, 어디서 구하는가
       ↓
3. 데이터 탐색    → EDA: 데이터의 구조와 패턴 파악
       ↓
4. 데이터 전처리  → 결측값, 이상값, 형식 정제
       ↓
5. 분석 / 모델링  → 통계 검정, 머신러닝 등
       ↓
6. 결과 해석      → 수치가 아닌 의미로 전달
       ↓
7. 의사결정 / 행동 → 분석의 목적
```

이 흐름은 선형이 아닙니다. 탐색하다 문제를 다시 정의하고, 전처리하다 수집을 다시 합니다. 반복이 분석입니다.

---

## 1단계: 문제 정의

막연한 질문을 구체적인 분석 질문으로 바꿉니다.

```
막연한 질문: "우리 서비스 사용자들은 어떤가요?"

구체적 질문:
  - 최근 30일 기준 DAU(일간 활성 사용자)는 얼마인가?
  - 신규 가입자 중 7일 이내에 재방문하는 비율은?
  - 어떤 기능을 쓴 사용자의 30일 유지율이 높은가?
```

좋은 분석 질문의 조건:
- **측정 가능하다** — 수치로 답할 수 있다
- **실행 가능하다** — 결과가 의사결정으로 이어진다
- **범위가 명확하다** — 기간, 대상, 지표가 정해져 있다

---

## 2단계: 데이터 수집과 이해

데이터를 받으면 분석 전에 먼저 파악합니다.

```python
import pandas as pd

df = pd.read_csv('users.csv')

# 크기 확인
print(df.shape)          # (행 수, 열 수)

# 컬럼과 타입 확인
print(df.dtypes)

# 처음 5행
print(df.head())

# 기본 통계량 한눈에
print(df.describe())

# 결측값 확인
print(df.isnull().sum())
```

이 다섯 줄만으로 데이터의 윤곽이 잡힙니다. 분석 전 반드시 실행합니다.

---

## 3단계: EDA(탐색적 데이터 분석)

EDA(Exploratory Data Analysis)는 데이터를 다각도로 살펴보는 과정입니다. 가설을 검증하기 전에 데이터가 어떻게 생겼는지 이해합니다.

```python
# 특정 컬럼의 분포 확인
df['age'].value_counts()
df['age'].hist(bins=20)

# 두 변수의 관계
df.plot.scatter(x='age', y='purchase_amount')

# 그룹별 평균
df.groupby('country')['revenue'].mean().sort_values(ascending=False)
```

EDA에서 찾을 것:
- **분포의 형태**: 한쪽으로 치우쳐 있는가, 정규분포에 가까운가
- **이상값**: 극단적으로 크거나 작은 값이 있는가
- **결측값 패턴**: 특정 조건에서만 값이 없는가
- **변수 간 관계**: 함께 움직이는 변수가 있는가

---

## 4단계: 데이터 전처리

실제 데이터는 항상 지저분합니다. 분석 시간의 60~80%가 전처리에 쓰입니다.

```python
# 결측값 처리
df['age'].fillna(df['age'].median(), inplace=True)   # 중앙값으로 채우기
df.dropna(subset=['email'], inplace=True)              # 필수 컬럼 결측 행 제거

# 이상값 처리 (IQR 방법)
Q1 = df['purchase_amount'].quantile(0.25)
Q3 = df['purchase_amount'].quantile(0.75)
IQR = Q3 - Q1
df = df[(df['purchase_amount'] >= Q1 - 1.5*IQR) &
        (df['purchase_amount'] <= Q3 + 1.5*IQR)]

# 타입 변환
df['created_at'] = pd.to_datetime(df['created_at'])

# 중복 제거
df.drop_duplicates(subset=['user_id'], inplace=True)
```

---

## 6단계: 결과 해석과 전달

분석의 마지막은 숫자가 아니라 이야기입니다.

```
나쁜 전달: "7일 재방문율이 23.4%입니다."

좋은 전달:
  "신규 가입자 4명 중 1명만 일주일 안에 돌아옵니다.
   특히 튜토리얼을 완료한 사용자는 재방문율이 61%로,
   미완료 사용자(12%)의 5배입니다.
   → 튜토리얼 완료율을 높이는 것이 유지율 개선의 핵심입니다."
```

수치는 맥락 없이 전달하면 의미를 잃습니다. 비교 기준, 시계열 변화, 원인 가설을 함께 제시합니다.

---

> 분석가의 가치는 데이터를 다루는 기술이 아닙니다. 올바른 질문을 찾고, 그 답을 행동으로 연결하는 능력입니다.

---

## 실습

```python
# Kaggle의 Titanic 데이터셋을 활용한 EDA 실습
# https://www.kaggle.com/c/titanic/data

import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('titanic.csv')

# 1. 데이터 기본 파악
print(df.shape)
print(df.dtypes)
print(df.isnull().sum())

# 2. 분석 질문 설정
# "어떤 승객이 생존할 가능성이 높았는가?"

# 3. 그룹별 생존율 탐색
print(df.groupby('Sex')['Survived'].mean())
print(df.groupby('Pclass')['Survived'].mean())

# 4. 시각화
df.groupby('Pclass')['Survived'].mean().plot(kind='bar')
plt.title('객실 등급별 생존율')
plt.show()

# 5. 결측값 처리 후 재분석
df['Age'].fillna(df['Age'].median(), inplace=True)
df.groupby(pd.cut(df['Age'], bins=[0,18,40,60,100]))['Survived'].mean()
```
