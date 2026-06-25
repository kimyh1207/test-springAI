---
title: "6-3. 탐색적 데이터 분석(EDA) 실전"
order: 3
tags: [eda, data-analysis]
status: draft
author: vivace
---

# 6-3. 탐색적 데이터 분석(EDA) 실전

개념은 충분히 익혔습니다. 이번엔 공개 데이터셋으로 처음부터 끝까지 EDA를 수행합니다. 각 단계를 왜 하는지 설명하면서 진행합니다. 이 흐름이 모든 EDA의 템플릿입니다.

---

## 데이터셋 소개 — Titanic

Titanic 데이터셋은 1912년 타이타닉 침몰 사고 승객 정보입니다. 분석 질문: **"어떤 승객이 생존했는가?"**

Kaggle에서 다운로드: `kaggle competitions download -c titanic`

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['figure.figsize'] = (10, 5)
sns.set_theme(style='whitegrid')

df = pd.read_csv('train.csv')
```

---

## Step 1: 데이터 기본 파악

```python
# 크기와 구조
print(f"행: {df.shape[0]}, 열: {df.shape[1]}")

# 컬럼 정보
print(df.info())
# PassengerId: int — 승객 ID
# Survived:    int — 생존 여부 (0=사망, 1=생존) ← 타겟 변수
# Pclass:      int — 객실 등급 (1=1등석, 2=2등석, 3=3등석)
# Name:        str — 이름
# Sex:         str — 성별
# Age:         float — 나이 (결측 있음)
# SibSp:       int — 동승 형제자매/배우자 수
# Parch:       int — 동승 부모/자녀 수
# Ticket:      str — 티켓 번호
# Fare:        float — 운임
# Cabin:       str — 객실 번호 (결측 많음)
# Embarked:    str — 탑승항 (C=셰르부르, Q=퀸스타운, S=사우샘프턴)

# 기본 통계
print(df.describe())

# 결측값
print(df.isnull().sum())
# Age: 177개 (약 20%)
# Cabin: 687개 (약 77%)
# Embarked: 2개
```

---

## Step 2: 타겟 변수 분포

```python
# 생존율
survival_rate = df['Survived'].mean()
print(f"전체 생존율: {survival_rate:.1%}")  # 38.4%

# 시각화
fig, axes = plt.subplots(1, 2, figsize=(10, 4))

df['Survived'].value_counts().plot(kind='bar', ax=axes[0], color=['#d9534f', '#5cb85c'])
axes[0].set_xticklabels(['사망(0)', '생존(1)'], rotation=0)
axes[0].set_title('생존 여부 분포')
axes[0].set_ylabel('인원 수')

axes[1].pie(df['Survived'].value_counts(),
            labels=['사망', '생존'],
            colors=['#d9534f', '#5cb85c'],
            autopct='%1.1f%%', startangle=90)
axes[1].set_title('생존 비율')

plt.tight_layout()
plt.show()
```

---

## Step 3: 변수별 생존율 탐색

### 성별 — 가장 강력한 변수

```python
gender_survival = df.groupby('Sex')['Survived'].mean()
print(gender_survival)
# female    0.742
# male      0.189

# 여성 생존율이 남성의 4배 수준
sns.barplot(data=df, x='Sex', y='Survived', palette=['#4e9af1', '#f06292'])
plt.title('성별 생존율')
plt.ylabel('생존율')
plt.show()
```

### 객실 등급

```python
pclass_survival = df.groupby('Pclass')['Survived'].mean()
print(pclass_survival)
# 1등석: 0.630
# 2등석: 0.473
# 3등석: 0.242

sns.barplot(data=df, x='Pclass', y='Survived')
plt.title('객실 등급별 생존율')
plt.xlabel('객실 등급 (1=최상, 3=최하)')
plt.ylabel('생존율')
plt.show()
```

### 나이 분포

```python
# 생존/사망 그룹별 나이 분포 비교
fig, ax = plt.subplots()
df[df['Survived']==1]['Age'].dropna().plot(kind='kde', ax=ax, label='생존', color='green')
df[df['Survived']==0]['Age'].dropna().plot(kind='kde', ax=ax, label='사망', color='red')
ax.set_title('생존/사망별 나이 분포')
ax.set_xlabel('나이')
ax.legend()
plt.show()

# 어린이(0-12세) 생존율
df['is_child'] = df['Age'] < 12
print(df.groupby('is_child')['Survived'].mean())
# False (성인): 0.367
# True  (어린이): 0.539
```

### 복합 분석 — 성별 × 객실 등급

```python
pivot = df.pivot_table(values='Survived',
                        index='Sex',
                        columns='Pclass',
                        aggfunc='mean')
print(pivot)
#         1등석   2등석   3등석
# female  0.968  0.921  0.500
# male    0.369  0.157  0.135

sns.heatmap(pivot, annot=True, fmt='.2%', cmap='RdYlGn',
            vmin=0, vmax=1)
plt.title('성별 × 객실 등급 생존율')
plt.show()
```

---

## Step 4: 변수 간 상관 분석

```python
# 수치형 변수만 선택
numeric_cols = ['Survived', 'Pclass', 'Age', 'SibSp', 'Parch', 'Fare']
corr = df[numeric_cols].corr()

sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm',
            vmin=-1, vmax=1, square=True)
plt.title('변수 간 상관계수')
plt.show()

# 주요 발견:
# Pclass ↔ Survived: -0.34 (등급이 낮을수록 생존율 낮음)
# Fare   ↔ Survived:  0.26 (운임이 높을수록 생존율 높음)
# Pclass ↔ Fare:     -0.55 (1등석이 운임 높음 — 당연)
```

---

## Step 5: 인사이트 정리

EDA 결과를 문장으로 정리합니다.

```
분석 질문: "어떤 승객이 생존했는가?"

주요 발견:
1. 성별이 가장 강력한 생존 예측 변수
   - 여성 생존율 74%, 남성 19% → "여성과 어린이 먼저" 원칙이 실제로 작동

2. 객실 등급과 생존율은 강한 양의 상관
   - 1등석 63%, 3등석 24%
   - 1등석 여성의 생존율은 96.8%에 달함

3. 어린이(12세 미만)는 성인보다 생존율이 높음
   - 어린이 54% vs 성인 37%

4. Cabin(77% 결측)은 분석에서 제외
   - 결측 자체가 3등석 승객일 가능성과 연관

다음 단계:
→ Age 결측값 처리 (직책(Mr/Mrs/Miss)으로 그룹화 후 중앙값 대체)
→ 머신러닝 모델(로지스틱 회귀, 랜덤포레스트)로 생존 예측
```

---

> EDA는 끝이 없습니다. 하나의 발견이 다음 질문을 낳습니다. 멈추는 기준은 "충분히 이해했는가"가 아니라 "의사결정에 필요한 정보를 얻었는가"입니다.

---

## 실습

```python
# Kaggle 공개 데이터셋으로 직접 EDA 수행
# 추천: House Prices, Iris, Wine Quality

# EDA 체크리스트
# □ 1. 데이터 크기, 컬럼, 타입 파악
# □ 2. 결측값 개수와 비율 확인
# □ 3. 수치형 변수: 분포(히스토그램), 이상값(박스플롯)
# □ 4. 범주형 변수: 빈도(막대그래프), 타겟과의 관계
# □ 5. 상관계수 히트맵
# □ 6. 복합 분석 (두 변수 조합)
# □ 7. 인사이트 3개 이상 문장으로 정리

# 목표: 이 데이터로 무엇을 예측할 수 있고,
#       어떤 변수가 중요할 것 같은지 가설 세우기
```
