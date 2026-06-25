---
title: "2-1. 시맨틱 HTML과 문서 구조"
order: 1
tags: [html, semantic]
status: draft
author: vivace
---

# 2-1. 시맨틱 HTML과 문서 구조

HTML은 화면을 그리는 도구가 아닙니다. **문서의 구조와 의미를 정의하는 언어**입니다. 태그 하나의 선택이 검색 엔진이 이 페이지를 읽는 방식을, 스크린 리더가 시각 장애인에게 내용을 전달하는 방식을, 팀원이 코드를 이해하는 속도를 결정합니다.

---

## HTML은 마크업이다

HTML(HyperText Markup Language)의 Markup은 "표시하다"는 뜻입니다. 텍스트에 역할을 표시하는 것이 HTML의 본질입니다.

```html
<h1>제목입니다</h1>
<p>본문 문단입니다.</p>
<a href="/about">소개 페이지로 이동</a>
```

브라우저는 이 태그를 읽고 "h1은 가장 중요한 제목, p는 문단, a는 링크"라고 해석합니다. 화면에 어떻게 보이는지는 CSS가 결정하지만, 의미는 HTML이 결정합니다.

---

## 시맨틱 태그란

시맨틱(Semantic)은 "의미론적인"이라는 뜻입니다. 시맨틱 태그는 생김새가 아니라 **역할을 이름에 담은 태그**입니다.

`<div>` 와 `<article>` 은 브라우저 화면에서 똑같이 블록으로 표시됩니다. 하지만 의미가 다릅니다.

```html
<!-- 시맨틱하지 않은 코드 -->
<div class="header">
  <div class="nav">...</div>
</div>
<div class="main">
  <div class="article">...</div>
  <div class="sidebar">...</div>
</div>
<div class="footer">...</div>

<!-- 시맨틱한 코드 -->
<header>
  <nav>...</nav>
</header>
<main>
  <article>...</article>
  <aside>...</aside>
</main>
<footer>...</footer>
```

두 번째 코드는 클래스 이름을 읽지 않아도 구조가 눈에 들어옵니다. 검색 엔진도 같은 방식으로 읽습니다.

### 자주 쓰는 시맨틱 태그

| 태그 | 역할 |
|------|------|
| `<header>` | 페이지 또는 섹션의 머리말. 로고·제목·내비게이션 포함 |
| `<nav>` | 사이트 내 이동 링크 묶음 |
| `<main>` | 페이지의 핵심 콘텐츠. 페이지당 하나만 사용 |
| `<article>` | 독립적으로 의미가 있는 콘텐츠 블록 (블로그 포스트, 뉴스 기사 등) |
| `<section>` | 주제별 섹션. 제목(`<h2>`~)을 포함해야 의미가 생김 |
| `<aside>` | 본문과 간접적으로 관련된 내용 (사이드바, 주석) |
| `<footer>` | 페이지 또는 섹션의 꼬리말. 저작권, 연락처 등 |
| `<figure>` | 이미지·코드·도표 등 독립적인 콘텐츠와 그 설명 묶음 |

---

## 문서 구조의 기본 뼈대

모든 HTML 파일은 이 구조에서 시작합니다.

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>페이지 제목</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h1>서비스 이름</h1>
    <nav>
      <a href="/">홈</a>
      <a href="/about">소개</a>
    </nav>
  </header>

  <main>
    <article>
      <h2>오늘의 주제</h2>
      <p>본문 내용이 여기에 들어갑니다.</p>
    </article>
  </main>

  <footer>
    <p>© 2024 vivace</p>
  </footer>

  <script src="main.js"></script>
</body>
</html>
```

**`<head>`** — 브라우저에게 주는 정보. 화면에 보이지 않습니다. charset(문자 인코딩), viewport(모바일 대응), title, CSS 링크가 들어갑니다.

**`<body>`** — 화면에 실제로 표시되는 모든 것.

**`<script>`는 `</body>` 직전** — HTML을 다 읽은 뒤 JavaScript를 실행해야 DOM이 완성된 상태에서 접근할 수 있습니다.

---

## 제목 계층 구조

`<h1>`부터 `<h6>`까지 제목 태그는 문서의 목차를 만듭니다.

```html
<h1>Spring AI 완전 정복</h1>        <!-- 페이지 전체 제목. 하나만 -->
  <h2>1부. 개발 환경</h2>
    <h3>1-1. Git 설치</h3>
    <h3>1-2. IDE 설정</h3>
  <h2>2부. Spring Boot</h2>
    <h3>2-1. 프로젝트 생성</h3>
```

제목 계층을 건너뛰지 않습니다. `<h1>` 다음은 `<h2>`, `<h2>` 다음은 `<h3>`입니다. 스크린 리더는 이 계층을 기반으로 문서를 탐색합니다.

---

## 폼과 입력 요소

사용자 입력을 받는 UI는 모두 `<form>` 안에 담습니다.

```html
<form action="/login" method="POST">
  <label for="email">이메일</label>
  <input type="email" id="email" name="email" required>

  <label for="password">비밀번호</label>
  <input type="password" id="password" name="password" required>

  <button type="submit">로그인</button>
</form>
```

`<label>`의 `for`와 `<input>`의 `id`를 연결하면 라벨을 클릭해도 입력창이 활성화됩니다. 접근성의 기본입니다.

`type` 속성은 브라우저가 입력값을 검증하게 만듭니다. `type="email"` 이면 `@`가 없으면 제출이 안 됩니다. JavaScript 없이 유효성 검사가 됩니다.

---

> 시맨틱 HTML은 코드를 읽는 모든 것을 위한 배려입니다. 사람, 검색 엔진, 스크린 리더, 그리고 6개월 뒤의 나.

---

## 실습

```html
<!-- index.html 파일을 만들고 아래 구조를 완성해보세요 -->
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>나의 첫 페이지</title>
</head>
<body>
  <header>
    <!-- 서비스 이름과 nav를 추가하세요 -->
  </header>

  <main>
    <article>
      <!-- h2 제목과 p 본문을 추가하세요 -->
    </article>
  </main>

  <footer>
    <!-- 저작권 정보를 추가하세요 -->
  </footer>
</body>
</html>
```

브라우저에서 열어보고, 개발자 도구(F12) → Elements 탭에서 구조가 어떻게 파악되는지 확인해보세요.
