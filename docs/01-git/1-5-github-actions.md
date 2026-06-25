---
title: "1-5. ★확장 — 협업 자동화: GitHub Actions로 CI 첫 걸음"
order: 5
tags: [github-actions, ci, automation]
status: draft
author: vivace
---

# 1-5. ★확장 — 협업 자동화: GitHub Actions로 CI 첫 걸음

코드를 push할 때마다 누군가 테스트를 돌리고 결과를 알려준다면 어떨까요. GitHub Actions는 그 "누군가"를 자동화합니다. 반복되는 수작업을 없애고, 팀이 코드에만 집중할 수 있는 환경을 만듭니다.

---

## CI란 무엇인가

CI(Continuous Integration, 지속적 통합)는 개발자가 코드를 공유 브랜치에 올릴 때마다 **자동으로 빌드하고 테스트하는 것**입니다.

CI 없이 팀이 일하면 이런 일이 생깁니다.

- A가 기능을 개발하는 동안 B도 같은 파일을 수정
- 나중에 합치려 하니 충돌에 테스트까지 깨짐
- 무엇이 언제 깨졌는지 추적이 안 됨
- "내 로컬에서는 됐는데..."

CI가 있으면 push 즉시 문제를 발견합니다. 문제가 작을 때 잡습니다. 시간이 지날수록 버그는 숨어들고 고치기 어려워집니다.

---

## GitHub Actions란

GitHub Actions는 GitHub에 내장된 자동화 도구입니다. 저장소에 `.github/workflows/` 폴더 안에 YAML 파일 하나를 만드는 것만으로 동작합니다. 별도 서버 없이, 추가 설치 없이 바로 씁니다.

### 핵심 개념

**Workflow** — 자동화 작업 전체를 정의하는 파일입니다. `.github/workflows/*.yml` 에 위치합니다.

**Event** — Workflow를 시작하는 신호입니다. `push`, `pull_request`, 특정 시간(`schedule`) 등이 있습니다.

**Job** — Workflow 안의 작업 단위입니다. 여러 Job은 병렬 또는 순서대로 실행할 수 있습니다.

**Step** — Job 안의 실행 단계입니다. 명령어 한 줄이거나, 미리 만들어진 Action을 사용합니다.

**Runner** — Job이 실행되는 서버입니다. GitHub이 Ubuntu, Windows, macOS 서버를 무료로 제공합니다.

```
Workflow (.github/workflows/ci.yml)
├── on: Event        push, pull_request, schedule ...
└── jobs:
    └── build-and-test
        ├── Step 1: 코드 체크아웃   (actions/checkout)
        ├── Step 2: Java 설치       (actions/setup-java)
        ├── Step 3: 빌드            (./gradlew build)
        └── Step 4: 결과 업로드     (actions/upload-artifact)
```

---

## 첫 번째 Workflow 만들기

Spring Boot 프로젝트를 기준으로 PR이 열릴 때마다 자동으로 빌드·테스트하는 Workflow를 만들어보겠습니다.

`.github/workflows/ci.yml`

```yaml
name: CI

# 어떤 이벤트에 실행할지 정의
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  build-and-test:
    # 어떤 OS에서 실행할지
    runs-on: ubuntu-latest

    steps:
      # 1. 코드를 Runner 서버로 가져옴
      - name: 코드 체크아웃
        uses: actions/checkout@v4

      # 2. Java 설치
      - name: Java 17 설치
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      # 3. Gradle 캐시 (빌드 속도 향상)
      - name: Gradle 캐시
        uses: actions/cache@v4
        with:
          path: |
            ~/.gradle/caches
            ~/.gradle/wrapper
          key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*') }}

      # 4. 빌드 권한 부여
      - name: Gradle 실행 권한
        run: chmod +x gradlew

      # 5. 빌드 및 테스트
      - name: 빌드 및 테스트
        run: ./gradlew build

      # 6. 테스트 결과 리포트 (실패해도 결과는 업로드)
      - name: 테스트 결과 업로드
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: build/reports/tests/
```

---

## YAML 문법 핵심만 짚기

GitHub Actions를 처음 접하면 YAML 문법이 낯설게 느껴집니다. 몇 가지만 알면 됩니다.

**들여쓰기가 구조를 결정합니다.** 탭이 아닌 공백 2칸을 씁니다.

```yaml
jobs:           # jobs 아래에
  build:        #   build라는 Job이 있고
    steps:      #     steps 아래에
      - name:   #       각 Step이 있음
```

**`uses`는 남이 만든 Action을 가져옵니다.**

```yaml
uses: actions/checkout@v4
# actions 조직의 checkout 저장소, v4 버전을 사용
```

**`run`은 직접 쉘 명령어를 실행합니다.**

```yaml
run: ./gradlew build
```

**`${{ }}`는 변수를 참조합니다.**

```yaml
key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*') }}
# runner.os: 현재 OS 이름 (Linux, Windows, macOS)
# hashFiles: 파일 내용으로 해시값 생성
```

---

## Workflow 실행 결과 보는 법

1. GitHub 저장소 상단 **Actions** 탭을 클릭합니다.
2. 왼쪽에서 Workflow 이름을 선택합니다.
3. 실행 목록에서 원하는 실행을 클릭합니다.
4. Job을 클릭하면 각 Step의 실행 로그가 펼쳐집니다.

PR에서는 리뷰 화면 하단에 CI 결과가 바로 보입니다.

```
✅ CI / build-and-test (pull_request)  — 통과
❌ CI / build-and-test (pull_request)  — 실패 (Details 클릭 시 로그 확인)
```

---

## 브랜치 보호 규칙과 연결하기

CI가 실패하면 PR 병합을 막을 수 있습니다. GitHub 저장소 **Settings → Branches → Branch protection rules**에서 설정합니다.

```
✅ Require status checks to pass before merging
   ✅ CI / build-and-test
```

이 설정 하나로 "테스트가 통과하지 않으면 main에 합칠 수 없다"는 규칙이 만들어집니다. 규칙이 코드가 아니라 시스템에 박히는 순간, 사람이 실수할 여지가 줄어듭니다.

---

## 더 나아가면

지금 만든 Workflow는 CI의 시작입니다. 여기서 확장하면 이런 것들이 가능합니다.

| 확장 | 설명 |
|------|------|
| **CD (지속적 배포)** | 테스트 통과 후 자동으로 서버에 배포 |
| **코드 품질 검사** | Checkstyle, SonarQube 연동 |
| **보안 취약점 스캔** | dependency-review-action 사용 |
| **슬랙 알림** | 빌드 실패 시 팀 채널에 자동 알림 |
| **멀티 환경 테스트** | Java 17, 21 등 여러 버전에서 동시 테스트 |

> 자동화는 규율이 아닙니다. 팀이 실수할 기회를 줄이는 안전망입니다. 한 번 만들어두면 팀 전체가 그 혜택을 누립니다.

---

## 실습

```bash
# 1. 프로젝트 루트에 Workflow 파일 생성
mkdir -p .github/workflows
touch .github/workflows/ci.yml

# 2. 위의 ci.yml 내용 붙여넣기 후 커밋
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions CI workflow"
git push origin feature/add-ci

# 3. GitHub에서 PR 열기
# → Actions 탭에서 Workflow 실행 확인
# → PR 하단에서 CI 결과 확인

# 4. 의도적으로 테스트를 실패시켜보기
# 테스트 파일에 실패하는 assertion 추가 후 push
# → CI가 실패하는 것을 확인
# → 수정 후 재push → CI 통과 확인
```

CI가 처음 통과되는 순간, 초록 체크마크 하나가 팀 전체에 "이 코드는 안전합니다"라고 말해줍니다.
