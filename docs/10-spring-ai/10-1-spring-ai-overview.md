---
title: "10-1. Spring AI 개요와 모델 추상화"
order: 1
tags: [spring-ai, chatclient, model-abstraction, configuration]
status: draft
author: vivace
---

# 10-1. Spring AI 개요와 모델 추상화

Spring AI는 생성형 AI 모델을 Spring 애플리케이션에 통합하기 위한 공식 프레임워크입니다. 모델 제공사에 상관없이 일관된 API를 제공합니다.

---

## 프로젝트 설정

### build.gradle

```groovy
plugins {
    id 'org.springframework.boot' version '3.3.0'
    id 'io.spring.dependency-management' version '1.1.5'
    id 'java'
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    
    // Spring AI BOM — 버전 통합 관리
    implementation platform('org.springframework.ai:spring-ai-bom:1.0.0')
    
    // 사용할 모델 선택 (하나 이상)
    implementation 'org.springframework.ai:spring-ai-openai-spring-boot-starter'
    implementation 'org.springframework.ai:spring-ai-anthropic-spring-boot-starter'
    
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'
}
```

### application.yml

```yaml
spring:
  ai:
    openai:
      api-key: ${OPENAI_API_KEY}
      chat:
        options:
          model: gpt-4o
          temperature: 0.7
    anthropic:
      api-key: ${ANTHROPIC_API_KEY}
      chat:
        options:
          model: claude-sonnet-4-6
          max-tokens: 2048
```

---

## 핵심 추상화 구조

Spring AI의 핵심은 `ChatModel` 인터페이스입니다. OpenAI든 Anthropic이든 같은 방식으로 호출합니다.

```
ChatClient (고수준 API)
    └── ChatModel (인터페이스)
            ├── OpenAiChatModel
            ├── AnthropicChatModel
            └── OllamaChatModel (로컬 모델)
```

```java
// 어떤 모델이든 같은 코드로 호출
@Service
public class AiService {

    private final ChatClient chatClient;

    public AiService(ChatClient.Builder builder) {
        this.chatClient = builder.build();
    }

    public String ask(String question) {
        return chatClient.prompt()
                .user(question)
                .call()
                .content();
    }
}
```

`ChatClient.Builder`는 Spring이 자동으로 주입합니다. `application.yml`의 설정을 읽어 적절한 모델 구현체를 선택합니다.

---

## 기본 동작 확인

```java
@RestController
@RequestMapping("/ai")
@RequiredArgsConstructor
public class AiController {

    private final AiService aiService;

    @GetMapping("/ask")
    public String ask(@RequestParam String question) {
        return aiService.ask(question);
    }
}
```

```bash
curl "http://localhost:8080/ai/ask?question=Spring%20AI가%20뭔가요%3F"
```

---

## 여러 모델 동시 사용

서비스에 따라 다른 모델을 쓰고 싶을 때 한정자(qualifier)로 구분합니다.

```java
@Configuration
public class AiConfig {

    @Bean
    @Qualifier("openai")
    public ChatClient openAiClient(OpenAiChatModel model) {
        return ChatClient.builder(model).build();
    }

    @Bean
    @Qualifier("anthropic")
    public ChatClient anthropicClient(AnthropicChatModel model) {
        return ChatClient.builder(model).build();
    }
}
```

```java
@Service
public class MultiModelService {

    private final ChatClient openAiClient;
    private final ChatClient anthropicClient;

    public MultiModelService(
        @Qualifier("openai") ChatClient openAiClient,
        @Qualifier("anthropic") ChatClient anthropicClient
    ) {
        this.openAiClient = openAiClient;
        this.anthropicClient = anthropicClient;
    }

    // 빠른 응답이 필요한 경우 → GPT-4o
    public String quickAnswer(String question) {
        return openAiClient.prompt().user(question).call().content();
    }

    // 긴 문서 분석 → Claude (긴 컨텍스트 윈도우)
    public String analyzeDocument(String document) {
        return anthropicClient.prompt().user(document).call().content();
    }
}
```

---

## 모델 옵션 런타임 오버라이드

요청마다 다른 설정을 적용해야 할 때 씁니다.

```java
// application.yml 기본값을 이 요청만 오버라이드
String response = chatClient.prompt()
        .user("창의적인 슬로건을 만들어줘")
        .options(OpenAiChatOptions.builder()
                .withTemperature(0.9f)     // 더 창의적으로
                .withMaxTokens(256)         // 짧게
                .build())
        .call()
        .content();
```

---

> Spring AI는 LLM을 스프링 생태계의 일등 시민으로 만듭니다. 의존성 주입, 설정 관리, 테스트 — 이미 알고 있는 방식 그대로 씁니다.
