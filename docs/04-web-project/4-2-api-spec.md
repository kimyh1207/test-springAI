---
title: "4-2. API 명세 설계와 프론트–백 연동"
order: 2
tags: [api, frontend, backend]
status: draft
author: vivace
---

# 4-2. API 명세 설계와 프론트–백 연동

프론트엔드와 백엔드가 함께 개발할 때 가장 흔한 문제는 "기다림"입니다. 백엔드 API가 완성되어야 프론트엔드가 연동할 수 있다는 생각 때문입니다. **API 명세를 먼저 합의하면 동시에 개발할 수 있습니다.**

---

## API 명세 설계

요구사항을 API로 변환합니다. 각 기능이 어떤 URL, 어떤 메서드, 어떤 요청/응답을 갖는지 정의합니다.

### 인증 API

| 메서드 | URL | 설명 |
|--------|-----|------|
| POST | `/api/auth/signup` | 회원가입 |
| POST | `/api/auth/login` | 로그인 |

**POST /api/auth/signup**

요청:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

응답 (201):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "createdAt": "2024-03-01T10:00:00"
  }
}
```

오류 응답 (400 — 이메일 중복):
```json
{
  "success": false,
  "message": "이미 사용 중인 이메일입니다."
}
```

**POST /api/auth/login**

요청:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

응답 (200):
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiJ9...",
    "tokenType": "Bearer"
  }
}
```

---

### 할 일 API

모든 할 일 API는 `Authorization: Bearer {토큰}` 헤더 필수.

| 메서드 | URL | 설명 |
|--------|-----|------|
| GET | `/api/todos` | 내 할 일 목록 조회 |
| POST | `/api/todos` | 할 일 추가 |
| PATCH | `/api/todos/{id}/toggle` | 완료 상태 토글 |
| PUT | `/api/todos/{id}` | 할 일 내용 수정 |
| DELETE | `/api/todos/{id}` | 할 일 삭제 |

**GET /api/todos**

쿼리 파라미터: `?filter=all|active|completed` (기본값: all)

응답 (200):
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "content": "Spring Boot 공부하기",
      "completed": false,
      "createdAt": "2024-03-01T10:00:00"
    },
    {
      "id": 2,
      "content": "Git 커밋 전략 읽기",
      "completed": true,
      "createdAt": "2024-03-01T09:00:00"
    }
  ]
}
```

---

## 백엔드 구현

명세에 맞춰 컨트롤러와 서비스를 구현합니다.

```java
@RestController
@RequestMapping("/api/todos")
@RequiredArgsConstructor
public class TodoController {

    private final TodoService todoService;

    @GetMapping
    public ApiResponse<List<TodoResponse>> getTodos(
            @RequestParam(defaultValue = "all") String filter,
            @AuthenticationPrincipal UserDetails userDetails) {
        Long userId = Long.parseLong(userDetails.getUsername());
        return ApiResponse.ok(todoService.findAll(userId, filter));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<TodoResponse> createTodo(
            @RequestBody @Valid TodoCreateRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        Long userId = Long.parseLong(userDetails.getUsername());
        return ApiResponse.ok(todoService.create(userId, request));
    }

    @PatchMapping("/{id}/toggle")
    public ApiResponse<TodoResponse> toggleTodo(
            @PathVariable Long id,
            @AuthenticationPrincipal UserDetails userDetails) {
        Long userId = Long.parseLong(userDetails.getUsername());
        return ApiResponse.ok(todoService.toggle(userId, id));
    }

    @PutMapping("/{id}")
    public ApiResponse<TodoResponse> updateTodo(
            @PathVariable Long id,
            @RequestBody @Valid TodoUpdateRequest request,
            @AuthenticationPrincipal UserDetails userDetails) {
        Long userId = Long.parseLong(userDetails.getUsername());
        return ApiResponse.ok(todoService.update(userId, id, request));
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteTodo(
            @PathVariable Long id,
            @AuthenticationPrincipal UserDetails userDetails) {
        Long userId = Long.parseLong(userDetails.getUsername());
        todoService.delete(userId, id);
    }
}
```

```java
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class TodoService {

    private final TodoRepository todoRepository;
    private final UserRepository userRepository;

    public List<TodoResponse> findAll(Long userId, String filter) {
        List<Todo> todos = switch (filter) {
            case "active"    -> todoRepository.findByUserIdAndCompleted(userId, false);
            case "completed" -> todoRepository.findByUserIdAndCompleted(userId, true);
            default          -> todoRepository.findByUserIdOrderByCreatedAtDesc(userId);
        };
        return todos.stream().map(TodoResponse::from).toList();
    }

    @Transactional
    public TodoResponse create(Long userId, TodoCreateRequest request) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new EntityNotFoundException("사용자 없음"));
        Todo todo = Todo.builder()
                .content(request.getContent())
                .user(user)
                .build();
        return TodoResponse.from(todoRepository.save(todo));
    }

    @Transactional
    public TodoResponse toggle(Long userId, Long todoId) {
        Todo todo = findTodoByIdAndUserId(todoId, userId);
        todo.toggleCompleted();
        return TodoResponse.from(todo);
    }

    @Transactional
    public TodoResponse update(Long userId, Long todoId, TodoUpdateRequest request) {
        Todo todo = findTodoByIdAndUserId(todoId, userId);
        todo.updateContent(request.getContent());
        return TodoResponse.from(todo);
    }

    @Transactional
    public void delete(Long userId, Long todoId) {
        Todo todo = findTodoByIdAndUserId(todoId, userId);
        todoRepository.delete(todo);
    }

    private Todo findTodoByIdAndUserId(Long todoId, Long userId) {
        return todoRepository.findByIdAndUserId(todoId, userId)
                .orElseThrow(() -> new EntityNotFoundException("할 일을 찾을 수 없습니다."));
    }
}
```

---

## 프론트엔드 연동

백엔드 API가 완성되지 않아도, 명세만 있으면 프론트엔드 개발을 시작할 수 있습니다.

```javascript
// api.js — API 호출 모듈
const BASE_URL = 'http://localhost:8080';

function getAuthHeader() {
  const token = localStorage.getItem('accessToken');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function request(method, path, body = null) {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader()
    }
  };
  if (body) options.body = JSON.stringify(body);

  const response = await fetch(`${BASE_URL}${path}`, options);
  return response.json();
}

// 인증
export const auth = {
  login:  (email, password) => request('POST', '/api/auth/login', { email, password }),
  signup: (email, password) => request('POST', '/api/auth/signup', { email, password }),
};

// 할 일
export const todos = {
  getAll:  (filter = 'all') => request('GET', `/api/todos?filter=${filter}`),
  create:  (content)        => request('POST', '/api/todos', { content }),
  toggle:  (id)             => request('PATCH', `/api/todos/${id}/toggle`),
  update:  (id, content)    => request('PUT', `/api/todos/${id}`, { content }),
  remove:  (id)             => request('DELETE', `/api/todos/${id}`),
};
```

```javascript
// app.js — 화면 렌더링
import { auth, todos } from './api.js';

let state = {
  todos: [],
  filter: 'all'
};

async function loadTodos() {
  const res = await todos.getAll(state.filter);
  if (res.success) {
    state.todos = res.data;
    render();
  }
}

async function handleAddTodo(content) {
  const res = await todos.create(content);
  if (res.success) await loadTodos();
}

async function handleToggle(id) {
  const res = await todos.toggle(id);
  if (res.success) await loadTodos();
}

function render() {
  const list = document.getElementById('todo-list');
  list.innerHTML = state.todos
    .map(todo => `
      <li class="${todo.completed ? 'done' : ''}">
        <span onclick="handleToggle(${todo.id})">${todo.content}</span>
        <button onclick="handleDelete(${todo.id})">삭제</button>
      </li>
    `).join('');
}
```

---

## CORS 설정

프론트엔드(localhost:3000)와 백엔드(localhost:8080)가 다른 포트에서 실행되면 브라우저가 보안 정책으로 요청을 차단합니다. 백엔드에서 CORS를 허용해야 합니다.

```java
@Configuration
public class CorsConfig {

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(List.of("http://localhost:3000", "http://localhost:5500"));
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        config.setAllowedHeaders(List.of("*"));
        config.setAllowCredentials(true);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);
        return source;
    }
}
```

---

> API 명세는 프론트와 백의 계약서입니다. 계약서 없이 만나면 서로 다른 것을 만들었다는 걸 연동할 때 발견합니다.

---

## 실습

```
1. 백엔드를 먼저 구현하고 Swagger UI에서 API를 직접 테스트해보세요.
   http://localhost:8080/swagger-ui.html

2. HTML + JavaScript로 프론트엔드를 구현하고 백엔드와 연동해보세요.
   - 로그인 → 토큰 localStorage 저장
   - 할 일 목록 불러오기
   - 할 일 추가 / 완료 토글 / 삭제

3. 개발자 도구 → Network 탭에서 실제 HTTP 요청/응답을 확인해보세요.
```
