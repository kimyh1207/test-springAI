---
title: "3-3. REST API 설계 원칙과 DTO/엔티티 분리"
order: 3
tags: [rest-api, dto, spring-boot]
status: draft
author: vivace
---

# 3-3. REST API 설계 원칙과 DTO/엔티티 분리

좋은 API는 사용하는 사람이 문서를 읽지 않아도 예측할 수 있습니다. URL만 봐도 무엇을 하는지 알고, 응답만 봐도 어떤 데이터가 오는지 알 수 있습니다. 그 예측 가능성을 만드는 것이 REST 설계 원칙입니다.

---

## REST란

REST(Representational State Transfer)는 HTTP를 기반으로 한 API 설계 스타일입니다. 규약이 아닌 가이드라인이지만, 업계 표준처럼 쓰입니다.

핵심은 두 가지입니다. **리소스를 URL로 표현하고, 행위는 HTTP 메서드로 표현합니다.**

```
# 나쁜 예 — 행위가 URL에 섞임
GET  /getUser?id=1
POST /createUser
POST /deleteUser?id=1

# 좋은 예 — 리소스 중심
GET    /users/1       사용자 조회
POST   /users         사용자 생성
PUT    /users/1       사용자 전체 수정
PATCH  /users/1       사용자 일부 수정
DELETE /users/1       사용자 삭제
```

---

## HTTP 메서드와 상태 코드

### HTTP 메서드

| 메서드 | 용도 | 멱등성 |
|--------|------|--------|
| `GET` | 조회 | O (여러 번 호출해도 결과 동일) |
| `POST` | 생성 | X (호출마다 새 리소스 생성) |
| `PUT` | 전체 수정 | O |
| `PATCH` | 일부 수정 | X |
| `DELETE` | 삭제 | O |

### HTTP 상태 코드

| 코드 | 의미 | 사용 상황 |
|------|------|-----------|
| `200 OK` | 성공 | GET, PUT, PATCH 성공 |
| `201 Created` | 생성 성공 | POST 성공 |
| `204 No Content` | 성공 (본문 없음) | DELETE 성공 |
| `400 Bad Request` | 잘못된 요청 | 유효성 검사 실패 |
| `401 Unauthorized` | 인증 필요 | 로그인 안 된 상태 |
| `403 Forbidden` | 권한 없음 | 로그인은 됐지만 접근 불가 |
| `404 Not Found` | 리소스 없음 | 해당 ID 데이터 없음 |
| `500 Internal Server Error` | 서버 오류 | 예상치 못한 서버 에러 |

---

## URL 설계 원칙

```
# 명사 복수형 사용
/users          (O)
/user           (△)
/getUsers       (X)

# 계층 구조 표현
/users/1/posts          사용자 1의 게시글 목록
/users/1/posts/5        사용자 1의 5번 게시글

# 필터/정렬/페이징은 쿼리 파라미터
/posts?category=tech&sort=latest&page=1&size=20

# 버전 관리
/api/v1/users
/api/v2/users
```

---

## DTO와 엔티티 분리

엔티티는 데이터베이스 테이블과 매핑되는 객체입니다. 이것을 API 응답에 그대로 쓰면 문제가 생깁니다.

```java
// 엔티티를 직접 반환하면 안 되는 이유
@GetMapping("/users/{id}")
public User getUser(@PathVariable Long id) {
    return userRepository.findById(id).get(); // 위험!
}
```

이렇게 하면 비밀번호 같은 민감한 필드가 노출됩니다. DB 구조 변경이 API 스펙 변경으로 이어집니다. JPA 연관관계로 인한 무한 순환 참조가 발생할 수 있습니다.

**DTO(Data Transfer Object)** 를 따로 만들어 API 스펙을 엔티티와 분리합니다.

```java
// 엔티티 — DB 매핑
@Entity
@Table(name = "users")
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class User {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false, unique = true)
    private String email;

    @Column(nullable = false)
    private String password;   // 응답에 포함하면 안 됨

    private LocalDateTime createdAt;
}

// 요청 DTO — 클라이언트가 보내는 데이터
@Getter
@NoArgsConstructor
public class UserCreateRequest {
    @NotBlank(message = "이름은 필수입니다.")
    private String name;

    @Email(message = "올바른 이메일 형식이 아닙니다.")
    @NotBlank(message = "이메일은 필수입니다.")
    private String email;

    @NotBlank
    @Size(min = 8, message = "비밀번호는 8자 이상이어야 합니다.")
    private String password;
}

// 응답 DTO — 클라이언트에게 돌려주는 데이터
@Getter
@Builder
public class UserResponse {
    private Long id;
    private String name;
    private String email;
    private LocalDateTime createdAt;

    // 엔티티 → DTO 변환
    public static UserResponse from(User user) {
        return UserResponse.builder()
                .id(user.getId())
                .name(user.getName())
                .email(user.getEmail())
                .createdAt(user.getCreatedAt())
                .build();
    }
}
```

---

## 일관된 API 응답 형식

응답 형식이 API마다 다르면 클라이언트가 매번 다르게 처리해야 합니다. 성공과 실패 모두 같은 구조로 응답합니다.

```java
@Getter
@Builder
public class ApiResponse<T> {
    private boolean success;
    private T data;
    private String message;

    public static <T> ApiResponse<T> ok(T data) {
        return ApiResponse.<T>builder()
                .success(true)
                .data(data)
                .build();
    }

    public static <T> ApiResponse<T> fail(String message) {
        return ApiResponse.<T>builder()
                .success(false)
                .message(message)
                .build();
    }
}
```

```java
// Controller에서 사용
@GetMapping("/{id}")
public ApiResponse<UserResponse> getUser(@PathVariable Long id) {
    return ApiResponse.ok(userService.findById(id));
}
```

```json
// 성공 응답
{
  "success": true,
  "data": {
    "id": 1,
    "name": "홍길동",
    "email": "hong@example.com"
  }
}

// 실패 응답
{
  "success": false,
  "message": "사용자를 찾을 수 없습니다."
}
```

---

> API는 팀과의 약속이자, 사용자와의 계약입니다. 한 번 공개된 API는 쉽게 바꾸기 어렵습니다. 처음에 잘 설계하는 것이 이후 수백 시간을 아낍니다.

---

## 실습

```java
// 게시글 API를 설계하고 구현해보세요.
//
// 요구사항:
// - GET  /api/posts          전체 게시글 목록 (페이징 포함)
// - GET  /api/posts/{id}     게시글 단건 조회
// - POST /api/posts          게시글 작성
// - PUT  /api/posts/{id}     게시글 수정
// - DELETE /api/posts/{id}   게시글 삭제
//
// 체크리스트:
// □ 엔티티와 DTO가 분리되어 있는가
// □ 각 엔드포인트에 적절한 HTTP 메서드와 상태 코드를 쓰는가
// □ 응답 형식이 일관성 있는가
```
