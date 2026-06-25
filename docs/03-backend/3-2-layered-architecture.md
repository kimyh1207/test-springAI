---
title: "3-2. 계층형 아키텍처(Controller · Service · Repository)"
order: 2
tags: [spring-boot, architecture, mvc]
status: draft
author: vivace
---

# 3-2. 계층형 아키텍처(Controller · Service · Repository)

코드가 커지면 모든 것이 한 파일에 뒤섞이기 시작합니다. HTTP 요청 처리, 비즈니스 규칙, 데이터베이스 접근이 한곳에 있으면 고치기 어렵고, 테스트하기 어렵고, 팀원이 이해하기 어렵습니다. 계층형 아키텍처는 역할을 나눠 이 문제를 해결합니다.

---

## 왜 계층을 나누는가

역할이 분리되면 세 가지가 달라집니다.

- **변경의 범위가 좁아집니다.** DB를 바꿔도 Controller는 건드리지 않아도 됩니다.
- **테스트가 쉬워집니다.** Service 로직만 따로 테스트할 수 있습니다.
- **팀이 분업할 수 있습니다.** API 담당과 DB 담당이 충돌 없이 작업합니다.

---

## 세 계층의 역할

```
HTTP 요청
    ↓
Controller   ← 요청을 받고, 응답을 돌려줌. 비즈니스 로직 없음
    ↓
Service      ← 비즈니스 규칙 처리. DB를 직접 모름
    ↓
Repository   ← DB 접근만 담당. SQL/JPA 쿼리가 여기 있음
    ↓
Database
```

**Controller** — "무엇을 요청받았는가"를 처리합니다. URL 매핑, 요청 파라미터 추출, 응답 형식 결정. 비즈니스 로직이 들어가면 안 됩니다.

**Service** — "어떻게 처리할 것인가"를 결정합니다. 비즈니스 규칙, 트랜잭션, 여러 Repository를 조합하는 로직이 여기 있습니다.

**Repository** — "데이터를 어떻게 저장/조회할 것인가"만 담당합니다. Spring Data JPA를 사용하면 인터페이스 선언만으로 대부분 구현됩니다.

---

## Controller

```java
@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    // GET /api/users
    @GetMapping
    public List<UserResponse> getUsers() {
        return userService.findAll();
    }

    // GET /api/users/1
    @GetMapping("/{id}")
    public UserResponse getUser(@PathVariable Long id) {
        return userService.findById(id);
    }

    // POST /api/users
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public UserResponse createUser(@RequestBody @Valid UserCreateRequest request) {
        return userService.create(request);
    }

    // DELETE /api/users/1
    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteUser(@PathVariable Long id) {
        userService.delete(id);
    }
}
```

`@RestController` = `@Controller` + `@ResponseBody`. 반환값이 자동으로 JSON으로 변환됩니다.

`@RequiredArgsConstructor`는 Lombok이 `final` 필드로 생성자를 만들어줍니다. Spring이 이 생성자로 의존성을 주입합니다(생성자 주입 방식).

---

## Service

```java
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class UserService {

    private final UserRepository userRepository;

    public List<UserResponse> findAll() {
        return userRepository.findAll()
                .stream()
                .map(UserResponse::from)
                .toList();
    }

    public UserResponse findById(Long id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("사용자를 찾을 수 없습니다. id=" + id));
        return UserResponse.from(user);
    }

    @Transactional
    public UserResponse create(UserCreateRequest request) {
        User user = User.builder()
                .name(request.getName())
                .email(request.getEmail())
                .build();
        return UserResponse.from(userRepository.save(user));
    }

    @Transactional
    public void delete(Long id) {
        userRepository.deleteById(id);
    }
}
```

`@Transactional(readOnly = true)`를 클래스에 걸고, 쓰기 작업에만 `@Transactional`을 추가합니다. 읽기 전용 트랜잭션은 성능 최적화가 적용됩니다.

---

## Repository

```java
@Repository
public interface UserRepository extends JpaRepository<User, Long> {

    // 메서드 이름만으로 쿼리 자동 생성
    Optional<User> findByEmail(String email);

    List<User> findByNameContaining(String keyword);

    boolean existsByEmail(String email);
}
```

`JpaRepository<엔티티, ID타입>`을 상속하면 기본 CRUD가 모두 제공됩니다.

| 제공되는 메서드 | 역할 |
|---------------|------|
| `save(entity)` | 저장 / 수정 |
| `findById(id)` | ID로 단건 조회 |
| `findAll()` | 전체 조회 |
| `deleteById(id)` | 삭제 |
| `count()` | 개수 조회 |
| `existsById(id)` | 존재 여부 확인 |

메서드 이름 규칙(`findBy`, `existsBy`, `deleteBy`)에 맞게 선언하면 Spring Data JPA가 자동으로 SQL을 만들어줍니다.

---

## 의존성 주입 — Spring의 핵심

Spring은 객체를 직접 생성하지 않습니다. Spring이 관리하는 객체(Bean)를 필요한 곳에 **주입**합니다.

```java
// 하지 말 것 — 직접 생성
public class UserController {
    private UserService userService = new UserService(); // 테스트 불가, 결합도 높음
}

// 권장 — 생성자 주입
public class UserController {
    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }
}
```

생성자 주입을 권장하는 이유는 두 가지입니다. 테스트할 때 Mock 객체로 교체하기 쉽고, `final`로 선언해 불변성을 보장할 수 있습니다.

`@RequiredArgsConstructor`를 쓰면 이 생성자 코드를 Lombok이 자동 생성합니다.

---

> 계층을 나누는 것은 규칙이 아닙니다. "이 코드가 바뀌면 어디까지 영향이 가는가"라는 질문에 답하는 방법입니다.

---

## 실습

```java
// Todo 항목을 관리하는 간단한 API를 계층형으로 만들어보세요.
// 1. TodoController: GET /api/todos, POST /api/todos, DELETE /api/todos/{id}
// 2. TodoService: 비즈니스 로직 (완료된 항목 필터링 등)
// 3. TodoRepository: JpaRepository 상속
// 4. Todo 엔티티: id, content, completed 필드

// 목표: 각 계층이 서로를 얼마나 모르는 상태로 만들 수 있는지 확인
```
