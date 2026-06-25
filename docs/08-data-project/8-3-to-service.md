---
title: "8-3. ★확장 — 분석 결과를 서비스/모델로 잇기"
order: 3
tags: [model, service, deployment, data-analysis]
status: draft
author: vivace
---

# 8-3. ★확장 — 분석 결과를 서비스/모델로 잇기

분석이 끝난 뒤 보고서를 쓰면 분석은 거기서 멈춥니다. 분석을 모델로, 모델을 서비스로 이으면 분석이 살아있는 시스템이 됩니다.

---

## 분석 → 모델

EDA에서 발견한 인사이트를 바탕으로 예측 모델을 만듭니다.

### 피처 준비

```python
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer

# 피처 정의
numeric_features = [
    'Tenure', 'CityTier', 'WarehouseToHome', 'HoursSpentOnApp',
    'NumberOfDeviceRegistered', 'SatisfactionScore', 'NumberOfAddress',
    'Complain', 'OrderAmountHikeFromlastYear', 'CouponUsed',
    'OrderCount', 'DaySinceLastOrder', 'CashbackAmount',
    'loyalty_score', 'cashback_per_order'
]
categorical_features = [
    'PreferredLoginDevice', 'PreferredPaymentMode',
    'Gender', 'PreferedOrderCat', 'MaritalStatus'
]

X = df[numeric_features + categorical_features]
y = df['Churn']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
```

### 파이프라인 구성

```python
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

### 모델 훈련과 평가

```python
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix

model_pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('model', GradientBoostingClassifier(n_estimators=200, max_depth=4, random_state=42))
])

model_pipeline.fit(X_train, y_train)

y_pred = model_pipeline.predict(X_test)
y_prob = model_pipeline.predict_proba(X_test)[:, 1]

print(classification_report(y_test, y_pred, target_names=['잔류', '이탈']))
print(f'ROC-AUC: {roc_auc_score(y_test, y_prob):.4f}')
```

### 모델 저장

```python
import joblib

joblib.dump(model_pipeline, 'churn_model.pkl')
print("모델 저장 완료")

# 검증
loaded = joblib.load('churn_model.pkl')
assert roc_auc_score(y_test, loaded.predict_proba(X_test)[:, 1]) > 0.80
```

---

## 모델 → 스코어링 시스템

모델을 저장했다면, 새 고객 데이터에 스코어를 부여하는 시스템을 만들 수 있습니다.

```python
def score_customers(customer_df: pd.DataFrame, model_path: str = 'churn_model.pkl') -> pd.DataFrame:
    model = joblib.load(model_path)
    
    churn_prob = model.predict_proba(customer_df[numeric_features + categorical_features])[:, 1]
    
    result = customer_df[['CustomerID']].copy()
    result['churn_probability'] = churn_prob
    result['risk_tier'] = pd.cut(
        churn_prob,
        bins=[0, 0.3, 0.6, 1.0],
        labels=['저위험', '중위험', '고위험']
    )
    return result.sort_values('churn_probability', ascending=False)

# 실행
new_customers = pd.read_csv('new_customers.csv')
scored = score_customers(new_customers)
print(scored.head(10))
```

---

## 모델 → REST API

Spring Boot 백엔드에서 Python 모델을 호출하려면 API로 감싸야 합니다.

```python
# Flask 또는 FastAPI로 감싸기
from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import pandas as pd

app = FastAPI()
model = joblib.load('churn_model.pkl')

class CustomerFeatures(BaseModel):
    Tenure: float
    CityTier: int
    WarehouseToHome: float
    HoursSpentOnApp: float
    NumberOfDeviceRegistered: int
    SatisfactionScore: int
    NumberOfAddress: int
    Complain: int
    OrderAmountHikeFromlastYear: float
    CouponUsed: float
    OrderCount: float
    DaySinceLastOrder: float
    CashbackAmount: float
    PreferredLoginDevice: str
    PreferredPaymentMode: str
    Gender: str
    PreferedOrderCat: str
    MaritalStatus: str

@app.post("/predict/churn")
def predict_churn(features: CustomerFeatures):
    input_df = pd.DataFrame([features.dict()])
    input_df['loyalty_score'] = input_df['Tenure'] * input_df['OrderCount']
    input_df['cashback_per_order'] = input_df['CashbackAmount'] / (input_df['OrderCount'] + 1)
    
    prob = model.predict_proba(input_df[numeric_features + categorical_features])[0][1]
    return {
        "churn_probability": round(float(prob), 4),
        "risk_tier": "고위험" if prob >= 0.6 else "중위험" if prob >= 0.3 else "저위험"
    }
```

```bash
# 실행
uvicorn churn_api:app --host 0.0.0.0 --port 8000
```

---

## Spring Boot에서 호출

```java
@Service
public class ChurnPredictionService {

    private final RestTemplate restTemplate;

    public ChurnRiskResponse predictChurn(CustomerFeatureRequest request) {
        String url = "http://ml-service:8000/predict/churn";
        return restTemplate.postForObject(url, request, ChurnRiskResponse.class);
    }
}
```

---

## 모니터링 — 모델은 살아있어야 한다

배포 후 모델 성능이 시간이 지나면서 저하(model drift)됩니다. 고객 행동이 바뀌기 때문입니다.

```python
# 주간 성능 모니터링 스크립트
def monitor_model_performance(week_data: pd.DataFrame, actual_churn: pd.Series):
    model = joblib.load('churn_model.pkl')
    y_prob = model.predict_proba(week_data[numeric_features + categorical_features])[:, 1]
    
    auc = roc_auc_score(actual_churn, y_prob)
    print(f'이번 주 ROC-AUC: {auc:.4f}')
    
    if auc < 0.75:
        print("경고: 모델 성능 저하 감지. 재훈련이 필요합니다.")
        # 알림 발송 로직
```

| 모니터링 항목 | 기준 | 조치 |
|-------------|------|------|
| ROC-AUC | 0.75 미만 | 재훈련 검토 |
| 예측 분포 변화 | 이탈 예측 비율이 ±10% 이상 변동 | 입력 데이터 점검 |
| 실제 이탈률 | 모델 예측과 30% 이상 차이 | 즉시 재훈련 |

---

## 프로젝트 마무리 체크리스트

```
[ ] 분석 질문이 답해졌는가
[ ] 인사이트가 행동 가능한 문장으로 정리됐는가
[ ] 모델 성능이 목표치를 달성했는가 (ROC-AUC ≥ 0.80)
[ ] 파이프라인이 재현 가능한가 (random_state 고정, fit/transform 분리)
[ ] 모델이 저장됐는가
[ ] API로 서빙 가능한가
[ ] 모니터링 계획이 있는가
```

---

> 분석은 보고서로 끝나서는 안 됩니다. 코드가 되고, API가 되고, 서비스의 일부가 될 때 비로소 가치가 생깁니다.
