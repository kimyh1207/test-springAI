---
title: "12-2. 하이퍼파라미터 튜닝과 과적합 제어"
order: 2
tags: [hyperparameter, overfitting, regularization, optuna]
status: draft
author: vivace
---

# 12-2. 하이퍼파라미터 튜닝과 과적합 제어

모델이 훈련 데이터에서는 잘 되는데 검증 데이터에서 성능이 떨어진다면 과적합입니다. 하이퍼파라미터 튜닝은 이 균형을 잡는 과정입니다.

---

## 과적합 진단

```python
import matplotlib.pyplot as plt
from sklearn.model_selection import learning_curve
import numpy as np

def plot_learning_curve(model, X, y):
    sizes, train_scores, val_scores = learning_curve(
        model, X, y,
        train_sizes=np.linspace(0.1, 1.0, 10),
        cv=5, scoring='roc_auc'
    )
    
    plt.figure(figsize=(8, 5))
    plt.plot(sizes, train_scores.mean(axis=1), 'o-', label='훈련')
    plt.plot(sizes, val_scores.mean(axis=1),  's-', label='검증')
    plt.fill_between(sizes, train_scores.mean(1)-train_scores.std(1),
                            train_scores.mean(1)+train_scores.std(1), alpha=0.1)
    plt.fill_between(sizes, val_scores.mean(1)-val_scores.std(1),
                            val_scores.mean(1)+val_scores.std(1), alpha=0.1)
    plt.xlabel('훈련 데이터 크기')
    plt.ylabel('ROC-AUC')
    plt.legend()
    plt.title('Learning Curve')
    plt.show()

plot_learning_curve(model, X_train, y_train)
```

**과적합**: 훈련 점수 >> 검증 점수 → 규제 강화, 데이터 추가  
**과소적합**: 둘 다 낮음 → 모델 복잡도 증가, 피처 추가

---

## GridSearchCV — 전수 탐색

```python
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import GradientBoostingClassifier

param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [3, 5, 7],
    'learning_rate': [0.05, 0.1, 0.2],
    'min_samples_leaf': [10, 20]
}

grid_search = GridSearchCV(
    GradientBoostingClassifier(random_state=42),
    param_grid,
    cv=5,
    scoring='roc_auc',
    n_jobs=-1,
    verbose=1
)

grid_search.fit(X_train, y_train)

print(f"최적 파라미터: {grid_search.best_params_}")
print(f"최적 ROC-AUC: {grid_search.best_score_:.4f}")

best_model = grid_search.best_estimator_
```

조합이 많으면 시간이 기하급수적으로 늘어납니다. 파라미터 수가 많으면 RandomizedSearchCV나 Optuna를 씁니다.

---

## RandomizedSearchCV — 무작위 샘플링

```python
from sklearn.model_selection import RandomizedSearchCV
from scipy.stats import randint, uniform

param_dist = {
    'n_estimators': randint(50, 300),
    'max_depth': randint(3, 10),
    'learning_rate': uniform(0.01, 0.3),
    'subsample': uniform(0.6, 0.4),
    'min_samples_leaf': randint(5, 30)
}

random_search = RandomizedSearchCV(
    GradientBoostingClassifier(random_state=42),
    param_dist,
    n_iter=50,          # 50가지 조합만 시도
    cv=5,
    scoring='roc_auc',
    n_jobs=-1,
    random_state=42
)

random_search.fit(X_train, y_train)
print(f"최적: {random_search.best_params_}")
```

---

## Optuna — 베이지안 최적화

지금까지 시도한 결과를 학습해 다음 탐색 방향을 결정합니다. GridSearch보다 적은 시도로 더 좋은 파라미터를 찾습니다.

```python
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

def objective(trial):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 300),
        'max_depth': trial.suggest_int('max_depth', 3, 9),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 5, 30),
        'random_state': 42
    }
    
    model = GradientBoostingClassifier(**params)
    score = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc').mean()
    return score

study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=100, show_progress_bar=True)

print(f"최적 파라미터: {study.best_params}")
print(f"최고 ROC-AUC: {study.best_value:.4f}")

# 파라미터 중요도 시각화
optuna.visualization.plot_param_importances(study).show()
```

---

## 과적합 제어 기법

### 조기 종료 (Early Stopping)

트리가 많아질수록 과적합이 심해집니다. 검증 성능이 나빠지면 멈춥니다.

```python
from sklearn.ensemble import GradientBoostingClassifier

model = GradientBoostingClassifier(
    n_estimators=1000,       # 최대값 높게 설정
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    random_state=42,
    validation_fraction=0.1,
    n_iter_no_change=20,     # 20번 개선 없으면 중단
    tol=1e-4
)

model.fit(X_train, y_train)
print(f"실제 사용된 트리 수: {model.n_estimators_}")
```

### 정규화

```python
from sklearn.linear_model import LogisticRegression

# L2 정규화 (Ridge): 모든 계수를 작게
lr_l2 = LogisticRegression(penalty='l2', C=0.1, random_state=42)

# L1 정규화 (Lasso): 불필요한 계수를 0으로 (피처 선택 효과)
lr_l1 = LogisticRegression(penalty='l1', C=0.1, solver='liblinear', random_state=42)

# Elastic Net: L1 + L2 결합
lr_en = LogisticRegression(penalty='elasticnet', C=0.1,
                            l1_ratio=0.5, solver='saga', random_state=42)
```

`C`는 정규화 강도의 역수입니다. C가 작을수록 정규화가 강합니다.

---

## 앙상블 — 여러 모델을 결합

```python
from sklearn.ensemble import VotingClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

# 소프트 보팅: 확률 평균
voting = VotingClassifier(
    estimators=[
        ('rf', RandomForestClassifier(n_estimators=100, random_state=42)),
        ('gb', GradientBoostingClassifier(n_estimators=100, random_state=42)),
        ('lr', LogisticRegression(random_state=42))
    ],
    voting='soft'
)

# 스태킹: 기본 모델들의 예측을 메타 모델이 학습
stacking = StackingClassifier(
    estimators=[
        ('rf', RandomForestClassifier(n_estimators=100, random_state=42)),
        ('gb', GradientBoostingClassifier(n_estimators=100, random_state=42)),
    ],
    final_estimator=LogisticRegression(),
    cv=5
)

# 성능 비교
for name, clf in [('Voting', voting), ('Stacking', stacking)]:
    scores = cross_val_score(clf, X_train, y_train, cv=5, scoring='roc_auc')
    print(f"{name}: {scores.mean():.4f} ± {scores.std():.4f}")
```

---

> 하이퍼파라미터 튜닝은 검증 세트 기준으로 합니다. 테스트 세트를 보면서 튜닝하면 테스트 세트에 과적합됩니다.
