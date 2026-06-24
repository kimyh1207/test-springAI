---
title: "4-1. 요구사항 분석과 도메인 모델링"
order: 1
tags: [requirements, domain-modeling]
status: draft
author: vivace
---

# 4-1. 요구사항 분석과 도메인 모델링

코드보다 먼저 해야 할 것이 있습니다. 무엇을 만들지 명확히 하는 것입니다. 요구사항이 흐릿한 채로 코딩을 시작하면 방향을 잃습니다. 방향을 잃으면 다시 만들어야 합니다.

---

## 미니 프로젝트: 할 일 관리 서비스 (TodoList)

배우기에 적당한 규모이면서 실제로 써볼 수 있는 주제를 선택합니다. 이 챕터의 프로젝트는 **할 일 관리 서비스**입니다.

단순해 보이지만 실무 서비스의 필수 요소가 모두 들어 있습니다. 사용자 인증, CRUD, 상태 관리, 프론트–백 연동.

---

## 요구사항 정의

요구사항은 **사용자 스토리** 형식으로 씁니다. "사용자로서, 나는 ~을 할 수 있다."

### 인증
- 사용자로서, 나는 이메일과 비밀번호로 회원가입할 수 있다.
- 사용자로서, 나는 로그인하여 JWT 토큰을 발급받을 수 있다.
- 사용자로서, 나는 로그아웃할 수 있다.

### 할 일 관리
- 사용자로서, 나는 할 일을 추가할 수 있다.
- 사용자로서, 나는 내 할 일 목록을 조회할 수 있다.
- 사용자로서, 나는 할 일의 완료 여부를 토글할 수 있다.
- 사용자로서, 나는 할 일의 내용을 수정할 수 있다.
- 사용자로서, 나는 할 일을 삭제할 수 있다.
- 사용자로서, 나는 완료된 할 일만 보거나 미완료 할 일만 볼 수 있다.

### 제약 조건
- 내 할 일은 나만 볼 수 있다. 다른 사용자의 할 일에 접근할 수 없다.
- 로그인하지 않으면 할 일 API에 접근할 수 없다.

---

## 도메인 모델링

도메인 모델은 서비스의 핵심 개념과 그 관계를 표현합니다. 코드 작성 전에 개념 구조를 정리합니다.

### 엔티티 식별

```
User (사용자)
  - 회원가입, 로그인을 하는 주체

Todo (할 일)
  - 사용자가 관리하는 핵심 데이터
  - 항상 특정 사용자에게 속함
```

### 관계 정의

```
User (1) ──────── (N) Todo

한 명의 사용자는 여러 개의 할 일을 가질 수 있다.
하나의 할 일은 반드시 한 명의 사용자에게 속한다.
```

### 엔티티 상세

**User**
| 필드 | 타입 | 제약 |
|------|------|------|
| id | Long | PK, 자동 생성 |
| email | String | NOT NULL, UNIQUE |
| password | String | NOT NULL (암호화 저장) |
| createdAt | LocalDateTime | 자동 기록 |

**Todo**
| 필드 | 타입 | 제약 |
|------|------|------|
| id | Long | PK, 자동 생성 |
| content | String | NOT NULL, 최대 500자 |
| completed | Boolean | NOT NULL, 기본값 false |
| user | User | FK (users.id) |
| createdAt | LocalDateTime | 자동 기록 |
| updatedAt | LocalDateTime | 자동 기록 |

---

## 엔티티 코드

```java
@Entity
@Table(name = "users")
@Getter
@Builder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
public class User {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String email;

    @Column(nullable = false)
    private String password;

    @CreationTimestamp
    private LocalDateTime createdAt;
}
```

```java
@Entity
@Table(name = "todos")
@Getter
@Builder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
public class Todo {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 500)
    private String content;

    @Column(nullable = false)
    @Builder.Default
    private Boolean completed = false;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    // 완료 상태 토글
    public void toggleCompleted() {
        this.completed = !this.completed;
    }

    // 내용 수정
    public void updateContent(String content) {
        this.content = content;
    }
}
```

---

## 화면 설계 (와이어프레임)

코드 전에 화면을 먼저 그려봅니다. 복잡한 툴이 필요 없습니다. 텍스트로 구조만 잡아도 충분합니다.

```
┌─────────────────────────────────────────┐
│  TodoList                   [로그아웃]   │  ← Header
├─────────────────────────────────────────┤
│  ┌───────────────────────────────────┐  │
│  │  할 일을 입력하세요...        [추가]│  │  ← 입력 영역
│  └───────────────────────────────────┘  │
│                                         │
│  [전체] [미완료] [완료]                  │  ← 필터 탭
│                                         │
│  ☐  Spring Boot 공부하기        [삭제]  │
│  ☑  Git 커밋 전략 읽기          [삭제]  │  ← 할 일 목록
│  ☐  포트폴리오 정리하기         [삭제]  │
│                                         │
│  총 3개 · 완료 1개                      │  ← 통계
└─────────────────────────────────────────┘
```

---

> 요구사항 단계에서 10분 투자하면, 개발 단계에서 10시간을 아낍니다. "일단 만들고 보자"는 가장 느린 방법입니다.

---

## 실습

```
1. 이 요구사항을 보고 빠진 것이 있는지 검토해보세요.
   - 비밀번호를 잊었을 때 어떻게 하는가?
   - 할 일에 마감일을 추가한다면 어떻게 모델링할까?
   - 할 일을 중요도 순으로 정렬한다면?

2. 본인이 만들고 싶은 서비스를 위 형식으로 요구사항 정의해보세요.
   - 사용자 스토리 5개 이상
   - 엔티티 2개 이상
   - ER 다이어그램 (텍스트로도 가능)
```
