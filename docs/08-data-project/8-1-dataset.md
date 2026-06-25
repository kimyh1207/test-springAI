---
title: "8-1. 데이터셋 선정과 분석 설계"
order: 1
tags: [dataset, problem-definition, data-analysis]
status: draft
author: vivace
---

# 8-1. 데이터셋 선정과 분석 설계

분석을 시작하기 전에 해야 할 일이 있습니다. 어떤 질문에 답할 것인지 결정하는 것입니다. 질문이 없으면 어떤 데이터도 의미가 없습니다.

---

## 좋은 분석 질문의 조건

좋은 분석 질문은 세 가지 조건을 만족합니다.

1. **구체적이다** — "매출이 왜 줄었나?" 보다 "지난 분기 대비 이번 분기 매출이 15% 감소한 원인은 무엇인가?"
2. **답할 수 있다** — 보유한 데이터로 실제로 답할 수 있어야 합니다
3. **결정에 연결된다** — 분석 결과가 어떤 행동으로 이어지는지 명확해야 합니다

나쁜 질문: "고객 데이터를 분석해보자"  
좋은 질문: "30일 이내에 이탈할 가능성이 높은 고객을 미리 식별해서 리텐션 캠페인 대상을 선정할 수 있을까?"

---

## 프로젝트 주제: 이커머스 고객 이탈 분석

이 챕터 전체에서 하나의 데이터셋을 가지고 분석을 완성합니다.

**데이터**: Kaggle — E-Commerce Customer Churn Dataset  
**질문**: 어떤 고객이 이탈할 가능성이 높은가? 이탈 고객의 행동 패턴은 무엇인가?  
**목표**: 이탈 예측 모델의 기반이 되는 인사이트 도출

```python
# 데이터 확보 (Kaggle CLI 또는 직접 다운로드)
# kaggle datasets download -d ankitverma2010/ecommerce-customer-churn-analysis-and-prediction

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('E Commerce.csv')
print(df.shape)       # (5630, 20)
print(df.dtypes)
```

---

## 데이터 첫 탐색 — 5분 프로파일링

데이터를 받으면 바로 모델을 만들지 않습니다. 먼저 데이터가 어떻게 생겼는지 파악합니다.

```python
# 기본 형태
print(df.head())
print(df.info())

# 결측값 현황
missing = df.isnull().sum()
missing_pct = (missing / len(df) * 100).round(2)
print(pd.DataFrame({'count': missing, 'pct': missing_pct}).query('count > 0'))

# 수치형 요약 통계
print(df.describe())

# 타깃 변수 분포
print(df['Churn'].value_counts(normalize=True))
```

결측값이 어디에 얼마나 있는지, 타깃 변수가 균형 잡혔는지, 수치형 변수의 범위가 상식적인지를 이 단계에서 확인합니다.

---

## 분석 계획서 작성

분석을 시작하기 전에 계획을 문서로 정리합니다. 분석이 산으로 가는 것을 막아줍니다.

```
# 분석 계획서

## 1. 핵심 질문
- 이탈 고객과 잔류 고객의 행동 차이는 무엇인가?
- 이탈을 가장 강하게 예측하는 변수는 무엇인가?

## 2. 분석 방법
- EDA: 타깃 변수별 분포 비교, 상관관계 분석
- 피처 엔지니어링: 거래 빈도, 최근성 파생변수
- 모델: 로지스틱 회귀 (해석 가능성 우선)

## 3. 성공 기준
- ROC-AUC 0.80 이상
- 이탈 예측 Recall 0.70 이상 (놓치는 이탈 고객 최소화)

## 4. 결과물
- 이탈 예측 스코어 컬럼이 추가된 고객 테이블
- 상위 이탈 위험군 고객 명단 (마케팅팀 전달용)
```

---

## 공개 데이터셋 소개

이 챕터의 데이터 말고도 연습할 수 있는 데이터셋입니다.

| 데이터셋 | 출처 | 분석 주제 |
|---------|------|---------|
| Titanic | Kaggle | 생존 예측 (분류) |
| House Prices | Kaggle | 주택 가격 예측 (회귀) |
| Bike Sharing | UCI | 자전거 수요 예측 (시계열) |
| Netflix Titles | Kaggle | 콘텐츠 트렌드 EDA |
| Seoul Bike Data | UCI | 기후-수요 관계 분석 |

좋은 데이터셋을 고르는 기준은 단순합니다. **실제 비즈니스 문제에서 나온 데이터**일수록 배울 것이 많습니다.

---

> 분석 계획서는 완벽할 필요가 없습니다. 탐색하면서 수정하면 됩니다. 중요한 것은 질문을 먼저 쓰는 습관입니다.
