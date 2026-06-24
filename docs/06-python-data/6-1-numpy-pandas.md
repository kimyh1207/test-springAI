---
title: "6-1. NumPy · Pandas 핵심 패턴"
order: 1
tags: [python, numpy, pandas]
status: draft
author: vivace
---

# 6-1. NumPy · Pandas 핵심 패턴

NumPy는 수치 연산의 엔진이고, Pandas는 데이터 조작의 도구입니다. 머신러닝 라이브러리도, 딥러닝 프레임워크도 내부적으로 NumPy 위에서 동작합니다. 두 라이브러리를 익히는 것이 Python 데이터 분석의 출발점입니다.

---

## NumPy — 빠른 수치 연산

Python 리스트로 수백만 건의 수치를 계산하면 느립니다. NumPy 배열은 C로 구현되어 있어 수십~수백 배 빠릅니다.

```python
import numpy as np

# 배열 생성
a = np.array([1, 2, 3, 4, 5])
b = np.zeros(5)           # [0. 0. 0. 0. 0.]
c = np.ones((3, 4))       # 3행 4열, 전부 1
d = np.arange(0, 10, 2)   # [0 2 4 6 8]
e = np.linspace(0, 1, 5)  # [0.   0.25 0.5  0.75 1.  ]

# 랜덤
np.random.seed(42)
f = np.random.normal(0, 1, 1000)  # 평균 0, 표준편차 1, 1000개
```

### 벡터 연산 — 루프 없이

```python
a = np.array([1, 2, 3, 4, 5])
b = np.array([10, 20, 30, 40, 50])

# 파이썬 리스트는 루프 필요, NumPy는 한 줄
print(a + b)     # [11 22 33 44 55]
print(a * 2)     # [ 2  4  6  8 10]
print(a ** 2)    # [ 1  4  9 16 25]
print(a > 3)     # [False False False  True  True]

# 집계
print(a.sum())   # 15
print(a.mean())  # 3.0
print(a.std())   # 1.414...
print(a.max())   # 5
```

### 인덱싱과 슬라이싱

```python
a = np.array([[1, 2, 3],
              [4, 5, 6],
              [7, 8, 9]])

print(a[0])        # [1 2 3]       — 첫 번째 행
print(a[0, 1])     # 2             — 0행 1열
print(a[:, 1])     # [2 5 8]       — 1열 전체
print(a[1:, :2])   # [[4 5][7 8]]  — 1행 이후, 2열 미만

# 불리언 인덱싱
print(a[a > 5])    # [6 7 8 9]
```

### 형태 변환

```python
a = np.arange(12)
print(a.reshape(3, 4))   # 3행 4열
print(a.reshape(2, -1))  # 2행, 열은 자동 계산 (2행 6열)

# 차원 추가/제거
b = np.array([1, 2, 3])
print(b.shape)             # (3,)
print(b[:, np.newaxis])    # (3, 1)로 변환 — 머신러닝에서 자주 쓰임
```

---

## Pandas — 데이터 조작의 핵심

### Series와 DataFrame

```python
import pandas as pd

# Series — 1차원 데이터 (인덱스 있는 배열)
s = pd.Series([10, 20, 30], index=['a', 'b', 'c'])
print(s['b'])   # 20

# DataFrame — 2차원 데이터 (행과 열)
df = pd.DataFrame({
    'name':   ['Alice', 'Bob', 'Charlie'],
    'age':    [25, 30, 35],
    'score':  [88, 72, 95]
})
```

### 데이터 선택

```python
# 열 선택
df['name']            # Series 반환
df[['name', 'score']] # DataFrame 반환 (열 여러 개)

# 행 선택
df.loc[0]             # 레이블로 선택 (인덱스가 0)
df.iloc[0]            # 위치로 선택 (첫 번째 행)
df.loc[0:2, 'name':'score']  # 행과 열 동시에

# 조건 필터링
df[df['age'] > 25]
df[(df['age'] > 25) & (df['score'] >= 80)]
df[df['name'].isin(['Alice', 'Charlie'])]
```

### 자주 쓰는 연산

```python
# 정렬
df.sort_values('score', ascending=False)
df.sort_values(['age', 'score'], ascending=[True, False])

# 새 컬럼 추가
df['grade'] = df['score'].apply(lambda x: 'A' if x >= 90 else 'B')
df['age_group'] = pd.cut(df['age'], bins=[0, 25, 35, 100],
                          labels=['청년', '중년', '장년'])

# 그룹별 집계
df.groupby('grade')['score'].mean()
df.groupby('grade').agg({'score': ['mean', 'std', 'count']})

# 피벗 테이블
pd.pivot_table(df, values='score', index='grade', columns='age_group', aggfunc='mean')
```

### 데이터 합치기

```python
# 수직 합치기 (같은 구조의 데이터 이어붙이기)
df_all = pd.concat([df_jan, df_feb, df_mar], ignore_index=True)

# 수평 합치기 (공통 키로 조인)
df_merged = pd.merge(df_users, df_orders, on='user_id', how='left')
# how: 'left', 'right', 'inner', 'outer' — SQL join과 동일한 개념
```

### 문자열 처리

```python
# str accessor — 벡터화된 문자열 연산
df['name'] = df['name'].str.lower()
df['email_domain'] = df['email'].str.split('@').str[1]
df = df[df['phone'].str.match(r'^\d{3}-\d{4}-\d{4}$')]  # 패턴 필터
df['name'].str.contains('김')
```

### 날짜 처리

```python
df['created_at'] = pd.to_datetime(df['created_at'])

df['year']  = df['created_at'].dt.year
df['month'] = df['created_at'].dt.month
df['day']   = df['created_at'].dt.day
df['weekday'] = df['created_at'].dt.day_name()

# 날짜 기준 리샘플링
df.set_index('created_at').resample('M')['revenue'].sum()  # 월별 집계
```

---

> NumPy는 계산, Pandas는 조작. 이 두 가지가 손에 익으면 어떤 데이터 문제도 코드로 풀 수 있습니다.

---

## 실습

```python
import pandas as pd
import numpy as np

# 실습 데이터 생성
np.random.seed(42)
n = 200
df = pd.DataFrame({
    'user_id':    range(1, n+1),
    'age':        np.random.randint(18, 65, n),
    'country':    np.random.choice(['KR', 'US', 'JP', 'DE'], n),
    'purchase':   np.random.exponential(50000, n),
    'joined':     pd.date_range('2023-01-01', periods=n, freq='D')
})

# 1. 국가별 평균 구매금액 상위 3개국
# 2. 나이를 10대, 20대, 30대... 로 그룹화 후 그룹별 구매금액 평균
# 3. 가입 월별 사용자 수
# 4. purchase가 상위 10%인 사용자만 필터링
# 5. user_id, country, purchase 컬럼만 선택 후 CSV로 저장
```
