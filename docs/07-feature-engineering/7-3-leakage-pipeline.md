---
title: "7-3. ★확장 — 피처 누수(leakage)와 재현 가능한 파이프라인"
order: 3
tags: [feature-leakage, pipeline, sklearn, reproducibility]
status: draft
author: vivace
---

# 7-3. ★확장 — 피처 누수(leakage)와 재현 가능한 파이프라인

피처 엔지니어링에서 가장 위험한 실수는 피처 누수입니다. 훈련할 때는 완벽하지만 실전에서는 작동하지 않는 모델을 만듭니다. 파이프라인은 이것을 막는 구조적 해결책입니다.

---

## 피처 누수(Feature Leakage)란

**예측 시점에 알 수 없는 정보가 피처에 포함된 것**입니다.

### 예시 1: 직접 누수

```python
# 신용카드 연체 예측
# 목표: 이번 달에 연체할 것인지 예측

# 잘못된 피처
df['num_late_payments_this_month'] = ...  # 이번 달 연체 횟수 → 정답이 들어가 있음
df['total_debt_after_default'] = ...      # 연체 후 총부채 → 미래 정보
```

### 예시 2: 전처리 누수

```python
# 잘못된 방법: 전체 데이터로 정규화 후 분리
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)  # 테스트 데이터의 통계가 훈련에 반영됨

X_train, X_test = train_test_split(X_scaled, ...)

# 올바른 방법: 분리 후 훈련 데이터만으로 fit
X_train, X_test = train_test_split(X, ...)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)  # fit 없이 transform만
```

### 예시 3: Target Encoding 누수

```python
# 잘못된 방법
target_mean = df.groupby('city')['churn'].mean()  # 전체 데이터 기준
df['city_encoded'] = df['city'].map(target_mean)

X_train, X_test, y_train, y_test = train_test_split(...)
# 테스트의 y값이 인코딩에 이미 반영됨

# 올바른 방법
X_train, X_test, y_train, y_test = train_test_split(X, y, ...)
train_target_mean = X_train.assign(target=y_train).groupby('city')['target'].mean()
X_train['city_encoded'] = X_train['city'].map(train_target_mean)
X_test['city_encoded']  = X_test['city'].map(train_target_mean)
```

---

## 누수를 발견하는 법

모델 성능이 비현실적으로 좋으면 누수를 의심합니다.

- 훈련 정확도 99%, 검증 정확도 99%: 의심
- 피처 중요도에서 예상치 못한 변수가 압도적으로 높음: 의심
- 모델을 실전에 배포했더니 성능이 급락: 확인 필요

```python
# 피처 중요도로 누수 탐지
importances = pd.Series(model.feature_importances_, index=feature_cols)
top = importances.sort_values(ascending=False).head(5)
print(top)
# 이 피처들이 예측 시점에 정말 알 수 있는 값인지 도메인 관점에서 확인
```

---

## sklearn Pipeline — 전처리와 모델을 하나로

Pipeline은 전처리 단계와 모델을 연결합니다. `fit`을 호출하면 각 단계가 순서대로 실행됩니다.

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('model', LogisticRegression())
])

pipe.fit(X_train, y_train)
pipe.predict(X_test)
```

`fit(X_train)`을 호출하면 `scaler.fit_transform(X_train)` 후 `model.fit()`이 자동으로 이어집니다. `predict(X_test)`는 `scaler.transform(X_test)` 후 `model.predict()`가 실행됩니다. 누수가 구조적으로 불가능합니다.

---

## ColumnTransformer — 컬럼별 다른 전처리

수치형과 범주형에 서로 다른 전처리를 적용해야 할 때 씁니다.

```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

numeric_features = ['age', 'income', 'tenure']
categorical_features = ['city', 'plan']

numeric_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

categorical_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('encoder', OneHotEncoder(handle_unknown='ignore', drop='first'))
])

preprocessor = ColumnTransformer([
    ('num', numeric_transformer, numeric_features),
    ('cat', categorical_transformer, categorical_features)
])
```

---

## 전체 파이프라인 구성

```python
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_score

full_pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('model', GradientBoostingClassifier(n_estimators=100, random_state=42))
])

# 교차 검증: 각 fold에서 전처리와 훈련이 함께 재실행됨
scores = cross_val_score(full_pipeline, X, y, cv=5, scoring='roc_auc')
print(f'ROC-AUC: {scores.mean():.4f} ± {scores.std():.4f}')

# 최종 훈련 및 저장
full_pipeline.fit(X_train, y_train)

import joblib
joblib.dump(full_pipeline, 'model_pipeline.pkl')

# 서빙 시
loaded = joblib.load('model_pipeline.pkl')
prediction = loaded.predict(new_data)
```

`joblib.dump`로 저장하면 전처리기와 모델이 함께 저장됩니다. 새 데이터가 들어왔을 때 훈련 시와 동일한 전처리가 자동으로 적용됩니다.

---

## 재현 가능성 체크리스트

파이프라인을 만들면서 확인해야 할 것들입니다.

| 항목 | 확인 방법 |
|------|-----------|
| 난수 고정 | `random_state=42` 명시 |
| train/test 분리 후 fit | `fit`은 훈련 데이터만으로 |
| 파이프라인 사용 | `Pipeline` + `ColumnTransformer` |
| 피처 목록 저장 | 서빙 시 같은 컬럼 순서 보장 |
| 피처 누수 검토 | 예측 시점에 해당 피처를 알 수 있는가 |

---

## 하이퍼파라미터 탐색

Pipeline과 GridSearchCV를 결합하면 전처리 파라미터도 함께 최적화할 수 있습니다.

```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'model__n_estimators': [50, 100, 200],
    'model__max_depth': [3, 5, 7],
    'preprocessor__num__imputer__strategy': ['mean', 'median']
}

grid_search = GridSearchCV(full_pipeline, param_grid, cv=5, scoring='roc_auc', n_jobs=-1)
grid_search.fit(X_train, y_train)

print(grid_search.best_params_)
print(f'Best ROC-AUC: {grid_search.best_score_:.4f}')
```

---

> 파이프라인은 불편함을 없애주는 도구가 아닙니다. 실수를 구조적으로 막는 도구입니다. 작은 프로젝트에서부터 습관으로 만들어야 합니다.
