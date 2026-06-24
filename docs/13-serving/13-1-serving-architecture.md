---
title: "13-1. 서빙 아키텍처(REST · 배치 · 스트림)"
order: 1
tags: [serving, rest, batch, streaming, fastapi]
status: draft
author: vivace
---

# 13-1. 서빙 아키텍처(REST · 배치 · 스트림)

같은 모델도 어떻게 서빙하느냐에 따라 아키텍처가 완전히 달라집니다. 사용 패턴을 먼저 이해해야 합니다.

---

## 서빙 패턴 비교

| 패턴 | 특징 | 예시 |
|------|------|------|
| **REST API** | 요청 즉시 응답, 낮은 지연 | 이탈 위험 스코어링, 추천 |
| **배치** | 대량 데이터를 주기적으로 처리 | 일일 고객 등급 업데이트 |
| **스트림** | 실시간 데이터 흐름에서 예측 | 사기 거래 탐지, 실시간 추천 |

---

## REST API 서빙 — FastAPI

```python
# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import joblib
import pandas as pd
import numpy as np
from typing import Optional

app = FastAPI(title="Churn Prediction API", version="1.0.0")

# 모델 로드 (서버 시작 시 한 번만)
model = joblib.load("churn_model.pkl")

FEATURES = [
    'Tenure', 'CityTier', 'WarehouseToHome', 'HoursSpentOnApp',
    'NumberOfDeviceRegistered', 'SatisfactionScore', 'NumberOfAddress',
    'Complain', 'OrderAmountHikeFromlastYear', 'CouponUsed',
    'OrderCount', 'DaySinceLastOrder', 'CashbackAmount',
    'PreferredLoginDevice', 'PreferredPaymentMode',
    'Gender', 'PreferedOrderCat', 'MaritalStatus'
]

class PredictRequest(BaseModel):
    customer_id: str
    Tenure: float
    CityTier: int = Field(ge=1, le=3)
    WarehouseToHome: float
    HoursSpentOnApp: float
    NumberOfDeviceRegistered: int
    SatisfactionScore: int = Field(ge=1, le=5)
    NumberOfAddress: int
    Complain: int = Field(ge=0, le=1)
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

class PredictResponse(BaseModel):
    customer_id: str
    churn_probability: float
    risk_tier: str
    model_version: str = "1.0.0"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    try:
        data = pd.DataFrame([request.dict(exclude={'customer_id'})])
        
        # 파생변수 생성 (훈련 시와 동일하게)
        data['loyalty_score'] = data['Tenure'] * data['OrderCount']
        data['cashback_per_order'] = data['CashbackAmount'] / (data['OrderCount'] + 1)
        
        prob = float(model.predict_proba(data)[0][1])
        
        if prob >= 0.6:
            tier = "고위험"
        elif prob >= 0.3:
            tier = "중위험"
        else:
            tier = "저위험"
        
        return PredictResponse(
            customer_id=request.customer_id,
            churn_probability=round(prob, 4),
            risk_tier=tier
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/batch", response_model=list[PredictResponse])
def predict_batch(requests: list[PredictRequest]):
    return [predict(req) for req in requests]
```

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 배치 서빙

매일 밤 전체 고객의 이탈 위험 스코어를 계산하고 DB에 저장합니다.

```python
# batch_scoring.py
import pandas as pd
import joblib
import logging
from datetime import datetime
from sqlalchemy import create_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_batch_scoring():
    logger.info("배치 스코어링 시작")
    start_time = datetime.now()
    
    # 1. 데이터 로드
    engine = create_engine("postgresql://user:pw@localhost/db")
    customers = pd.read_sql("SELECT * FROM customers WHERE is_active = true", engine)
    logger.info(f"대상 고객: {len(customers):,}명")
    
    # 2. 피처 생성
    customers['loyalty_score'] = customers['tenure'] * customers['order_count']
    customers['cashback_per_order'] = customers['cashback_amount'] / (customers['order_count'] + 1)
    
    # 3. 예측
    model = joblib.load("churn_model.pkl")
    customers['churn_probability'] = model.predict_proba(customers[FEATURES])[:, 1]
    customers['risk_tier'] = pd.cut(
        customers['churn_probability'],
        bins=[0, 0.3, 0.6, 1.0],
        labels=['저위험', '중위험', '고위험']
    )
    customers['scored_at'] = datetime.now()
    
    # 4. 저장
    result = customers[['customer_id', 'churn_probability', 'risk_tier', 'scored_at']]
    result.to_sql('churn_scores', engine, if_exists='replace', index=False)
    
    elapsed = (datetime.now() - start_time).seconds
    logger.info(f"완료: {len(customers):,}명 처리, {elapsed}초 소요")

if __name__ == "__main__":
    run_batch_scoring()
```

```yaml
# GitHub Actions 스케줄러
name: Daily Batch Scoring
on:
  schedule:
    - cron: '0 1 * * *'  # 매일 오전 1시 (KST 10시)
jobs:
  score:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run scoring
        run: python batch_scoring.py
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

---

## 스트림 서빙 — 실시간 예측

Kafka 메시지를 소비하며 실시간으로 예측합니다.

```python
from kafka import KafkaConsumer, KafkaProducer
import json
import joblib

model = joblib.load("fraud_model.pkl")
producer = KafkaProducer(
    bootstrap_servers=['kafka:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

consumer = KafkaConsumer(
    'transactions',
    bootstrap_servers=['kafka:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    transaction = message.value
    
    features = extract_features(transaction)
    fraud_prob = float(model.predict_proba([features])[0][1])
    
    result = {
        "transaction_id": transaction["id"],
        "fraud_probability": fraud_prob,
        "block": fraud_prob >= 0.9
    }
    
    producer.send('fraud-decisions', result)
    
    if result["block"]:
        producer.send('blocked-transactions', transaction)
```

---

> REST는 요청-응답, 배치는 대량-주기, 스트림은 실시간. 세 가지 패턴을 상황에 맞게 선택하고 조합합니다.
