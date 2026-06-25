---
title: "2-2. CSS 레이아웃(Flexbox · Grid)과 반응형"
order: 2
tags: [css, flexbox, grid, responsive]
status: draft
author: vivace
---

# 2-2. CSS 레이아웃(Flexbox · Grid)과 반응형

CSS를 처음 배우는 사람 대부분이 같은 벽에 막힙니다. 요소가 생각대로 배치되지 않는 것입니다. Flexbox와 Grid, 두 가지만 제대로 이해하면 어떤 레이아웃이든 만들 수 있습니다.

---

## CSS의 역할

HTML이 구조를 정의한다면, CSS는 그 구조가 **어떻게 보일지**를 결정합니다.

```css
/* 선택자 { 속성: 값; } */
h1 {
  color: #1a1a1a;
  font-size: 2rem;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 24px;
}
```

CSS는 캐스케이드(Cascade) 구조입니다. 같은 요소에 여러 규칙이 충돌하면 **더 구체적인 선택자**가 이깁니다. 이 원칙을 이해하면 예상치 못한 스타일 덮어쓰기를 막을 수 있습니다.

---

## 박스 모델 — 모든 요소는 상자다

모든 HTML 요소는 상자입니다. 이 상자는 네 개의 층으로 이루어집니다.

```
┌──────────────────────────────┐
│           margin             │  외부 여백 (다른 요소와의 간격)
│  ┌────────────────────────┐  │
│  │        border          │  │  테두리
│  │  ┌──────────────────┐  │  │
│  │  │     padding      │  │  │  내부 여백 (콘텐츠와 테두리 사이)
│  │  │  ┌────────────┐  │  │  │
│  │  │  │  content   │  │  │  │  실제 내용
│  │  │  └────────────┘  │  │  │
│  │  └──────────────────┘  │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

`box-sizing: border-box`를 쓰면 width가 padding과 border를 포함한 크기가 됩니다. 레이아웃 계산이 훨씬 직관적으로 됩니다. 모든 프로젝트에 기본으로 적용하는 것을 권장합니다.

```css
*, *::before, *::after {
  box-sizing: border-box;
}
```

---

## Flexbox — 한 방향 정렬

Flexbox는 **한 축(가로 또는 세로)을 기준으로 요소를 배치**합니다. 내비게이션 바, 카드 목록, 버튼 그룹처럼 일렬로 늘어서는 레이아웃에 적합합니다.

```css
.container {
  display: flex;
  flex-direction: row;        /* 가로 방향 (기본값) */
  justify-content: space-between; /* 주축(가로) 정렬 */
  align-items: center;        /* 교차축(세로) 정렬 */
  gap: 16px;                  /* 자식 요소 간격 */
}
```

### justify-content — 주축 정렬

```
flex-start   │▪▪▪            │  왼쪽 정렬
center       │    ▪▪▪        │  가운데 정렬
flex-end     │         ▪▪▪  │  오른쪽 정렬
space-between│▪    ▪    ▪   │  양 끝 붙이고 균등 간격
space-around │ ▪   ▪   ▪   │  각 요소 양쪽에 동일 간격
```

### align-items — 교차축 정렬

```
stretch      │ 높이 맞춤 (기본값) │
center       │ 세로 가운데 정렬   │
flex-start   │ 위쪽 정렬          │
flex-end     │ 아래쪽 정렬        │
```

### 실전 예: 내비게이션 바

```html
<nav class="navbar">
  <span class="logo">MyApp</span>
  <ul class="menu">
    <li><a href="/">홈</a></li>
    <li><a href="/about">소개</a></li>
  </ul>
</nav>
```

```css
.navbar {
  display: flex;
  justify-content: space-between;  /* 로고는 왼쪽, 메뉴는 오른쪽 */
  align-items: center;
  padding: 0 24px;
  height: 60px;
}

.menu {
  display: flex;
  list-style: none;
  gap: 24px;
}
```

---

## Grid — 두 방향 배치

Grid는 **가로와 세로 격자를 동시에 제어**합니다. 전체 페이지 레이아웃, 대시보드, 이미지 갤러리처럼 행과 열이 모두 필요한 구조에 적합합니다.

```css
.grid-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);  /* 동일한 너비 3열 */
  gap: 16px;
}
```

`1fr`은 "사용 가능한 공간을 비율로 나눠가져라"는 단위입니다. `repeat(3, 1fr)`은 3등분입니다.

### 실전 예: 반응형 카드 그리드

```css
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}
```

`auto-fill`과 `minmax`의 조합은 반응형을 자동으로 처리합니다. 카드 하나의 최소 너비가 280px이고, 공간이 남으면 늘어나며, 공간이 좁아지면 자동으로 줄이 바뀝니다. 미디어 쿼리 없이도 반응형이 됩니다.

### 실전 예: 페이지 전체 레이아웃

```css
.page-layout {
  display: grid;
  grid-template-areas:
    "header  header"
    "sidebar main"
    "footer  footer";
  grid-template-columns: 240px 1fr;
  grid-template-rows: 60px 1fr 40px;
  min-height: 100vh;
}

header   { grid-area: header; }
.sidebar { grid-area: sidebar; }
main     { grid-area: main; }
footer   { grid-area: footer; }
```

`grid-template-areas`를 쓰면 레이아웃 구조가 CSS 코드 자체로 시각화됩니다.

---

## 반응형 디자인

스마트폰, 태블릿, 데스크톱. 화면 크기는 다양합니다. **하나의 코드로 모든 화면에 적응하는 UI**를 만드는 것이 반응형 디자인입니다.

### 미디어 쿼리

화면 너비에 따라 다른 CSS를 적용합니다.

```css
/* 기본: 모바일 (320px~) */
.card-grid {
  grid-template-columns: 1fr;
}

/* 태블릿 (768px 이상) */
@media (min-width: 768px) {
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 데스크톱 (1024px 이상) */
@media (min-width: 1024px) {
  .card-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

**모바일 퍼스트(Mobile First)**: 가장 작은 화면을 기본으로 작성하고, 넓어질수록 확장합니다. 성능과 유지보수 모두 유리합니다.

### 반응형 단위

| 단위 | 기준 | 사용처 |
|------|------|--------|
| `px` | 절대값 | 테두리, 아이콘 크기 등 고정값 |
| `rem` | 루트 폰트 크기 (기본 16px) | 폰트 크기, 간격 |
| `%` | 부모 요소 크기 | 너비, 높이 |
| `vw` / `vh` | 뷰포트 너비 / 높이 | 전체 화면 레이아웃 |
| `fr` | Grid의 비율 단위 | Grid 열/행 크기 |

---

## Flexbox vs Grid

두 가지를 상황에 따라 함께 씁니다.

| 상황 | 선택 |
|------|------|
| 내비게이션 바, 버튼 그룹 | Flexbox |
| 페이지 전체 레이아웃 | Grid |
| 반응형 카드 목록 | Grid (`auto-fill`) |
| 아이콘과 텍스트를 나란히 | Flexbox |
| 복잡한 대시보드 | Grid (부모) + Flexbox (자식) |

---

> 레이아웃이 안 맞으면 먼저 박스 모델을 의심하세요. 그다음 Flex와 Grid의 축 방향을 확인하세요. 원인은 항상 이 안에 있습니다.

---

## 실습

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>레이아웃 실습</title>
  <style>
    /* 1. 전체 초기화 */
    *, *::before, *::after { box-sizing: border-box; }
    body { margin: 0; font-family: sans-serif; }

    /* 2. Flexbox 내비게이션 구현해보세요 */
    .navbar { /* ... */ }

    /* 3. Grid 카드 레이아웃 구현해보세요 */
    .card-grid { /* ... */ }

    /* 4. 모바일에서 카드가 1열이 되도록 미디어 쿼리 추가 */
  </style>
</head>
<body>
  <nav class="navbar">
    <span>Logo</span>
    <ul>
      <li><a href="#">홈</a></li>
      <li><a href="#">소개</a></li>
      <li><a href="#">연락처</a></li>
    </ul>
  </nav>

  <div class="card-grid">
    <div class="card">카드 1</div>
    <div class="card">카드 2</div>
    <div class="card">카드 3</div>
  </div>
</body>
</html>
```

브라우저 너비를 줄여보면서 반응형이 동작하는지 확인해보세요.
