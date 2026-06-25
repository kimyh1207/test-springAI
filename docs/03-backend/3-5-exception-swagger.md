---
title: "3-5. 예외 처리 · 검증 · API 문서화(Swagger)"
order: 5
tags: [spring-boot, exception, swagger, validation]
status: draft
author: vivace
---

# 3-5. 예외 처리 · 검증 · API 문서화(Swagger)

오류도 API의 일부입니다. 성공 응답만 잘 만들어도 부족합니다. 잘못된 요청에 명확한 오류 메시지를 돌려주고, 그 모든 API를 문서화해야 진짜 쓸 수 있는 백엔드입니다.

---

## 입력값 검증 — Validation

사용자 입력은 항상 검증해야 합니다. Controller에서 `@Valid`를 붙이면 DTO의 검증 애너테이션이 자동으로 실행됩니다.

```java
@Getter
@NoArgsConstructor
public class UserCreateRequest {

    @NotBlank(message = "이름은 필수입니다.")
    @Size(max = 50, message = "이름은 50자 이하여야 합니다.")
    private String name;

    @NotBlank(message = "이메일은 필수입니다.")
    @Email(message = "올바른 이메일 형식이 아닙니다.")
    private String email;

    @NotBlank(message = "비밀번호는 필수입니다.")
    @Size(min = 8, max = 20, message = "비밀번호는 8~20자여야 합니다.")
    private String password;

    @Min(value = 0, message = "나이는 0 이상이어야 합니다.")
    @Max(value = 150, message = "올바른 나이를 입력하세요.")
    private int age;
}
```

```java
@PostMapping
public ApiResponse<UserResponse> createUser(
        @RequestBody @Valid UserCreateRequest request) {
    return ApiResponse.ok(userService.create(request));
}
```

검증 실패 시 Spring이 자동으로 `MethodArgumentNotValidException`을 던집니다.

### 자주 쓰는 검증 애너테이션

| 애너테이션 | 설명 |
|-----------|------|
| `@NotNull` | null 불가 |
| `@NotBlank` | null, 빈 문자열, 공백만 있는 문자열 불가 |
| `@NotEmpty` | null, 빈 문자열 불가 |
| `@Size(min, max)` | 문자열 길이 범위 |
| `@Min` / `@Max` | 숫자 최솟값 / 최댓값 |
| `@Email` | 이메일 형식 |
| `@Pattern(regexp)` | 정규식 패턴 |
| `@Positive` | 양수 |

---

## 전역 예외 처리 — @ControllerAdvice

예외를 각 Controller마다 처리하면 중복 코드가 생깁니다. `@ControllerAdvice`로 한 곳에서 모든 예외를 처리합니다.

```java
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    // 입력값 검증 실패
    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ApiResponse<Void> handleValidationException(MethodArgumentNotValidException e) {
        String message = e.getBindingResult()
                .getFieldErrors()
                .stream()
                .map(error -> error.getField() + ": " + error.getDefaultMessage())
                .collect(Collectors.joining(", "));
        return ApiResponse.fail(message);
    }

    // 리소스 없음
    @ExceptionHandler(EntityNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ApiResponse<Void> handleEntityNotFoundException(EntityNotFoundException e) {
        return ApiResponse.fail(e.getMessage());
    }

    // 비즈니스 로직 예외
    @ExceptionHandler(BusinessException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ApiResponse<Void> handleBusinessException(BusinessException e) {
        return ApiResponse.fail(e.getMessage());
    }

    // 예상치 못한 서버 오류
    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public ApiResponse<Void> handleException(Exception e) {
        log.error("Unexpected error", e);
        return ApiResponse.fail("서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
    }
}
```

### 커스텀 예외 클래스

```java
// 비즈니스 예외의 부모 클래스
public class BusinessException extends RuntimeException {
    public BusinessException(String message) {
        super(message);
    }
}

// 구체적인 예외
public class StockInsufficientException extends BusinessException {
    public StockInsufficientException(Long productId) {
        super("재고가 부족합니다. productId=" + productId);
    }
}

public class DuplicateEmailException extends BusinessException {
    public DuplicateEmailException(String email) {
        super("이미 사용 중인 이메일입니다: " + email);
    }
}
```

```java
// Service에서 사용
public UserResponse create(UserCreateRequest request) {
    if (userRepository.existsByEmail(request.getEmail())) {
        throw new DuplicateEmailException(request.getEmail());
    }
    // ...
}
```

예외 클래스가 세분화되면 GlobalExceptionHandler에서 다르게 처리할 수 있습니다.

---

## API 문서화 — Swagger(SpringDoc)

Swagger는 API 명세를 자동으로 생성하고 웹 UI로 제공합니다. 프론트엔드 개발자와 협업할 때 필수입니다.

### 의존성 추가

```groovy
implementation 'org.springdoc:springdoc-openapi-starter-webmvc-ui:2.2.0'
```

의존성 추가만 하면 `http://localhost:8080/swagger-ui.html`에서 자동 생성된 문서를 볼 수 있습니다.

### 문서 상세 설정

```java
@RestController
@RequestMapping("/api/users")
@Tag(name = "User", description = "사용자 관리 API")
public class UserController {

    @GetMapping("/{id}")
    @Operation(
        summary = "사용자 단건 조회",
        description = "ID로 사용자 정보를 조회합니다."
    )
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "조회 성공"),
        @ApiResponse(responseCode = "404", description = "사용자 없음")
    })
    public ApiResponse<UserResponse> getUser(
            @Parameter(description = "사용자 ID") @PathVariable Long id) {
        return ApiResponse.ok(userService.findById(id));
    }
}
```

Swagger UI에서 API를 직접 실행해볼 수도 있어 프론트엔드와 백엔드가 동시에 개발할 때 실시간으로 맞춰볼 수 있습니다.

---

> 오류 메시지는 사용자(그리고 프론트엔드 개발자)에게 보내는 편지입니다. "오류가 발생했습니다"는 아무것도 알려주지 않습니다. "이메일 형식이 올바르지 않습니다"는 무엇을 고쳐야 할지 알려줍니다.

---

## 실습

```java
// 1. UserCreateRequest에 검증 애너테이션 추가
//    - name: 2~20자, 공백 불가
//    - email: 이메일 형식
//    - password: 8~20자, 공백 불가

// 2. GlobalExceptionHandler 작성
//    - 검증 실패 → 400, 필드명과 오류 메시지 반환
//    - 리소스 없음 → 404, 메시지 반환
//    - 기타 예외 → 500, 일반 메시지 반환

// 3. Swagger 의존성 추가 후
//    http://localhost:8080/swagger-ui.html 접속
//    → API 목록 확인 및 직접 실행해보기
```
