---
title: "10-2. ChatClient · 프롬프트 템플릿 · 구조화 출력"
order: 2
tags: [chatclient, prompt-template, structured-output, spring-ai]
status: draft
author: vivace
---

# 10-2. ChatClient · 프롬프트 템플릿 · 구조화 출력

Spring AI의 ChatClient는 단순한 텍스트 호출을 넘어 프롬프트 템플릿, 구조화된 출력, 시스템 메시지 관리까지 지원합니다.

---

## 시스템 프롬프트 설정

```java
@Configuration
public class AiConfig {

    @Bean
    public ChatClient customerServiceClient(ChatClient.Builder builder) {
        return builder
                .defaultSystem("""
                        당신은 이커머스 고객 서비스 어시스턴트입니다.
                        항상 한국어로 답하고, 공감적이고 친절하게 응대하세요.
                        환불, 배송, 상품 문의만 처리합니다.
                        다른 주제는 "해당 문의는 처리하기 어렵습니다."라고 답하세요.
                        """)
                .build();
    }
}
```

```java
@Service
@RequiredArgsConstructor
public class CustomerServiceAi {

    private final ChatClient customerServiceClient;

    public String handleInquiry(String customerMessage) {
        return customerServiceClient.prompt()
                .user(customerMessage)
                .call()
                .content();
    }
}
```

---

## 프롬프트 템플릿

변수를 포함한 프롬프트를 재사용 가능하게 관리합니다.

### 코드에서 인라인 정의

```java
public String summarizeReview(String productName, String review) {
    return chatClient.prompt()
            .user(u -> u.text("""
                    상품: {product}
                    리뷰: {review}
                    
                    위 리뷰를 두 문장으로 요약하고 별점(1~5)을 매겨주세요.
                    """)
                    .param("product", productName)
                    .param("review", review))
            .call()
            .content();
}
```

### 파일로 분리 (권장)

프롬프트가 길어지면 `resources/prompts/` 폴더에 분리합니다.

```
src/main/resources/
└── prompts/
    ├── review-summary.st      ← StringTemplate 형식
    ├── product-description.st
    └── customer-reply.st
```

```
// review-summary.st
상품: {product}
리뷰: {review}

위 리뷰를 다음 형식으로 요약하세요:
- 핵심 요약: (한 문장)
- 별점: (1~5)
- 개선 제안: (있으면 한 문장, 없으면 "없음")
```

```java
@Value("classpath:prompts/review-summary.st")
private Resource reviewSummaryPrompt;

public String summarizeReview(String productName, String review) {
    return chatClient.prompt()
            .user(u -> u.text(reviewSummaryPrompt)
                    .param("product", productName)
                    .param("review", review))
            .call()
            .content();
}
```

---

## 구조화된 출력 — BeanOutputConverter

응답을 Java 객체로 바로 받습니다. JSON 파싱 코드를 직접 쓸 필요가 없습니다.

```java
// 원하는 출력 형태를 Java 레코드로 정의
public record ReviewAnalysis(
    String sentiment,     // positive, negative, neutral
    int score,            // 1~5
    List<String> keywords,
    String summary,
    boolean actionRequired
) {}
```

```java
public ReviewAnalysis analyzeReview(String reviewText) {
    return chatClient.prompt()
            .user(u -> u.text("""
                    다음 리뷰를 분석하세요.
                    
                    리뷰: {review}
                    """)
                    .param("review", reviewText))
            .call()
            .entity(ReviewAnalysis.class);  // 자동 역직렬화
}
```

Spring AI가 내부적으로 다음을 처리합니다:
1. `ReviewAnalysis` 스키마를 JSON Schema로 변환해 프롬프트에 추가
2. 모델 응답을 파싱해 `ReviewAnalysis` 인스턴스로 변환

```java
// 사용
ReviewAnalysis result = aiService.analyzeReview("배송이 늦었지만 상품은 좋아요.");
System.out.println(result.sentiment());   // neutral
System.out.println(result.score());       // 3
System.out.println(result.keywords());    // [배송지연, 상품품질]
```

---

## 멀티턴 대화 관리

```java
@Service
public class ConversationService {

    private final ChatClient chatClient;
    // 실제 서비스에서는 Redis나 DB에 저장
    private final Map<String, List<Message>> sessions = new ConcurrentHashMap<>();

    public ConversationService(ChatClient.Builder builder) {
        this.chatClient = builder
                .defaultSystem("당신은 친절한 어시스턴트입니다.")
                .build();
    }

    public String chat(String sessionId, String userMessage) {
        List<Message> history = sessions.computeIfAbsent(sessionId, k -> new ArrayList<>());
        
        history.add(new UserMessage(userMessage));
        
        String response = chatClient.prompt()
                .messages(history)
                .call()
                .content();
        
        history.add(new AssistantMessage(response));
        
        // 히스토리 크기 제한 (최근 20개)
        if (history.size() > 20) {
            history.subList(0, history.size() - 20).clear();
        }
        
        return response;
    }
    
    public void clearSession(String sessionId) {
        sessions.remove(sessionId);
    }
}
```

---

## 스트리밍 응답

```java
@GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<String> streamChat(@RequestParam String question) {
    return chatClient.prompt()
            .user(question)
            .stream()
            .content();
}
```

프론트엔드에서는 `EventSource`로 받습니다.

```javascript
const source = new EventSource(`/ai/stream?question=${encodeURIComponent(question)}`);
source.onmessage = (event) => {
    document.getElementById('response').textContent += event.data;
};
source.onerror = () => source.close();
```

---

## 테스트

```java
@SpringBootTest
class AiServiceTest {

    @Autowired
    private AiService aiService;

    @MockBean
    private ChatClient chatClient;

    @Test
    void analyzeReview_positive_returnsCorrectSentiment() {
        // given
        ReviewAnalysis fakeResult = new ReviewAnalysis("positive", 5,
                List.of("품질", "배송"), "훌륭한 상품", false);
        
        // ChatClient 체이닝 모킹
        var mockCallSpec = mock(ChatClient.CallResponseSpec.class);
        var mockRequestSpec = mock(ChatClient.ChatClientRequestSpec.class);
        
        when(chatClient.prompt()).thenReturn(mockRequestSpec);
        when(mockRequestSpec.user(any(Consumer.class))).thenReturn(mockRequestSpec);
        when(mockRequestSpec.call()).thenReturn(mockCallSpec);
        when(mockCallSpec.entity(ReviewAnalysis.class)).thenReturn(fakeResult);
        
        // when
        ReviewAnalysis result = aiService.analyzeReview("정말 좋아요!");
        
        // then
        assertThat(result.sentiment()).isEqualTo("positive");
        assertThat(result.score()).isEqualTo(5);
    }
}
```

---

> 프롬프트를 코드에서 분리하고, 응답을 객체로 받는 것. 이 두 가지가 유지보수 가능한 AI 기능의 기본입니다.
