---
title: "20-2. 배포 파이프라인과 환경 구성"
order: 202
tags: [deployment, ci-cd, github-actions, docker, environment]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 20-2. 배포 파이프라인과 환경 구성

## 환경 분리

```
개발(dev) → 스테이징(staging) → 프로덕션(prod)

dev:       로컬 Docker Compose, 실제 LLM API 사용
staging:   클라우드 환경, 프로덕션과 동일한 설정
prod:      실제 트래픽 처리, 모니터링 전체 활성화
```

---

## 환경별 설정 관리

```bash
# .env.dev
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
DATABASE_URL=sqlite:///data/dev_shop.db
REDIS_URL=redis://localhost:6379
AI_SERVICE_URL=http://localhost:8000
LOG_LEVEL=DEBUG
DAILY_COST_LIMIT_USD=5.0

# .env.staging
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}  # CI Secret
DATABASE_URL=postgresql://staging-db/shop
REDIS_URL=redis://staging-redis:6379
AI_SERVICE_URL=http://ai-service:8000
LOG_LEVEL=INFO
DAILY_COST_LIMIT_USD=20.0

# .env.prod
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}  # Vault / Secret Manager
DATABASE_URL=postgresql://prod-db/shop
REDIS_URL=redis://prod-redis:6379
AI_SERVICE_URL=http://ai-service:8000
LOG_LEVEL=WARNING
DAILY_COST_LIMIT_USD=50.0
```

```python
# config.py — 환경 기반 설정 로드
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    anthropic_api_key: str
    openai_api_key: str
    database_url: str = "sqlite:///data/shop.db"
    redis_url: str = "redis://localhost:6379"
    log_level: str = "INFO"
    daily_cost_limit_usd: float = 50.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## Docker Compose (개발 환경)

```yaml
# docker-compose.dev.yml
version: "3.9"

services:
  # AI 서비스
  ai-service:
    build:
      context: ./ai_service
      dockerfile: Dockerfile.dev   # 핫리로드 지원
    volumes:
      - ./ai_service:/app           # 소스 마운트
      - ./data:/app/data
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000
    depends_on:
      - redis
      - chroma

  # Spring Boot 게이트웨이
  spring-gateway:
    build:
      context: ./spring-gateway
    ports:
      - "8080:8080"
    environment:
      - AI_SERVICE_URL=http://ai-service:8000
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - ai-service
      - redis

  # Chroma 벡터 DB
  chroma:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma
    ports:
      - "8001:8000"

  # Redis (세션, 캐시, 속도 제한)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # 프론트엔드 (개발 서버)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend/src:/app/src
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8080

volumes:
  chroma_data:
```

---

## GitHub Actions CI/CD

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, staging]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ghcr.io/${{ github.repository_owner }}

jobs:
  # ── 1. 테스트 ──────────────────────────────────────
  test-python:
    name: Python Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      
      - name: Install dependencies
        run: pip install -r ai_service/requirements.txt
      
      - name: Run tests
        run: |
          cd ai_service
          pytest tests/ -v --tb=short \
            --cov=. --cov-report=xml \
            --ignore=tests/integration
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      
      - uses: codecov/codecov-action@v4
        with:
          file: ai_service/coverage.xml

  test-spring:
    name: Spring Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-java@v4
        with:
          java-version: "21"
          distribution: "temurin"
          cache: "gradle"
      
      - name: Run tests
        run: |
          cd spring-gateway
          ./gradlew test jacocoTestReport
        env:
          JWT_SECRET: test-secret-key

  # ── 2. 평가 ──────────────────────────────────────
  evaluate:
    name: Agent Evaluation
    needs: [test-python]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r ai_service/requirements.txt
      
      - name: Run evaluation
        run: python ai_service/evaluation/runner.py --output eval_results.json
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      
      - name: Check pass rate >= 80%
        run: |
          python -c "
          import json, sys
          results = json.load(open('eval_results.json'))
          passed = sum(r['passed'] for r in results)
          rate = passed / len(results)
          print(f'통과율: {rate:.0%} ({passed}/{len(results)})')
          sys.exit(0 if rate >= 0.8 else 1)
          "
      
      - uses: actions/upload-artifact@v4
        with:
          name: eval-results-${{ github.sha }}
          path: eval_results.json

  # ── 3. 빌드 ──────────────────────────────────────
  build:
    name: Build Docker Images
    needs: [test-python, test-spring, evaluate]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    permissions:
      contents: read
      packages: write
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push AI service
        uses: docker/build-push-action@v5
        with:
          context: ./ai_service
          push: true
          tags: |
            ${{ env.IMAGE_PREFIX }}/ai-service:latest
            ${{ env.IMAGE_PREFIX }}/ai-service:${{ github.sha }}
      
      - name: Build and push Spring gateway
        uses: docker/build-push-action@v5
        with:
          context: ./spring-gateway
          push: true
          tags: |
            ${{ env.IMAGE_PREFIX }}/spring-gateway:latest
            ${{ env.IMAGE_PREFIX }}/spring-gateway:${{ github.sha }}

  # ── 4. 배포 ──────────────────────────────────────
  deploy-staging:
    name: Deploy to Staging
    needs: [build]
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to staging
        run: |
          # SSH로 스테이징 서버에 배포
          ssh -i ${{ secrets.STAGING_SSH_KEY }} \
              deploy@${{ secrets.STAGING_HOST }} \
              "cd /app && \
               export IMAGE_TAG=${{ github.sha }} && \
               docker compose pull && \
               docker compose up -d --remove-orphans"
      
      - name: Wait for health check
        run: |
          for i in {1..30}; do
            if curl -sf https://staging.example.com/api/actuator/health; then
              echo "서비스 정상"
              exit 0
            fi
            sleep 10
          done
          echo "헬스체크 실패"
          exit 1
      
      - name: Run smoke tests
        run: |
          curl -sf -X POST https://staging.example.com/api/chat \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${{ secrets.STAGING_TEST_TOKEN }}" \
            -d '{"query": "안녕하세요", "session_id": "ci-test"}'

  deploy-prod:
    name: Deploy to Production
    needs: [deploy-staging]
    runs-on: ubuntu-latest
    environment: production   # GitHub 환경 보호 규칙 (수동 승인)
    
    steps:
      - name: Deploy to production
        run: |
          ssh -i ${{ secrets.PROD_SSH_KEY }} \
              deploy@${{ secrets.PROD_HOST }} \
              "cd /app && \
               export IMAGE_TAG=${{ github.sha }} && \
               docker compose pull && \
               docker compose up -d --remove-orphans"
```

---

## 롤백 절차

```bash
# 이전 버전으로 롤백
#!/bin/bash
# scripts/rollback.sh

PREV_SHA=$1
if [ -z "$PREV_SHA" ]; then
    echo "사용법: ./rollback.sh <이전_commit_sha>"
    exit 1
fi

echo "롤백: $PREV_SHA"
export IMAGE_TAG=$PREV_SHA
docker compose pull
docker compose up -d --remove-orphans

# 헬스체크
sleep 15
if curl -sf http://localhost:8080/actuator/health > /dev/null; then
    echo "롤백 성공"
else
    echo "롤백 후에도 헬스체크 실패"
    exit 1
fi
```

---

## 시크릿 관리

```
로컬 개발:  .env 파일 (gitignore)
CI/CD:     GitHub Secrets (Actions secrets)
프로덕션:  AWS Secrets Manager 또는 HashiCorp Vault

절대로:
  ✗ 코드에 API 키 하드코딩
  ✗ 채팅이나 PR 본문에 키 붙여넣기
  ✗ 로그에 키 출력
```

```python
# 시크릿이 로그에 노출되지 않도록
import logging

class SensitiveDataFilter(logging.Filter):
    """API 키, 토큰이 로그에 남지 않도록 필터링."""
    
    PATTERNS = ["sk-ant-", "sk-", "Bearer ", "password", "secret"]
    
    def filter(self, record):
        message = record.getMessage()
        for pattern in self.PATTERNS:
            if pattern.lower() in message.lower():
                record.msg = "[REDACTED - sensitive data]"
                record.args = ()
                break
        return True
```

> "파이프라인은 실수를 막는 장치다 — 테스트 없이 프로덕션에 가면 사고, 평가 없이 AI가 바뀌면 무음 실패다."
