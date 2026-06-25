---
title: "2-4. ★확장 — 컴포넌트 사고와 모던 프론트엔드로의 다리"
order: 4
tags: [component, react, vue, frontend]
status: draft
author: vivace
---

# 2-4. ★확장 — 컴포넌트 사고와 모던 프론트엔드로의 다리

React, Vue, Angular. 모던 프론트엔드 프레임워크는 모두 하나의 개념 위에서 작동합니다. **컴포넌트**입니다. 이 챕터는 프레임워크를 가르치지 않습니다. 프레임워크가 왜 존재하는지, 어떤 문제를 해결하는지를 이해하는 것이 목표입니다.

---

## 왜 프레임워크가 필요한가

지금까지 배운 방식으로 할 일 목록을 만들었다고 가정합니다.

```javascript
// 항목 추가
function addTodo(text) {
  const li = document.createElement('li');
  li.textContent = text;
  li.addEventListener('click', () => li.classList.toggle('done'));
  document.getElementById('list').appendChild(li);
}

// 항목 삭제
function removeTodo(id) {
  document.getElementById(`todo-${id}`).remove();
}

// 완료 개수 업데이트
function updateCount() {
  const done = document.querySelectorAll('.done').length;
  document.getElementById('count').textContent = `완료: ${done}`;
}
```

항목이 추가될 때마다 개수를 업데이트해야 합니다. 삭제할 때도. 완료 표시를 토글할 때도. **상태가 바뀔 때마다 관련된 모든 DOM을 직접 동기화해야 합니다.** 기능이 10개, 20개가 되면 이 동기화 코드가 뒤엉킵니다.

이것이 모던 프레임워크가 해결하는 핵심 문제입니다.

---

## 컴포넌트란 무엇인가

컴포넌트는 **UI의 독립적인 단위**입니다. 구조(HTML), 스타일(CSS), 동작(JavaScript)을 하나로 묶습니다. 레고 블록처럼 조합해서 화면 전체를 만듭니다.

```
페이지
├── Header
│   ├── Logo
│   └── Navigation
├── Main
│   ├── SearchBar
│   └── TodoList
│       ├── TodoItem
│       ├── TodoItem
│       └── TodoItem
└── Footer
```

각 컴포넌트는 독립적으로 개발하고, 테스트하고, 재사용합니다. `TodoItem`을 다른 페이지에서 쓰고 싶으면 그냥 가져다 씁니다.

---

## 상태와 렌더링 — 프레임워크의 핵심 약속

프레임워크가 해결하는 핵심은 이것입니다.

> **상태(state)가 바뀌면 화면이 자동으로 업데이트된다.**

개발자는 DOM을 직접 조작하지 않습니다. 상태만 바꾸면 됩니다. 프레임워크가 변경된 부분만 찾아서 효율적으로 화면을 다시 그립니다.

```javascript
// Vanilla JS: DOM을 직접 조작
todos.push(newTodo);
document.getElementById('list').innerHTML = ''; // 다시 그리기
todos.forEach(t => /* ... 렌더링 ... */);
document.getElementById('count').textContent = todos.length;

// React (개념): 상태만 바꾸면 나머지는 React가 처리
setTodos([...todos, newTodo]);
// → React가 변경된 부분만 DOM에 반영
```

---

## Virtual DOM — 왜 빠른가

React 같은 프레임워크는 Virtual DOM이라는 개념을 씁니다. 실제 DOM을 직접 건드리기 전에, 메모리 안에서 변경 전후를 비교(diffing)합니다. 달라진 부분만 실제 DOM에 적용합니다.

```
상태 변경
  ↓
새 Virtual DOM 생성
  ↓
이전 Virtual DOM과 비교 (diffing)
  ↓
달라진 부분만 실제 DOM 업데이트 (patching)
```

DOM 조작은 느립니다. 최소한으로 줄이는 것이 성능의 핵심입니다.

---

## Vanilla JS로 컴포넌트 패턴 직접 만들어보기

프레임워크 없이도 컴포넌트 사고방식을 적용할 수 있습니다. 직접 만들어보면 프레임워크가 무엇을 대신 해주는지 명확히 보입니다.

```javascript
// 상태 중심으로 설계
let state = {
  todos: [],
  filter: 'all'  // all | active | completed
};

// 상태가 바뀔 때마다 화면을 다시 그리는 함수
function render() {
  const filtered = state.todos.filter(todo => {
    if (state.filter === 'active') return !todo.done;
    if (state.filter === 'completed') return todo.done;
    return true;
  });

  document.getElementById('list').innerHTML = filtered
    .map(todo => `
      <li class="${todo.done ? 'done' : ''}" data-id="${todo.id}">
        ${todo.text}
      </li>
    `).join('');

  document.getElementById('count').textContent =
    `총 ${state.todos.length}개, 완료 ${state.todos.filter(t => t.done).length}개`;
}

// 상태 변경 함수
function addTodo(text) {
  state.todos.push({ id: Date.now(), text, done: false });
  render();  // 상태 바꾸고 렌더링
}

function toggleTodo(id) {
  state.todos = state.todos.map(t =>
    t.id === id ? { ...t, done: !t.done } : t
  );
  render();
}
```

이 패턴의 핵심은 **상태를 직접 조작하지 않고, 변경 함수를 통해서만 바꾼다**는 것입니다. 상태가 바뀌면 항상 `render()`를 호출합니다. React가 하는 일을 우리가 수동으로 하는 것입니다.

---

## 모던 프레임워크로 가는 길

이 패턴을 이해했다면 React나 Vue를 배울 준비가 됐습니다.

| 개념 | Vanilla JS (직접 구현) | React |
|------|----------------------|-------|
| 상태 | `let state = {}` | `useState()` |
| 렌더링 | `render()` 직접 호출 | 자동 (상태 변경 감지) |
| 컴포넌트 | 함수로 HTML 문자열 반환 | JSX를 반환하는 함수 |
| 이벤트 | `addEventListener` | `onClick={handler}` |
| 상태 불변성 | `{ ...t, done: !t.done }` | 동일 (불변 업데이트) |

개념은 같습니다. React는 이 반복 작업을 추상화하고, 성능을 최적화하고, 개발 경험을 개선한 도구입니다.

---

## 어떤 프레임워크를 선택할까

| 프레임워크 | 특징 | 적합한 상황 |
|-----------|------|-------------|
| **React** | 유연성, 생태계, 취업 시장 | 대부분의 프로젝트, 팀 협업 |
| **Vue** | 학습 곡선 완만, 직관적 문법 | 빠른 프로토타입, 소규모 팀 |
| **Svelte** | 빌드 시 컴파일, 런타임 오버헤드 없음 | 성능 중심 프로젝트 |

이 책의 프론트엔드 실습은 순수 JavaScript로 진행합니다. 컴포넌트 사고방식을 익힌 뒤 React나 Vue로 자연스럽게 확장하는 것을 목표로 합니다.

---

> 프레임워크는 도구입니다. 도구를 쓰기 전에 도구가 해결하는 문제를 먼저 직접 겪어야 합니다. 그래야 도구가 보입니다.

---

## 실습

```javascript
// 미니 상태 관리 구현
// 목표: 카운터 앱을 상태 중심으로 만들기

let state = { count: 0 };

function render() {
  document.getElementById('counter').textContent = state.count;
  document.getElementById('dec-btn').disabled = state.count <= 0;
}

function increment() {
  state = { ...state, count: state.count + 1 };
  render();
}

function decrement() {
  if (state.count > 0) {
    state = { ...state, count: state.count - 1 };
    render();
  }
}

document.getElementById('inc-btn').addEventListener('click', increment);
document.getElementById('dec-btn').addEventListener('click', decrement);

render();  // 초기 렌더링
```

```html
<button id="dec-btn">-</button>
<span id="counter">0</span>
<button id="inc-btn">+</button>
```

이 코드를 만든 뒤, React로 같은 컴포넌트를 구현해보면 차이가 눈에 들어옵니다.
