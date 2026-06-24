---
title: "12-3. ★확장 — 실험 관리와 재현성"
order: 3
tags: [mlflow, experiment-tracking, reproducibility, model-registry]
status: draft
author: vivace
---

# 12-3. ★확장 — 실험 관리와 재현성

"저번에 성능 좋았던 모델이 뭐였더라?" 실험 관리가 없으면 이 질문에 답할 수 없습니다. MLflow로 모든 실험을 기록하고 재현합니다.

---

## MLflow 설치와 기본 사용

```bash
pip install mlflow scikit-learn
```

```python
import mlflow
import mlflow.sklearn
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score

# 실험 이름 설정
mlflow.set_experiment("churn-prediction")

with mlflow.start_run(run_name="gb-baseline"):
    # 파라미터 기록
    params = {
        "n_estimators": 100,
        "max_depth": 5,
        "learning_rate": 0.1
    }
    mlflow.log_params(params)
    
    # 모델 훈련
    model = GradientBoostingClassifier(**params, random_state=42)
    model.fit(X_train, y_train)
    
    # 지표 기록
    train_auc = roc_auc_score(y_train, model.predict_proba(X_train)[:, 1])
    val_auc   = roc_auc_score(y_val,   model.predict_proba(X_val)[:, 1])
    
    mlflow.log_metrics({
        "train_roc_auc": train_auc,
        "val_roc_auc":   val_auc,
        "overfit_gap":   train_auc - val_auc
    })
    
    # 모델 저장
    mlflow.sklearn.log_model(model, "model")
    
    print(f"Train AUC: {train_auc:.4f}, Val AUC: {val_auc:.4f}")
```

```bash
# 브라우저에서 실험 결과 확인
mlflow ui --port 5000
# → http://localhost:5000
```

---

## Optuna + MLflow 결합

하이퍼파라미터 탐색 과정 전체를 기록합니다.

```python
import optuna

def objective(trial):
    with mlflow.start_run(run_name=f"trial-{trial.number}", nested=True):
        params = {
            "n_estimators":    trial.suggest_int("n_estimators", 50, 300),
            "max_depth":       trial.suggest_int("max_depth", 3, 9),
            "learning_rate":   trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample":       trial.suggest_float("subsample", 0.6, 1.0),
            "random_state":    42
        }
        
        mlflow.log_params(params)
        
        model = GradientBoostingClassifier(**params)
        score = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc').mean()
        
        mlflow.log_metric("cv_roc_auc", score)
        return score

with mlflow.start_run(run_name="optuna-study"):
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=50)
    
    mlflow.log_params(study.best_params)
    mlflow.log_metric("best_roc_auc", study.best_value)
    
    print(f"최적 파라미터: {study.best_params}")
```

---

## Model Registry — 모델 버전 관리

```python
# 최종 모델을 레지스트리에 등록
with mlflow.start_run(run_name="final-model"):
    best_params = study.best_params
    best_params["random_state"] = 42
    
    final_model = GradientBoostingClassifier(**best_params)
    final_model.fit(X_train, y_train)
    
    test_auc = roc_auc_score(y_test, final_model.predict_proba(X_test)[:, 1])
    mlflow.log_metric("test_roc_auc", test_auc)
    
    # 레지스트리에 등록
    mlflow.sklearn.log_model(
        final_model,
        artifact_path="model",
        registered_model_name="churn-predictor"
    )
```

```python
# 스테이지 전환: Staging → Production
from mlflow.tracking import MlflowClient

client = MlflowClient()

# 최신 버전을 Production으로 승격
client.transition_model_version_stage(
    name="churn-predictor",
    version=1,
    stage="Production"
)
```

```python
# 서빙: Production 모델 로드
model_uri = "models:/churn-predictor/Production"
loaded_model = mlflow.sklearn.load_model(model_uri)

predictions = loaded_model.predict_proba(X_new)[:, 1]
```

---

## 재현성 체크리스트

```python
import random
import numpy as np

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    # PyTorch 사용 시
    # torch.manual_seed(seed)
    # torch.cuda.manual_seed_all(seed)

set_seed(42)
```

실험 재현에 필요한 것들:

| 항목 | 방법 |
|------|------|
| 코드 버전 | Git 커밋 해시를 MLflow에 기록 |
| 데이터 버전 | 데이터 파일 해시, DVC 사용 |
| 난수 시드 | 모든 라이브러리에 seed 고정 |
| 환경 | requirements.txt, conda env |
| 하이퍼파라미터 | MLflow params로 기록 |

```python
# Git 커밋 해시를 MLflow 태그로 기록
import subprocess

def get_git_hash():
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD']
        ).decode('ascii').strip()
    except:
        return "unknown"

with mlflow.start_run():
    mlflow.set_tag("git_commit", get_git_hash())
    mlflow.set_tag("data_version", "v2.1")
    # ...
```

---

## 실험 비교

```python
# 여러 실험 결과를 DataFrame으로 가져오기
runs = mlflow.search_runs(
    experiment_names=["churn-prediction"],
    filter_string="metrics.val_roc_auc > 0.80"
)

print(runs[["run_id", "params.n_estimators", "params.max_depth",
            "metrics.val_roc_auc", "metrics.overfit_gap"]]
      .sort_values("metrics.val_roc_auc", ascending=False)
      .head(10))
```

---

> 실험 관리는 귀찮은 작업이 아닙니다. 6개월 뒤 "이 모델 어떻게 만들었지?"라는 질문에 30초 안에 답할 수 있게 해주는 보험입니다.
