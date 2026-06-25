---
title: "13-3. 모니터링 · 로깅 · 비용 관리"
order: 3
tags: [monitoring, logging, prometheus, grafana, model-drift]
status: draft
author: vivace
---

# 13-3. 모니터링 · 로깅 · 비용 관리

배포 후가 시작입니다. 서비스가 정상 작동하는지, 모델 성능이 유지되는지, 비용이 예산 안에 있는지 지속적으로 봐야 합니다.

---

## 애플리케이션 메트릭 — Prometheus

```python
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time

app = FastAPI()

# 메트릭 정의
PREDICTION_COUNT = Counter(
    'predictions_total',
    'Total number of predictions',
    ['risk_tier', 'status']
)
PREDICTION_LATENCY = Histogram(
    'prediction_latency_seconds',
    'Prediction latency',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)
HIGH_RISK_GAUGE = Gauge(
    'high_risk_customers_ratio',
    'Ratio of high-risk customers in recent predictions'
)

@app.post("/predict")
def predict(request: PredictRequest):
    start = time.time()
    
    try:
        result = _do_predict(request)
        PREDICTION_COUNT.labels(risk_tier=result.risk_tier, status='success').inc()
        return result
    except Exception as e:
        PREDICTION_COUNT.labels(risk_tier='unknown', status='error').inc()
        raise
    finally:
        PREDICTION_LATENCY.observe(time.time() - start)

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ai-service'
    scrape_interval: 15s
    static_configs:
      - targets: ['ai-service:8000']
```

---

## 구조화된 로깅

```python
import structlog
import logging

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

@app.post("/predict")
def predict(request: PredictRequest):
    log = logger.bind(customer_id=request.customer_id)
    
    result = _do_predict(request)
    
    log.info("prediction_made",
             churn_probability=result.churn_probability,
             risk_tier=result.risk_tier,
             tenure=request.Tenure,
             complain=request.Complain)
    
    return result
```

출력 예:
```json
{"timestamp": "2024-03-15T10:23:45Z", "event": "prediction_made", 
 "customer_id": "CUST-123", "churn_probability": 0.72, 
 "risk_tier": "고위험", "tenure": 2, "complain": 1}
```

---

## 모델 드리프트 감지

배포 후 시간이 지나면 입력 데이터 분포가 바뀌고 모델 성능이 저하됩니다.

```python
import numpy as np
from scipy import stats

class DriftDetector:
    def __init__(self, reference_data: np.ndarray, threshold: float = 0.05):
        self.reference_data = reference_data
        self.threshold = threshold  # p-value 임계값
    
    def detect(self, current_data: np.ndarray, feature_name: str) -> dict:
        # KS 검정: 두 분포가 동일한지 검사
        stat, p_value = stats.ks_2samp(self.reference_data, current_data)
        
        drifted = p_value < self.threshold
        
        result = {
            "feature": feature_name,
            "ks_statistic": round(stat, 4),
            "p_value": round(p_value, 4),
            "drifted": drifted
        }
        
        if drifted:
            logger.warning("data_drift_detected", **result)
        
        return result

# 주간 드리프트 모니터링 스크립트
def weekly_drift_check():
    ref_data = pd.read_parquet("reference_data.parquet")
    current_data = pd.read_sql("SELECT * FROM prediction_logs WHERE date >= NOW() - INTERVAL '7 days'", engine)
    
    numeric_features = ['Tenure', 'CashbackAmount', 'OrderCount']
    detectors = {col: DriftDetector(ref_data[col].values) for col in numeric_features}
    
    for col in numeric_features:
        result = detectors[col].detect(current_data[col].values, col)
        if result["drifted"]:
            send_alert(f"피처 드리프트 감지: {col} (p={result['p_value']})")
```

---

## Grafana 대시보드 구성

```json
{
  "panels": [
    {
      "title": "예측 처리량 (RPS)",
      "targets": [{"expr": "rate(predictions_total[5m])"}]
    },
    {
      "title": "P95 응답 시간",
      "targets": [{"expr": "histogram_quantile(0.95, rate(prediction_latency_seconds_bucket[5m]))"}]
    },
    {
      "title": "오류율",
      "targets": [{"expr": "rate(predictions_total{status='error'}[5m]) / rate(predictions_total[5m])"}]
    },
    {
      "title": "고위험 고객 비율",
      "targets": [{"expr": "high_risk_customers_ratio"}]
    }
  ]
}
```

알림 규칙:
- 오류율 > 1% → Slack 알림
- P95 응답 > 500ms → Slack 알림
- 고위험 비율 갑자기 +20% 증가 → 드리프트 의심

---

## LLM API 비용 관리

LLM을 쓰는 경우 토큰 사용량을 추적하고 예산을 설정합니다.

```python
class CostTracker:
    # 2024년 기준 근사값
    PRICE_PER_1K_TOKENS = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    }
    
    def __init__(self, monthly_budget_usd: float):
        self.monthly_budget = monthly_budget_usd
        self.monthly_cost = 0.0
    
    def track(self, model: str, input_tokens: int, output_tokens: int):
        prices = self.PRICE_PER_1K_TOKENS.get(model, {"input": 0.01, "output": 0.03})
        cost = (input_tokens / 1000 * prices["input"] +
                output_tokens / 1000 * prices["output"])
        
        self.monthly_cost += cost
        
        if self.monthly_cost > self.monthly_budget * 0.8:
            logger.warning("budget_80pct_reached",
                          spent=self.monthly_cost,
                          budget=self.monthly_budget)
        
        return cost
```

---

> 모니터링 없는 서비스는 눈 감고 운전하는 것입니다. 장애는 대부분 지표에서 먼저 신호를 보냅니다.
