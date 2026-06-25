---
title: "5-4. 시각화로 데이터 읽기"
order: 4
tags: [visualization, matplotlib, seaborn]
status: draft
author: vivace
---

# 5-4. 시각화로 데이터 읽기

숫자 1,000개를 테이블로 보면 아무것도 보이지 않습니다. 같은 데이터를 차트로 그리면 패턴이 보입니다. 시각화는 데이터 분석의 언어입니다. 분석가 자신을 위해서도, 결과를 전달하기 위해서도 필수입니다.

---

## 라이브러리 선택

Python 데이터 시각화의 두 축입니다.

| 라이브러리 | 특징 | 주 용도 |
|-----------|------|---------|
| **Matplotlib** | 세밀한 제어, 저수준 | 커스텀 차트, 논문 수준 |
| **Seaborn** | Matplotlib 기반, 통계 특화 | EDA, 빠른 탐색 |
| **Plotly** | 인터랙티브 | 대시보드, 웹 서비스 |

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# 기본 스타일 설정
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.family'] = 'Malgun Gothic'  # 한글 폰트 (Windows)
sns.set_theme(style='whitegrid')
```

---

## 분포 시각화

### 히스토그램 — 수치형 변수의 분포

```python
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

# 기본 히스토그램
axes[0].hist(df['age'], bins=30, color='steelblue', edgecolor='white')
axes[0].set_title('나이 분포')
axes[0].set_xlabel('나이')
axes[0].set_ylabel('빈도')

# KDE(커널 밀도 추정) 포함
sns.histplot(df['age'], bins=30, kde=True, ax=axes[1])
axes[1].set_title('나이 분포 (KDE 포함)')

plt.tight_layout()
plt.show()
```

### 박스플롯 — 분포 요약과 이상값

```python
# 그룹별 박스플롯
sns.boxplot(data=df, x='grade', y='score', palette='Set2')
plt.title('등급별 점수 분포')
plt.show()

# 박스플롯 읽는 법
# ─────────── 최댓값 (이상값 제외)
#      ┌──┐   Q3 (75번째 백분위)
#      │  │   IQR (사분위 범위)
#      ├──┤   중앙값 (50번째 백분위)
#      │  │
#      └──┘   Q1 (25번째 백분위)
# ─────────── 최솟값 (이상값 제외)
#      ○      이상값 (Q3 + 1.5*IQR 초과)
```

### 바이올린 플롯 — 박스플롯 + 분포 형태

```python
sns.violinplot(data=df, x='country', y='revenue', palette='muted')
plt.title('국가별 매출 분포')
plt.xticks(rotation=45)
plt.show()
```

---

## 관계 시각화

### 산점도 — 두 변수의 관계

```python
# 기본 산점도
plt.scatter(df['age'], df['income'], alpha=0.5, color='steelblue')
plt.xlabel('나이')
plt.ylabel('소득')
plt.title('나이와 소득의 관계')
plt.show()

# 추세선 포함 (seaborn)
sns.regplot(data=df, x='age', y='income',
            scatter_kws={'alpha': 0.3},
            line_kws={'color': 'red'})
plt.title('나이와 소득의 관계 (추세선 포함)')
plt.show()

# 색상으로 세 번째 변수 표현
sns.scatterplot(data=df, x='age', y='income',
                hue='gender', style='gender', alpha=0.7)
plt.show()
```

### 페어플롯 — 여러 변수 쌍의 관계 한눈에

```python
# 수치형 변수들의 모든 조합을 한번에
sns.pairplot(df[['age', 'income', 'score', 'gender']],
             hue='gender', diag_kind='kde')
plt.suptitle('변수 쌍별 관계', y=1.02)
plt.show()
```

### 히트맵 — 상관계수 시각화

```python
corr = df[['age', 'income', 'score', 'purchase']].corr()

plt.figure(figsize=(8, 6))
sns.heatmap(corr,
            annot=True,      # 수치 표시
            fmt='.2f',       # 소수점 2자리
            cmap='coolwarm', # 색상 팔레트
            vmin=-1, vmax=1, # 색상 범위
            square=True)
plt.title('상관계수 히트맵')
plt.show()
```

---

## 비교 시각화

### 막대그래프 — 그룹 간 비교

```python
# 그룹별 평균 비교
group_means = df.groupby('category')['revenue'].mean().sort_values(ascending=False)

fig, ax = plt.subplots()
bars = ax.bar(group_means.index, group_means.values, color='steelblue')
ax.set_title('카테고리별 평균 매출')
ax.set_ylabel('평균 매출 (만원)')

# 막대 위에 수치 표시
for bar, val in zip(bars, group_means.values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f'{val:.0f}', ha='center', va='bottom', fontsize=9)
plt.show()
```

### 선 그래프 — 시계열 변화

```python
# 월별 매출 추이
monthly = df.groupby('month')['revenue'].sum()

plt.plot(monthly.index, monthly.values, marker='o', color='steelblue', linewidth=2)
plt.fill_between(monthly.index, monthly.values, alpha=0.1, color='steelblue')
plt.title('월별 매출 추이')
plt.xlabel('월')
plt.ylabel('매출 (만원)')
plt.grid(axis='y', alpha=0.3)
plt.show()
```

---

## 차트 선택 가이드

| 목적 | 추천 차트 |
|------|-----------|
| 수치형 변수의 분포 | 히스토그램, 박스플롯 |
| 두 수치형 변수의 관계 | 산점도 |
| 그룹 간 비교 | 막대그래프, 박스플롯 |
| 시간에 따른 변화 | 선 그래프 |
| 비율 / 구성 | 파이차트, 누적 막대 |
| 상관관계 행렬 | 히트맵 |
| 여러 변수 한번에 | 페어플롯 |

---

## 좋은 시각화의 조건

```
□ 제목이 있다 — 이 차트가 무엇을 보여주는지
□ 축 레이블이 있다 — 단위 포함
□ 범례가 명확하다
□ 색상이 의미를 갖는다 — 빨강=위험, 초록=안전 등
□ 불필요한 요소가 없다 — 3D 효과, 그라데이션은 정보를 흐림
□ 이상값이 설명된다 — "이것은 왜 이렇게 크은가"
```

---

> 차트는 데이터를 보여주는 것이 아닙니다. 데이터에서 발견한 이야기를 전달하는 것입니다. 이야기가 없는 차트는 벽지입니다.

---

## 실습

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 실습 데이터 (Titanic 또는 아래 생성 데이터 활용)
np.random.seed(42)
n = 500
df = pd.DataFrame({
    'age':      np.random.normal(35, 10, n).clip(18, 70).astype(int),
    'income':   np.random.exponential(50000, n),
    'score':    np.random.normal(70, 15, n).clip(0, 100),
    'category': np.random.choice(['A', 'B', 'C'], n),
    'month':    np.random.choice(range(1, 13), n)
})

# 1. age의 히스토그램 + KDE
# 2. category별 score 박스플롯
# 3. age vs income 산점도 (추세선 포함)
# 4. 수치형 변수들의 상관 히트맵
# 5. month별 income 합계 선 그래프
#
# 각 차트에 제목, 축 레이블을 빠짐없이 추가하세요.
```
