---
title: "13장. 모델 서빙과 AIOps 구성"
order: 13
tags: [serving, aiops, docker, monitoring]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 13장. 모델 서빙과 AIOps 구성

## 들어가며

모델을 만들었다고 끝이 아닙니다. 실제 서비스에 올리고, 안정적으로 운영하고, 성능 저하를 감지하고, 필요하면 새 모델로 교체하는 것까지가 ML 엔지니어의 일입니다.

---

## 이 챕터에서 배울 것

- **[13-1. 서빙 아키텍처(REST·배치·스트림)](./13-1-serving-architecture.md)** — 예측 방식에 따라 아키텍처가 달라진다
- **[13-2. 컨테이너화와 배포](./13-2-containerization.md)** — Docker와 GitHub Actions로 자동화된 배포 파이프라인
- **[13-3. 모니터링·로깅·비용 관리](./13-3-monitoring.md)** — 살아있는 서비스는 지켜봐야 한다
- **[13-4. ★ 운영 중 모델 갱신과 롤백 전략](./13-4-update-rollback.md)** — 서비스 중단 없이 더 좋은 모델로 교체하는 방법

---

> 훈련된 모델은 도구입니다. 도구가 가치를 만들려면 사용자 손에 닿아야 합니다.

이 챕터를 마치면 ML 모델을 REST API로 서빙하고, 컨테이너로 배포하고, 운영 중 성능을 모니터링할 수 있습니다.
