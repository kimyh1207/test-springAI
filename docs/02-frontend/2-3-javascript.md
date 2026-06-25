---
title: "2-3. JavaScript 핵심: DOM, 이벤트, 비동기(fetch/async)"
order: 3
tags: [javascript, dom, async]
status: draft
author: vivace
---

# 2-3. JavaScript 핵심: DOM · 이벤트 · 비동기

HTML이 뼈대, CSS가 옷이라면 JavaScript는 행동입니다. 버튼을 클릭했을 때 무언가 일어나게 하고, 서버에서 데이터를 받아 화면에 표시하는 것, 모두 JavaScript가 합니다.

---

## DOM — 문서를 프로그램으로 다루는 방법

브라우저는 HTML을 읽고 **DOM(Document Object Model)** 이라는 트리 구조로 변환합니다. JavaScript는 이 DOM을 통해 HTML 요소를 읽고, 수정하고, 추가하고, 삭제합니다.

```html
<div id="result">
  <p class="message">결과가 여기 나타납니다.</p>
</div>
```

```javascript
// 요소 선택
const result = document.getElementById('result');
const message = document.querySelector('.message');  // CSS 선택자 사용

// 내용 변경
message.textContent = '데이터를 불러왔습니다.';

// 스타일 변경
result.style.backgroundColor = '#f0f9ff';

// 클래스 추가/제거
result.classList.add('active');
result.classList.remove('hidden');
result.classList.toggle('expanded');  // 있으면 제거, 없으면 추가

// 새 요소 생성 및 추가
const newItem = document.createElement('li');
newItem.textContent = '새 항목';
document.querySelector('ul').appendChild(newItem);
```

`querySelector`는 CSS 선택자 문법을 그대로 씁니다. `#id`, `.class`, `태그명`, 조합 모두 가능합니다. 실무에서 가장 많이 쓰는 DOM 접근 방법입니다.

---

## 이벤트 — 사용자 행동에 반응하기

이벤트는 사용자가 무언가를 했을 때 발생하는 신호입니다. JavaScript는 이 신호를 듣고 원하는 동작을 실행합니다.

```javascript
const button = document.querySelector('#submit-btn');

button.addEventListener('click', function(event) {
  event.preventDefault();  // 기본 동작(폼 제출 등) 막기
  console.log('버튼이 클릭됐습니다.');
});
```

### 자주 쓰는 이벤트

| 이벤트 | 발생 시점 |
|--------|-----------|
| `click` | 클릭 |
| `submit` | 폼 제출 |
| `input` | 입력값 변경 (실시간) |
| `change` | 입력 완료 후 포커스 이동 |
| `keydown` / `keyup` | 키 누름 / 뗌 |
| `mouseover` / `mouseout` | 마우스 진입 / 이탈 |
| `DOMContentLoaded` | HTML 파싱 완료 |

### 실전 예: 실시간 입력 검증

```javascript
const emailInput = document.querySelector('#email');
const errorMsg = document.querySelector('#email-error');

emailInput.addEventListener('input', function() {
  const value = emailInput.value;
  if (!value.includes('@')) {
    errorMsg.textContent = '올바른 이메일 형식이 아닙니다.';
    errorMsg.style.display = 'block';
  } else {
    errorMsg.style.display = 'none';
  }
});
```

---

## 비동기 — 기다리면서도 멈추지 않기

JavaScript는 기본적으로 한 번에 하나의 작업을 처리합니다. 서버에 데이터를 요청하고 기다리는 동안 화면이 굳어버리면 사용자 경험이 끔찍해집니다. 비동기 처리는 이 문제를 해결합니다.

### fetch — 서버에 HTTP 요청 보내기

```javascript
fetch('https://api.example.com/posts')
  .then(response => response.json())
  .then(data => {
    console.log(data);
  })
  .catch(error => {
    console.error('오류 발생:', error);
  });
```

`fetch`는 Promise를 반환합니다. `.then()`은 요청이 완료됐을 때, `.catch()`는 오류가 발생했을 때 실행됩니다.

### async/await — 더 읽기 쉬운 비동기 코드

Promise 체인이 길어지면 읽기 어렵습니다. `async/await`는 비동기 코드를 동기 코드처럼 쓸 수 있게 합니다.

```javascript
// fetch + .then 방식
fetch('/api/users')
  .then(res => res.json())
  .then(users => {
    users.forEach(user => console.log(user.name));
  });

// async/await 방식 (같은 동작, 더 읽기 쉬움)
async function loadUsers() {
  try {
    const response = await fetch('/api/users');
    const users = await response.json();
    users.forEach(user => console.log(user.name));
  } catch (error) {
    console.error('사용자 목록을 불러오지 못했습니다:', error);
  }
}

loadUsers();
```

`await`는 `async` 함수 안에서만 쓸 수 있습니다. `try/catch`로 오류를 처리합니다.

---

## 실전: API 응답을 화면에 렌더링

지금까지 배운 DOM, 이벤트, 비동기를 모두 합칩니다. 버튼을 누르면 API에서 할 일 목록을 가져와 화면에 표시합니다.

```html
<button id="load-btn">할 일 목록 불러오기</button>
<ul id="todo-list"></ul>
```

```javascript
document.getElementById('load-btn').addEventListener('click', async () => {
  const list = document.getElementById('todo-list');
  list.innerHTML = '<li>불러오는 중...</li>';

  try {
    const response = await fetch('https://jsonplaceholder.typicode.com/todos?_limit=5');
    const todos = await response.json();

    list.innerHTML = '';  // 기존 내용 지우기
    todos.forEach(todo => {
      const li = document.createElement('li');
      li.textContent = todo.title;
      li.style.textDecoration = todo.completed ? 'line-through' : 'none';
      list.appendChild(li);
    });
  } catch {
    list.innerHTML = '<li>불러오기 실패. 다시 시도해주세요.</li>';
  }
});
```

이 패턴이 모든 웹 서비스의 기본입니다. 버튼 클릭 → API 요청 → 응답 파싱 → DOM 업데이트.

---

## ES6+ 필수 문법

현대 JavaScript는 ES6(2015) 이후 크게 달라졌습니다. 실무에서 반드시 쓰는 문법만 정리합니다.

```javascript
// 화살표 함수
const add = (a, b) => a + b;

// 구조 분해 할당
const { name, age } = user;
const [first, ...rest] = array;

// 템플릿 리터럴
const greeting = `안녕하세요, ${name}님!`;

// 스프레드 연산자
const newArray = [...existing, newItem];
const newObj = { ...defaults, ...overrides };

// 옵셔널 체이닝 (null 안전 접근)
const city = user?.address?.city;  // user나 address가 없어도 에러 없음

// Nullish 병합 연산자
const displayName = user.name ?? '익명';  // null/undefined일 때만 기본값 사용
```

---

> JavaScript는 배울수록 깊어지는 언어입니다. 하지만 DOM, 이벤트, 비동기 이 세 가지만 익혀도 실제 웹 서비스의 프론트엔드를 읽고 수정할 수 있습니다.

---

## 실습

`jsonplaceholder.typicode.com`은 테스트용 무료 API입니다. 아래 요청을 직접 실행해보세요.

```javascript
// 브라우저 콘솔에서 실행 (F12 → Console)

// 1. 게시글 목록 가져오기
const posts = await fetch('https://jsonplaceholder.typicode.com/posts?_limit=3')
  .then(r => r.json());
console.log(posts);

// 2. 사용자 정보 가져오기
const user = await fetch('https://jsonplaceholder.typicode.com/users/1')
  .then(r => r.json());
console.log(`이름: ${user.name}, 이메일: ${user.email}`);

// 3. 응답 데이터를 직접 DOM에 렌더링해보세요
//    빈 <ul id="list"></ul>을 HTML에 만들고
//    posts의 title을 <li>로 추가하는 코드를 작성해보세요
```
