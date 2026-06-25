---
title: "3-1. Spring Boot 프로젝트 구조와 의존성 관리"
order: 1
tags: [spring-boot, gradle, maven]
status: draft
author: vivace
---

# 3-1. Spring Boot 프로젝트 구조와 의존성 관리

Spring Boot 프로젝트를 처음 열면 파일이 많아 막막합니다. 하지만 구조는 단순합니다. 어디에 무엇이 있는지 한 번만 파악하면 이후엔 익숙한 집처럼 느껴집니다.

---

## Spring Boot란

Spring Boot는 Spring Framework 위에서 동작하는 도구입니다. Spring은 강력하지만 설정이 복잡합니다. Spring Boot는 그 복잡한 설정을 자동화합니다. 개발자는 비즈니스 로직에만 집중할 수 있습니다.

```
Spring Framework  →  강력하지만 설정 복잡
Spring Boot       →  자동 설정 + 내장 서버 + 빠른 시작
```

내장 Tomcat 서버가 포함되어 있어 별도 서버 설치 없이 `main()` 하나로 서비스가 실행됩니다.

---

## 프로젝트 생성

Spring Initializr(start.spring.io)에서 시작합니다. 설정 후 ZIP을 다운받아 IDE에서 열면 됩니다.

```
Project:  Gradle - Groovy
Language: Java
Spring Boot: 3.x.x
Packaging: Jar
Java: 17

Dependencies:
  - Spring Web
  - Spring Data JPA
  - H2 Database (개발용 인메모리 DB)
  - Lombok
  - Validation
```

---

## 프로젝트 구조

```
my-project/
├── src/
│   ├── main/
│   │   ├── java/com/example/myproject/
│   │   │   ├── MyProjectApplication.java  ← 진입점 (main 메서드)
│   │   │   ├── controller/               ← HTTP 요청 처리
│   │   │   ├── service/                  ← 비즈니스 로직
│   │   │   ├── repository/               ← DB 접근
│   │   │   ├── domain/                   ← 엔티티(DB 테이블 매핑)
│   │   │   └── dto/                      ← 요청/응답 데이터 구조
│   │   └── resources/
│   │       ├── application.yml           ← 설정 파일
│   │       └── static/                   ← 정적 파일 (HTML, CSS)
│   └── test/
│       └── java/                         ← 테스트 코드
├── build.gradle                          ← 의존성 관리
└── gradlew                               ← Gradle 실행 스크립트
```

각 폴더의 역할이 명확합니다. 새 기능을 추가할 때 어느 폴더에 무엇을 만들어야 할지 구조가 알려줍니다.

---

## 진입점 — Application 클래스

```java
@SpringBootApplication
public class MyProjectApplication {
    public static void main(String[] args) {
        SpringApplication.run(MyProjectApplication.class, args);
    }
}
```

`@SpringBootApplication` 하나가 세 가지 역할을 합니다.

| 애너테이션 | 역할 |
|-----------|------|
| `@SpringBootConfiguration` | 설정 클래스 선언 |
| `@EnableAutoConfiguration` | 의존성 기반 자동 설정 활성화 |
| `@ComponentScan` | 같은 패키지의 컴포넌트 자동 등록 |

`SpringApplication.run()`이 호출되는 순간 내장 Tomcat이 시작되고 서비스가 올라옵니다.

---

## 의존성 관리 — build.gradle

Gradle은 라이브러리를 자동으로 내려받아 프로젝트에 연결합니다.

```groovy
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-starter-validation'
    runtimeOnly 'com.h2database:h2'
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
}
```

`spring-boot-starter-*` 형태의 의존성은 관련 라이브러리를 한 번에 묶어서 제공합니다. 버전 충돌을 직접 관리할 필요가 없습니다.

---

## 설정 파일 — application.yml

서버 포트, 데이터베이스 연결, 로그 레벨 등 환경 설정을 담습니다.

```yaml
spring:
  datasource:
    url: jdbc:h2:mem:testdb
    driver-class-name: org.h2.Driver
  jpa:
    hibernate:
      ddl-auto: create-drop   # 시작 시 테이블 생성, 종료 시 삭제
    show-sql: true            # 실행되는 SQL 콘솔에 출력
  h2:
    console:
      enabled: true

server:
  port: 8080
```

---

## Lombok — 반복 코드 제거

Java는 getter, setter, 생성자 코드가 많습니다. Lombok은 애너테이션 하나로 이를 자동 생성합니다.

```java
// Lombok 없이
public class User {
    private Long id;
    private String name;
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
}

// Lombok 사용
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class User {
    private Long id;
    private String name;
}
```

| 애너테이션 | 역할 |
|-----------|------|
| `@Getter` / `@Setter` | getter/setter 자동 생성 |
| `@NoArgsConstructor` | 기본 생성자 |
| `@AllArgsConstructor` | 전체 필드 생성자 |
| `@RequiredArgsConstructor` | final 필드 생성자 (의존성 주입에 주로 사용) |
| `@Builder` | 빌더 패턴 |

---

> 프로젝트 구조를 외우려 하지 마세요. 왜 이렇게 나뉘었는지를 이해하면 자연스럽게 손에 익습니다.

---

## 실습

```bash
# 1. start.spring.io에서 프로젝트 생성 후 IDE에서 열기

# 2. 애플리케이션 실행
./gradlew bootRun

# 3. 브라우저에서 확인
# http://localhost:8080            → Whitelabel Error Page (정상. 아직 컨트롤러 없음)
# http://localhost:8080/h2-console → H2 DB 웹 콘솔
```
