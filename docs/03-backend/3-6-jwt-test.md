---
title: "3-6. ★확장 — 인증/인가(JWT), 테스트 코드, 환경 분리"
order: 6
tags: [jwt, security, testing, spring-boot]
status: draft
author: vivace
---

# 3-6. ★확장 — 인증/인가(JWT) · 테스트 코드 · 환경 분리

실무 서비스가 되려면 세 가지 기반이 필요합니다. 누가 요청하는지 확인하는 **인증**, 코드가 올바르게 동작하는지 검증하는 **테스트**, 개발과 운영을 분리하는 **환경 관리**입니다.

---

## JWT 기반 인증

### 세션 방식 vs JWT 방식

세션은 서버가 로그인 상태를 기억합니다. 서버가 여러 대로 늘어나면(스케일 아웃) 세션 공유 문제가 생깁니다.

JWT(JSON Web Token)는 서버가 상태를 저장하지 않습니다(Stateless). 토큰 자체에 사용자 정보가 담겨 있어 어느 서버에서든 검증할 수 있습니다.

```
세션 방식
클라이언트 → [요청 + 세션ID] → 서버 → DB(세션 조회) → 응답

JWT 방식
클라이언트 → [요청 + JWT] → 서버 → 토큰 서명 검증(DB 불필요) → 응답
```

### JWT 구조

JWT는 `.`으로 구분된 세 부분으로 이루어집니다.

```
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzA5NTU3NjAwfQ.abc123
      Header               Payload                  Signature
```

- **Header**: 알고리즘 정보
- **Payload**: 사용자 ID, 만료 시각 등 클레임
- **Signature**: 서버만 아는 Secret Key로 서명 (변조 방지)

Payload는 Base64 인코딩으로 누구나 읽을 수 있습니다. **민감한 정보(비밀번호 등)를 넣으면 안 됩니다.**

### 구현

```groovy
// build.gradle 의존성 추가
implementation 'io.jsonwebtoken:jjwt-api:0.12.3'
runtimeOnly 'io.jsonwebtoken:jjwt-impl:0.12.3'
runtimeOnly 'io.jsonwebtoken:jjwt-jackson:0.12.3'
implementation 'org.springframework.boot:spring-boot-starter-security'
```

```java
@Component
public class JwtTokenProvider {

    @Value("${jwt.secret}")
    private String secretKey;

    @Value("${jwt.expiration}")
    private long expirationMs;

    // 토큰 생성
    public String generateToken(Long userId) {
        return Jwts.builder()
                .subject(String.valueOf(userId))
                .expiration(new Date(System.currentTimeMillis() + expirationMs))
                .signWith(getSigningKey())
                .compact();
    }

    // 토큰에서 사용자 ID 추출
    public Long getUserId(String token) {
        return Long.parseLong(
                Jwts.parser()
                        .verifyWith(getSigningKey())
                        .build()
                        .parseSignedClaims(token)
                        .getPayload()
                        .getSubject()
        );
    }

    // 토큰 유효성 검증
    public boolean validate(String token) {
        try {
            Jwts.parser().verifyWith(getSigningKey()).build().parseSignedClaims(token);
            return true;
        } catch (JwtException e) {
            return false;
        }
    }

    private SecretKey getSigningKey() {
        return Keys.hmacShaKeyFor(secretKey.getBytes(StandardCharsets.UTF_8));
    }
}
```

```yaml
# application.yml
jwt:
  secret: my-very-long-secret-key-at-least-32-bytes
  expiration: 3600000  # 1시간 (밀리초)
```

---

## 테스트 코드

테스트 없는 코드는 언제 깨질지 모릅니다. 코드가 복잡해질수록 테스트의 가치가 커집니다.

### 단위 테스트 — Service 계층

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private UserService userService;

    @Test
    @DisplayName("이메일 중복 시 예외가 발생한다")
    void createUser_duplicateEmail_throwsException() {
        // given
        UserCreateRequest request = new UserCreateRequest("홍길동", "hong@test.com", "password123");
        given(userRepository.existsByEmail("hong@test.com")).willReturn(true);

        // when & then
        assertThatThrownBy(() -> userService.create(request))
                .isInstanceOf(DuplicateEmailException.class)
                .hasMessageContaining("이미 사용 중인 이메일");
    }

    @Test
    @DisplayName("사용자를 정상적으로 생성한다")
    void createUser_success() {
        // given
        UserCreateRequest request = new UserCreateRequest("홍길동", "hong@test.com", "password123");
        User savedUser = User.builder().id(1L).name("홍길동").email("hong@test.com").build();
        given(userRepository.existsByEmail(any())).willReturn(false);
        given(userRepository.save(any())).willReturn(savedUser);

        // when
        UserResponse response = userService.create(request);

        // then
        assertThat(response.getName()).isEqualTo("홍길동");
        assertThat(response.getEmail()).isEqualTo("hong@test.com");
    }
}
```

**given → when → then** 구조로 테스트를 작성합니다.
- **given**: 테스트 전제 조건 설정
- **when**: 테스트 대상 실행
- **then**: 결과 검증

`@Mock`으로 Repository를 가짜 객체로 대체합니다. 실제 DB 없이 Service 로직만 테스트합니다.

### 통합 테스트 — Controller 계층

```java
@SpringBootTest
@AutoConfigureMockMvc
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    @DisplayName("사용자를 생성한다")
    void createUser() throws Exception {
        UserCreateRequest request = new UserCreateRequest("홍길동", "hong@test.com", "password123");

        mockMvc.perform(post("/api/users")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.name").value("홍길동"));
    }
}
```

---

## 환경 분리

개발(dev), 테스트(test), 운영(prod) 환경은 DB, 로그 레벨, 외부 서비스 설정이 다릅니다. Spring Profile로 환경별 설정을 분리합니다.

```
resources/
├── application.yml          ← 공통 설정
├── application-dev.yml      ← 개발 환경
├── application-test.yml     ← 테스트 환경
└── application-prod.yml     ← 운영 환경
```

```yaml
# application.yml (공통)
spring:
  application:
    name: my-service

---
# application-dev.yml (개발)
spring:
  datasource:
    url: jdbc:h2:mem:devdb
  jpa:
    show-sql: true
    hibernate:
      ddl-auto: create-drop

logging:
  level:
    com.example: DEBUG

---
# application-prod.yml (운영)
spring:
  datasource:
    url: ${DB_URL}           # 환경변수로 주입
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}
  jpa:
    show-sql: false
    hibernate:
      ddl-auto: validate     # 운영에서는 테이블 변경 금지

logging:
  level:
    com.example: WARN
```

```bash
# 개발 환경으로 실행
./gradlew bootRun --args='--spring.profiles.active=dev'

# 운영 환경으로 실행 (JAR 배포 시)
java -jar app.jar --spring.profiles.active=prod
```

운영 환경의 DB 비밀번호, API 키 등 민감한 정보는 코드에 직접 쓰지 않습니다. 환경변수(`${DB_PASSWORD}`)나 AWS Secrets Manager 같은 외부 저장소에서 주입합니다.

---

> 테스트 코드는 미래의 나를 위한 안전망입니다. 오늘 작성한 테스트가 6개월 뒤 리팩토링할 때 "이 코드를 건드려도 괜찮다"는 확신을 줍니다.

---

## 실습

```java
// 1. UserService의 create() 메서드 단위 테스트 작성
//    - 중복 이메일 예외 케이스
//    - 정상 생성 케이스

// 2. UserController 통합 테스트 작성
//    - POST /api/users 성공 케이스 (201 응답 확인)
//    - POST /api/users 검증 실패 케이스 (400 응답 + 오류 메시지 확인)

// 3. 환경 분리 적용
//    - application-dev.yml: H2 인메모리 DB
//    - application-prod.yml: MySQL (URL은 환경변수로)
//    - dev 프로필로 실행하여 동작 확인
```
