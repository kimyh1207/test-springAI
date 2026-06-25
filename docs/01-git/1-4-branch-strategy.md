---
title: "1-4. 브랜치 전략(Git Flow / Trunk-based)과 PR 리뷰"
order: 4
tags: [git, branch, gitflow]
status: draft
author: vivace
---

# 1-4. 브랜치 전략(Git Flow / Trunk-based)과 PR 리뷰

브랜치를 어떻게 나누고 관리하느냐는 팀의 개발 속도와 직결됩니다. 규칙이 없으면 충돌이 늘고, 규칙이 너무 복잡하면 오히려 팀이 느려집니다. 좋은 브랜치 전략은 팀 규모와 배포 방식에 맞아야 합니다.

---

## 브랜치 전략이 왜 필요한가

팀원이 2명만 되어도 "어느 브랜치에서 작업하지?", "언제 main에 합칠까?", "배포는 어떤 브랜치 기준으로 하지?" 같은 질문이 생깁니다. 이 질문들에 대한 팀의 합의가 바로 브랜치 전략입니다.

전략 없이 브랜치를 쓰면 이런 일이 생깁니다.

- A는 `main`에서 직접 작업, B는 별도 브랜치 사용 → 충돌 반복
- 배포했더니 미완성 기능이 섞여 나감
- 어떤 코드가 운영 중인지 아무도 모름

브랜치 전략은 이런 혼란을 막는 팀의 약속입니다.

---

## Git Flow — 안정성을 최우선으로

Git Flow는 2010년 Vincent Driessen이 제안한 전략으로, 지금도 릴리즈 주기가 명확한 프로젝트에서 널리 사용됩니다.

### 브랜치 구조

```
main        ─────────────────────────────────────▶  (운영 배포본)
               ↑ merge                  ↑ merge
release      ──────────────────────────              (배포 준비)
               ↑ merge
develop     ──────────────────────────────────────▶  (통합 개발)
               ↑ merge    ↑ merge    ↑ merge
feature/A  ───────        │           │
feature/B            ─────            │
feature/C                        ─────
```

| 브랜치 | 역할 | 특징 |
|--------|------|------|
| `main` | 운영 중인 코드 | 항상 배포 가능한 상태 유지 |
| `develop` | 다음 릴리즈 준비 | 기능 개발의 통합 지점 |
| `feature/*` | 기능 개발 | develop에서 분기, 완성 후 develop에 병합 |
| `release/*` | 배포 준비 | develop에서 분기, QA·버그수정 후 main+develop에 병합 |
| `hotfix/*` | 긴급 수정 | main에서 직접 분기, 수정 후 main+develop에 병합 |

### Git Flow의 흐름

**1단계: 기능 개발**
```bash
git checkout develop
git checkout -b feature/user-login   # develop에서 분기

# ... 개발 ...

git checkout develop
git merge feature/user-login         # 완성 후 develop에 병합
git branch -d feature/user-login     # 브랜치 삭제
```

**2단계: 배포 준비**
```bash
git checkout develop
git checkout -b release/1.2.0        # 릴리즈 브랜치 생성

# ... QA, 버그 수정 ...

git checkout main
git merge release/1.2.0              # 운영 배포
git tag -a v1.2.0 -m "Release 1.2.0"

git checkout develop
git merge release/1.2.0              # develop에도 반영
git branch -d release/1.2.0
```

**3단계: 긴급 버그 수정**
```bash
git checkout main
git checkout -b hotfix/login-error   # 운영에서 직접 분기

# ... 수정 ...

git checkout main
git merge hotfix/login-error
git checkout develop
git merge hotfix/login-error         # develop에도 반영
```

### Git Flow가 맞는 팀

- 모바일 앱, 패키지 소프트웨어처럼 **릴리즈 버전**이 명확한 프로젝트
- QA 단계가 길고 배포 주기가 주·월 단위인 팀
- 여러 버전을 동시에 유지보수해야 하는 경우

### Git Flow의 단점

브랜치가 많아질수록 관리 부담이 커집니다. `develop`과 `main`이 오래 따로 살다 보면 병합할 때 충돌이 커집니다. 빠른 배포가 필요한 팀에는 맞지 않습니다.

---

## Trunk-based Development — 속도를 최우선으로

Trunk-based Development(TBD)는 Google, Facebook 같은 빅테크 기업이 채택한 전략입니다. 핵심은 단순합니다. **모든 개발자가 하나의 브랜치(trunk = main)에 자주 통합합니다.**

### 브랜치 구조

```
main   ───●───●───●───●───●───●───▶  (모두가 여기에 직접 통합)
           │       │       │
short/A ───┘       │       │          (수명 1~2일의 짧은 브랜치)
short/B            └───────┘
```

브랜치를 만들더라도 수명은 최대 1~2일입니다. 오래 살아있는 브랜치는 없습니다.

### Trunk-based의 핵심 원칙

**1. 작게 나눠 자주 통합**
큰 기능도 작은 단위로 잘라 매일 main에 통합합니다. 완성되지 않은 코드는 Feature Flag로 숨깁니다.

```java
// Feature Flag 예시 — 기능은 있지만 아직 활성화 안 됨
if (featureFlags.isEnabled("new-payment-flow")) {
    return newPaymentService.process(request);
}
return legacyPaymentService.process(request);
```

**2. CI(지속적 통합)가 필수**
main에 push될 때마다 자동으로 테스트가 실행됩니다. 테스트가 없으면 TBD는 불가능합니다.

**3. 작은 PR, 빠른 리뷰**
PR 하나의 크기가 작아서 리뷰도 빠릅니다. 하루에 여러 번 배포도 가능합니다.

### Trunk-based가 맞는 팀

- 웹 서비스처럼 **지속적 배포**가 필요한 프로젝트
- 자동화된 테스트 인프라가 갖춰진 팀
- 소규모 팀 또는 개발 속도가 중요한 스타트업

### Trunk-based의 단점

테스트 자동화가 뒷받침되지 않으면 `main`이 쉽게 깨집니다. 팀 전체가 작은 단위로 일하는 문화가 필요합니다. 처음 도입할 때 팀 적응 비용이 있습니다.

---

## 두 전략 비교

| 항목 | Git Flow | Trunk-based |
|------|----------|-------------|
| 브랜치 수명 | 길다 (feature는 수일~수주) | 짧다 (1~2일) |
| 배포 주기 | 주·월 단위 | 일·시간 단위 |
| 진입 장벽 | 낮다 (구조가 명확) | 높다 (테스트 자동화 필수) |
| 충돌 위험 | 높다 (브랜치가 오래 분기) | 낮다 (자주 통합) |
| 적합한 규모 | 중·대규모, 릴리즈 주기 명확 | 소규모, 빠른 배포 |

어느 것이 더 좋은가는 없습니다. 팀의 상황에 맞는 것이 좋은 전략입니다.

---

## PR 리뷰 — 코드가 팀에 합류하는 관문

Pull Request는 "내가 작성한 코드를 공유 브랜치에 합칩시다"라는 제안입니다. 리뷰는 이 제안을 팀이 함께 검증하는 과정입니다.

### 좋은 PR의 조건

**작아야 합니다.** 500줄짜리 PR은 아무도 제대로 리뷰하지 않습니다. 200줄 이하가 이상적입니다. 큰 기능이라면 단계별로 나눠 PR을 올립니다.

**맥락을 설명합니다.** 코드만 올리지 않습니다. PR 본문에 이런 내용이 있어야 합니다.

```markdown
## 변경 내용
JWT 기반 로그인 구현. AccessToken(15분) + RefreshToken(7일) 구조.

## 변경 이유
세션 방식은 서버 스케일아웃 시 세션 공유 문제가 발생함.
Stateless 방식의 JWT로 전환.

## 테스트 방법
1. POST /api/auth/login 으로 토큰 발급 확인
2. 만료된 토큰으로 요청 시 401 응답 확인

## 관련 이슈
Closes #42
```

### 좋은 리뷰의 조건

리뷰는 사람이 아니라 코드를 봅니다. 리뷰어의 역할은 잘못을 지적하는 것이 아니라 함께 더 나은 코드를 만드는 것입니다.

**질문 형태로 씁니다.**
```
# 나쁜 리뷰
이렇게 하면 안 됩니다.

# 좋은 리뷰
이 경우 동시 요청이 많으면 race condition이 발생할 수 있지 않을까요?
synchronized 블록이나 atomic 연산을 고려해볼 수 있을 것 같습니다.
```

**칭찬도 리뷰입니다.**
```
이 부분 깔끔하게 처리했네요. 이 패턴 팀 전체에 적용하면 좋겠습니다.
```

**우선순위를 표시합니다.**
```
[필수] 이 버그는 반드시 수정해야 합니다.
[제안] 더 나은 방법이 있을 것 같아 공유합니다.
[질문] 이렇게 한 이유가 있나요?
```

### PR이 거절될 때

Approved가 아닌 Changes Requested를 받아도 실망할 필요 없습니다. 리뷰어의 피드백은 코드를 더 좋게 만들기 위한 협력입니다. 수정 후 다시 리뷰를 요청하면 됩니다.

> 코드 리뷰는 팀이 서로의 코드를 읽는 유일한 시간입니다. 그 시간이 쌓여 팀의 코드 품질이 결정됩니다.

---

## 실습

```bash
# 1. Git Flow 흉내내기
git checkout -b develop
git checkout -b feature/hello-world
echo "Hello" > hello.txt
git add hello.txt && git commit -m "feat: add hello world"

# develop에 병합
git checkout develop
git merge feature/hello-world --no-ff  # --no-ff: 병합 커밋 생성 (히스토리 보존)
git branch -d feature/hello-world

# 2. 병합 히스토리 확인
git log --oneline --graph

# 3. main에 릴리즈
git checkout main
git merge develop --no-ff
git tag -a v0.1.0 -m "First release"
git log --oneline --graph
```

`--no-ff` 옵션이 중요합니다. 이 옵션 없이 병합하면 Git이 fast-forward(단순히 포인터만 이동)를 시도해 병합 커밋이 생기지 않습니다. `--no-ff`를 쓰면 "언제 어떤 브랜치가 합쳐졌는지" 히스토리에 명확하게 남습니다.
