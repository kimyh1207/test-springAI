---
title: "13-4. ★확장 — 운영 중 모델 갱신과 롤백 전략"
order: 4
tags: [model-update, rollback, blue-green, canary, shadow-mode]
status: draft
author: vivace
---

# 13-4. ★확장 — 운영 중 모델 갱신과 롤백 전략

더 좋은 모델이 생겼다고 그냥 교체하면 안 됩니다. 서비스 중단 없이, 리스크를 최소화하면서 전환하는 전략이 필요합니다.

---

## 배포 전략 비교

| 전략 | 방법 | 위험도 | 복잡도 |
|------|------|--------|--------|
| **직접 교체** | 기존 모델 → 새 모델 | 높음 | 낮음 |
| **블루-그린** | 두 환경 동시 운영 후 전환 | 낮음 | 중간 |
| **카나리** | 일부 트래픽만 새 모델로 | 낮음 | 중간 |
| **섀도우** | 새 모델은 관찰만, 응답은 기존 | 없음 | 높음 |

---

## 섀도우 배포 — 리스크 없이 검증

새 모델을 실제 트래픽으로 테스트하되, 응답은 기존 모델이 합니다.

```python
import asyncio
import logging

logger = logging.getLogger(__name__)

class ShadowPredictor:
    def __init__(self, production_model, shadow_model):
        self.production = production_model
        self.shadow = shadow_model
    
    async def predict(self, features: dict) -> dict:
        # 프로덕션 모델 결과
        prod_result = self._predict_with(self.production, features)
        
        # 섀도우 모델은 비동기로 실행 (응답 지연 없음)
        asyncio.create_task(self._shadow_predict(features, prod_result))
        
        return prod_result  # 항상 프로덕션 결과 반환
    
    async def _shadow_predict(self, features: dict, prod_result: dict):
        try:
            shadow_result = self._predict_with(self.shadow, features)
            
            # 두 결과 비교 로깅
            diff = abs(prod_result["churn_probability"] - shadow_result["churn_probability"])
            logger.info("shadow_comparison",
                       prod_prob=prod_result["churn_probability"],
                       shadow_prob=shadow_result["churn_probability"],
                       tier_match=(prod_result["risk_tier"] == shadow_result["risk_tier"]),
                       probability_diff=round(diff, 4))
        except Exception as e:
            logger.error("shadow_prediction_failed", error=str(e))
    
    def _predict_with(self, model, features: dict) -> dict:
        prob = float(model.predict_proba([list(features.values())])[0][1])
        tier = "고위험" if prob >= 0.6 else "중위험" if prob >= 0.3 else "저위험"
        return {"churn_probability": prob, "risk_tier": tier}
```

섀도우 배포 기간(보통 1~2주) 동안 비교 로그를 분석합니다. tier_match 비율이 90% 이상이고 새 모델 성능이 개선됐다면 전환합니다.

---

## 카나리 배포

트래픽의 일부(5~10%)만 새 모델로 보내고 성능을 비교합니다.

```python
import random

class CanaryRouter:
    def __init__(self, production_model, canary_model, canary_fraction: float = 0.1):
        self.production = production_model
        self.canary = canary_model
        self.canary_fraction = canary_fraction
    
    def predict(self, features: dict, customer_id: str) -> dict:
        # customer_id 해시로 결정적 라우팅 (동일 고객은 항상 같은 모델)
        use_canary = (hash(customer_id) % 100) < (self.canary_fraction * 100)
        
        model = self.canary if use_canary else self.production
        model_name = "canary" if use_canary else "production"
        
        result = self._run(model, features)
        result["model_variant"] = model_name
        
        return result
    
    def _run(self, model, features: dict) -> dict:
        prob = float(model.predict_proba([list(features.values())])[0][1])
        return {
            "churn_probability": round(prob, 4),
            "risk_tier": "고위험" if prob >= 0.6 else "중위험" if prob >= 0.3 else "저위험"
        }
```

카나리 트래픽 비율은 단계적으로 올립니다: 5% → 20% → 50% → 100%.

---

## 롤백 — 빠르게, 자동으로

```python
# MLflow에서 이전 버전 로드
from mlflow.tracking import MlflowClient
import mlflow.sklearn

client = MlflowClient()

def rollback_to_previous_version(model_name: str) -> None:
    versions = client.get_latest_versions(model_name, stages=["Production", "Staging"])
    
    prod_versions = sorted(
        [v for v in versions if v.current_stage == "Production"],
        key=lambda v: int(v.version)
    )
    
    if len(prod_versions) < 2:
        raise ValueError("롤백할 이전 버전이 없습니다.")
    
    current = prod_versions[-1]
    previous = prod_versions[-2]
    
    # 현재 버전 → Staging
    client.transition_model_version_stage(model_name, current.version, "Staging")
    # 이전 버전 → Production
    client.transition_model_version_stage(model_name, previous.version, "Production")
    
    logger.warning("model_rollback",
                  from_version=current.version,
                  to_version=previous.version)

# GitHub Actions 롤백 워크플로
# workflow_dispatch로 수동 트리거 또는 알림 기반 자동 트리거
```

---

## 자동 롤백 트리거

```python
class AutoRollbackMonitor:
    def __init__(self, error_rate_threshold: float = 0.05,
                 latency_p95_threshold: float = 1.0):
        self.error_rate_threshold = error_rate_threshold
        self.latency_threshold = latency_p95_threshold
        self.consecutive_violations = 0
        self.violation_limit = 3  # 3회 연속 위반 시 롤백
    
    def check(self, error_rate: float, latency_p95: float) -> bool:
        violated = (error_rate > self.error_rate_threshold or
                   latency_p95 > self.latency_threshold)
        
        if violated:
            self.consecutive_violations += 1
            logger.warning("slo_violation",
                          error_rate=error_rate,
                          latency_p95=latency_p95,
                          consecutive=self.consecutive_violations)
            
            if self.consecutive_violations >= self.violation_limit:
                logger.error("triggering_auto_rollback")
                rollback_to_previous_version("churn-predictor")
                return True
        else:
            self.consecutive_violations = 0
        
        return False
```

---

## 배포 체크리스트

```
배포 전:
[ ] 새 모델 성능이 기존 모델 대비 개선됐는가 (val AUC 비교)
[ ] 테스트 파이프라인 통과
[ ] 섀도우 배포로 충분히 검증 (최소 1주)
[ ] 롤백 절차 문서화 및 테스트

배포 중:
[ ] 카나리 5% 시작
[ ] 오류율, 지연 시간 실시간 모니터링
[ ] 카나리 비율 단계적 증가 (5→20→50→100%)

배포 후:
[ ] 48시간 집중 모니터링
[ ] 비즈니스 지표 확인 (이탈 고객 캠페인 효과)
[ ] 이전 모델 버전 보존 (최소 30일)
```

---

> 빠른 배포만큼 중요한 것이 빠른 롤백입니다. 롤백을 1분 안에 할 수 있다면, 새 모델 배포가 두렵지 않습니다.
