---
title: "4-3. ★확장 — 배포 가능한 형태로 마무리하기"
order: 3
tags: [deployment, docker]
status: draft
author: vivace
---

# 4-3. ★확장 — 배포 가능한 형태로 마무리하기

로컬에서만 돌아가는 서비스는 포트폴리오가 되지 않습니다. 외부에서 접근할 수 있어야 비로소 "서비스"입니다. 이 챕터에서는 만든 서비스를 배포 가능한 형태로 정리하고, 실제로 외부에 노출하는 방법을 다룹니다.

---

## 배포 전 체크리스트

코드가 완성됐다고 바로 배포하면 문제가 생깁니다. 배포 전에 확인할 것들입니다.

```
□ H2 인메모리 DB → MySQL/PostgreSQL로 교체 (재시작하면 데이터 사라짐)
□ 하드코딩된 비밀번호, API 키 → 환경변수로 이동
□ JWT Secret Key → 충분히 긴 키, 환경변수로 주입
□ CORS 설정 → 운영 도메인만 허용
□ 로그 레벨 → 운영 환경에서 DEBUG 끄기
□ 예외 처리 → 스택 트레이스가 응답에 노출되지 않는지 확인
```

---

## MySQL로 전환

```yaml
# application-prod.yml
spring:
  datasource:
    url: jdbc:mysql://${DB_HOST}:3306/${DB_NAME}?useSSL=false&characterEncoding=UTF-8
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}
    driver-class-name: com.mysql.cj.jdbc.Driver
  jpa:
    hibernate:
      ddl-auto: validate  # 운영에서는 테이블 자동 변경 금지
    properties:
      hibernate:
        dialect: org.hibernate.dialect.MySQLDialect
```

```groovy
// build.gradle
runtimeOnly 'com.mysql:mysql-connector-j'
```

---

## JAR 빌드와 실행

Spring Boot 애플리케이션은 단일 JAR 파일로 빌드됩니다. 이 파일 하나를 서버에 올려 실행합니다.

```bash
# 빌드 (테스트 포함)
./gradlew build

# 빌드 결과물 위치
ls build/libs/
# my-project-0.0.1-SNAPSHOT.jar

# 실행
java -jar build/libs/my-project-0.0.1-SNAPSHOT.jar \
  --spring.profiles.active=prod \
  --DB_HOST=localhost \
  --DB_NAME=todoapp \
  --DB_USERNAME=root \
  --DB_PASSWORD=secret
```

---

## Docker로 컨테이너화

Docker를 쓰면 "내 컴퓨터에서는 됩니다" 문제가 사라집니다. 어떤 서버든 Docker가 있으면 같은 환경에서 실행됩니다.

```dockerfile
# Dockerfile (프로젝트 루트에 위치)
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

COPY build/libs/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
```

```bash
# 이미지 빌드
./gradlew build
docker build -t todoapp:latest .

# 컨테이너 실행
docker run -d \
  -p 8080:8080 \
  -e SPRING_PROFILES_ACTIVE=prod \
  -e DB_HOST=host.docker.internal \
  -e DB_NAME=todoapp \
  -e DB_USERNAME=root \
  -e DB_PASSWORD=secret \
  --name todoapp \
  todoapp:latest

# 로그 확인
docker logs -f todoapp
```

### Docker Compose — 앱 + DB 함께 실행

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: todoapp
      MYSQL_ROOT_PASSWORD: secret
    volumes:
      - mysql-data:/var/lib/mysql
    ports:
      - "3306:3306"

  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      SPRING_PROFILES_ACTIVE: prod
      DB_HOST: db
      DB_NAME: todoapp
      DB_USERNAME: root
      DB_PASSWORD: secret
    depends_on:
      - db

volumes:
  mysql-data:
```

```bash
# 전체 스택 실행 (백그라운드)
docker compose up -d

# 중지
docker compose down
```

---

## 무료 배포 옵션

로컬을 벗어나 외부에서 접근 가능하게 만드는 가장 빠른 방법들입니다.

| 서비스 | 특징 | 무료 플랜 |
|--------|------|-----------|
| **Railway** | Git push → 자동 배포, DB 포함 | $5 크레딧/월 |
| **Render** | 무료 플랜 있음, 비활성 시 슬립 | 750시간/월 |
| **Fly.io** | Docker 기반, 글로벌 배포 | 공유 CPU 3대 |
| **AWS EC2** | 완전한 제어, 학습 곡선 높음 | 1년 프리 티어 |

포트폴리오 목적이라면 **Railway**가 가장 빠릅니다. GitHub 저장소를 연결하면 push할 때마다 자동 배포됩니다.

### Railway 배포 방법

```bash
# 1. railway.app에서 회원가입 후 프로젝트 생성
# 2. GitHub 저장소 연결
# 3. 환경변수 설정 (Settings → Variables)
#    SPRING_PROFILES_ACTIVE=prod
#    DB_HOST, DB_NAME, DB_USERNAME, DB_PASSWORD
# 4. MySQL 서비스 추가 → 연결 정보 복사
# 5. Deploy → 자동 빌드 및 배포 시작
```

---

## 프론트엔드 배포

HTML/CSS/JS로 만든 프론트엔드는 정적 파일 호스팅 서비스를 씁니다.

| 서비스 | 특징 |
|--------|------|
| **GitHub Pages** | GitHub 저장소에서 바로 배포 |
| **Netlify** | 드래그앤드롭 배포, 도메인 제공 |
| **Vercel** | Git 연동, 자동 배포 |

```bash
# GitHub Pages 배포
# 1. 저장소 Settings → Pages
# 2. Source: main 브랜치 / docs 폴더 또는 루트
# 3. Save → https://kimyh1207.github.io/todoapp 으로 접근 가능
```

프론트엔드를 배포한 뒤 백엔드 CORS 설정에 실제 도메인을 추가해야 합니다.

```java
config.setAllowedOrigins(List.of(
    "http://localhost:5500",
    "https://kimyh1207.github.io"  // 배포된 프론트 도메인 추가
));
```

---

> 배포는 목적지가 아닙니다. 코드가 사용자에게 닿는 순간입니다. 처음 배포해서 외부에서 내 서비스가 동작하는 걸 확인했을 때의 그 느낌, 그게 개발의 보람입니다.

---

## 실습

```bash
# 1. JAR 빌드 및 로컬 실행 확인
./gradlew build
java -jar build/libs/*.jar --spring.profiles.active=dev

# 2. Dockerfile 작성 후 Docker로 실행
docker build -t todoapp .
docker run -p 8080:8080 todoapp

# 3. Railway 또는 Render에 배포
#    → 외부 URL에서 Swagger UI 접근 확인
#    → 프론트엔드에서 실제 배포된 API 연동 확인
```
