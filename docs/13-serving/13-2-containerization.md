---
title: "13-2. 컨테이너화와 배포"
order: 2
tags: [docker, github-actions, cicd, deployment]
status: draft
author: vivace
---

# 13-2. 컨테이너화와 배포

모델 서빙 서버를 Docker로 패키징하고 GitHub Actions로 자동 배포합니다.

---

## Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 보안: root가 아닌 사용자로 실행
RUN useradd -m -u 1000 appuser

WORKDIR /app

# 의존성 먼저 설치 (캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드
COPY app.py .
COPY churn_model.pkl .

USER appuser

EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

```
# requirements.txt
fastapi==0.111.0
uvicorn[standard]==0.29.0
scikit-learn==1.4.2
pandas==2.2.1
joblib==1.4.0
pydantic==2.7.0
```

---

## Docker Compose — 전체 스택

```yaml
# docker-compose.yml
services:
  ai-service:
    build:
      context: ./ai-service
      dockerfile: Dockerfile
    image: churn-predictor:latest
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=info
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  spring-backend:
    build: ./backend
    ports:
      - "8080:8080"
    environment:
      - AI_SERVICE_URL=http://ai-service:8000
      - SPRING_PROFILES_ACTIVE=prod
    depends_on:
      ai-service:
        condition: service_healthy
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - spring-backend
```

---

## GitHub Actions CI/CD

```yaml
# .github/workflows/deploy-ai-service.yml
name: Deploy AI Service

on:
  push:
    branches: [main]
    paths:
      - 'ai-service/**'

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/ai-service

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r ai-service/requirements.txt pytest httpx
      - name: Run tests
        run: pytest ai-service/tests/ -v

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=raw,value=latest

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./ai-service
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            cd /opt/app
            docker compose pull ai-service
            docker compose up -d --no-deps ai-service
            docker compose ps
```

---

## API 테스트

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

SAMPLE_REQUEST = {
    "customer_id": "CUST-001",
    "Tenure": 12,
    "CityTier": 1,
    "WarehouseToHome": 15.0,
    "HoursSpentOnApp": 3.0,
    "NumberOfDeviceRegistered": 2,
    "SatisfactionScore": 4,
    "NumberOfAddress": 2,
    "Complain": 0,
    "OrderAmountHikeFromlastYear": 15.0,
    "CouponUsed": 2.0,
    "OrderCount": 8.0,
    "DaySinceLastOrder": 5.0,
    "CashbackAmount": 180.0,
    "PreferredLoginDevice": "Mobile Phone",
    "PreferredPaymentMode": "Credit Card",
    "Gender": "Male",
    "PreferedOrderCat": "Laptop & Accessory",
    "MaritalStatus": "Single"
}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_predict_returns_valid_response():
    response = client.post("/predict", json=SAMPLE_REQUEST)
    assert response.status_code == 200
    
    data = response.json()
    assert data["customer_id"] == "CUST-001"
    assert 0.0 <= data["churn_probability"] <= 1.0
    assert data["risk_tier"] in ["저위험", "중위험", "고위험"]

def test_predict_invalid_input():
    bad_request = SAMPLE_REQUEST.copy()
    bad_request["SatisfactionScore"] = 10  # 범위 초과
    response = client.post("/predict", json=bad_request)
    assert response.status_code == 422
```

---

> 컨테이너는 "내 컴퓨터에서는 되는데" 문제를 없앱니다. CI/CD는 배포를 두려움이 아닌 일상으로 만듭니다.
