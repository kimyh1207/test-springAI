---
title: "12-1. 학습·검증·평가 지표"
order: 1
tags: [metrics, classification, regression, cross-validation]
status: draft
author: vivace
---

# 12-1. 학습·검증·평가 지표

"모델 정확도가 95%입니다." 이것만으로는 아무것도 모릅니다. 데이터가 불균형하면 아무것도 예측 안 해도 95%가 나올 수 있습니다. 지표를 제대로 선택하고 해석해야 합니다.

---

## 훈련·검증·테스트 세트 분리

```python
from sklearn.model_selection import train_test_split

# 전략적 분리
X_temp, X_test, y_temp, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
X_train, X_val, y_train, y_val = train_test_split(
    X_temp, y_temp, test_size=0.25, random_state=42, stratify=y_temp
)
# 결과: train 60% / val 20% / test 20%

print(f"훈련: {len(X_train)}, 검증: {len(X_val)}, 테스트: {len(X_test)}")
```

**테스트 세트는 마지막에 딱 한 번만 씁니다.** 반복해서 보면 테스트 세트에 과적합됩니다.

---

## 분류 지표

### 혼동 행렬(Confusion Matrix)

```python
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

y_pred = model.predict(X_test)
cm = confusion_matrix(y_test, y_pred)

disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['잔류', '이탈'])
disp.plot(cmap='Blues')
plt.title('혼동 행렬')
plt.show()
```

```
              예측: 잔류    예측: 이탈
실제: 잔류      TN(858)      FP(34)     ← FP: 잔류인데 이탈로 예측 (마케팅 낭비)
실제: 이탈      FN(51)       TP(57)     ← FN: 이탈인데 잔류로 예측 (놓친 고객)
```

### 핵심 지표 4가지

```python
from sklearn.metrics import classification_report

print(classification_report(y_test, y_pred, target_names=['잔류', '이탈']))
```

| 지표 | 공식 | 의미 | 최적화 상황 |
|------|------|------|------------|
| **Accuracy** | (TP+TN)/전체 | 전체 정답률 | 클래스 균형일 때 |
| **Precision** | TP/(TP+FP) | 이탈 예측 중 실제 이탈 비율 | FP 비용이 클 때 (스팸 필터) |
| **Recall** | TP/(TP+FN) | 실제 이탈 중 예측 성공 비율 | FN 비용이 클 때 (이탈 방지) |
| **F1** | 2×P×R/(P+R) | Precision과 Recall의 조화 평균 | 둘 다 중요할 때 |

**이탈 방지**가 목표라면 Recall을 우선시합니다. 이탈 고객을 놓치는 것(FN)이 더 비싸기 때문입니다.

### ROC-AUC

```python
from sklearn.metrics import roc_auc_score, roc_curve

y_prob = model.predict_proba(X_test)[:, 1]
auc = roc_auc_score(y_test, y_prob)
print(f'ROC-AUC: {auc:.4f}')

fpr, tpr, thresholds = roc_curve(y_test, y_prob)
plt.plot(fpr, tpr, label=f'AUC = {auc:.3f}')
plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel('FPR (False Positive Rate)')
plt.ylabel('TPR (Recall)')
plt.title('ROC Curve')
plt.legend()
plt.show()
```

ROC-AUC는 분류 임계값에 무관하게 모델의 전반적 판별 능력을 측정합니다. 0.5 = 랜덤, 1.0 = 완벽.

### 임계값 조정

기본 임계값 0.5를 바꾸면 Precision과 Recall 균형을 조절할 수 있습니다.

```python
# 이탈 방지 목적: Recall 높이기 → 임계값 낮추기
threshold = 0.35
y_pred_adjusted = (y_prob >= threshold).astype(int)

print(classification_report(y_test, y_pred_adjusted))
```

---

## 회귀 지표

```python
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

mae  = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2   = r2_score(y_test, y_pred)

print(f'MAE:  {mae:.2f}')   # 평균 절대 오차 (원래 단위)
print(f'RMSE: {rmse:.2f}')  # 큰 오차에 더 민감
print(f'R²:   {r2:.4f}')    # 분산 설명력 (1에 가까울수록 좋음)
```

| 지표 | 특징 | 사용 시기 |
|------|------|---------|
| MAE | 이상치 덜 민감, 해석 쉬움 | 오차 크기가 선형으로 중요할 때 |
| RMSE | 큰 오차에 패널티 | 큰 오차를 특히 피해야 할 때 |
| R² | 상대적 설명력 | 모델 간 비교 |

---

## 교차 검증

단일 train/test 분리는 운에 따라 결과가 달라집니다. K-Fold 교차 검증으로 신뢰할 수 있는 성능 추정을 합니다.

```python
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.ensemble import GradientBoostingClassifier

model = GradientBoostingClassifier(n_estimators=100, random_state=42)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')

print(f'ROC-AUC: {scores.mean():.4f} ± {scores.std():.4f}')
print(f'각 Fold: {scores.round(4)}')
```

`StratifiedKFold`: 각 fold에서 클래스 비율이 유지되도록 분할합니다. 불균형 데이터에서 필수입니다.

---

## 클래스 불균형 처리

이탈률이 16%라면 84%를 모두 잔류로 예측해도 정확도가 84%입니다. 이건 쓸모없는 모델입니다.

```python
from sklearn.utils.class_weight import compute_class_weight
import numpy as np

# 방법 1: 클래스 가중치 조정
class_weights = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
weight_dict = dict(enumerate(class_weights))

model = GradientBoostingClassifier(random_state=42)
# 트리 기반 모델은 sample_weight로 처리
from sklearn.utils import class_weight
sample_weights = class_weight.compute_sample_weight('balanced', y_train)
model.fit(X_train, y_train, sample_weight=sample_weights)

# 방법 2: 오버샘플링 (SMOTE)
from imblearn.over_sampling import SMOTE

smote = SMOTE(random_state=42)
X_resampled, y_resampled = smote.fit_resample(X_train, y_train)
print(f"리샘플링 후 분포: {pd.Series(y_resampled).value_counts()}")
```

---

> 지표는 목적에 따라 선택합니다. 암 진단이라면 Recall, 스팸 필터라면 Precision, 일반적인 비교라면 F1. 정확도(Accuracy)만 보는 습관은 버려야 합니다.
