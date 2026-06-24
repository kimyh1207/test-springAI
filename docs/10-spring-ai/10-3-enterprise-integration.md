---
title: "10-3. ★확장 — 엔터프라이즈 백엔드에 LLM 통합하기"
order: 3
tags: [enterprise, cost, caching, fallback, observability]
status: draft
author: vivace
---

# 10-3. ★확장 — 엔터프라이즈 백엔드에 LLM 통합하기

데모에서 작동하는 것과 프로덕션에서 신뢰할 수 있는 것은 다릅니다. 비용, 속도, 장애 대응, 모니터링까지 고려해야 합니다.

---

## 비용 통제

LLM API는 토큰 단위 과금입니다. 트래픽이 늘면 비용이 선형으로 증가합니다.

### 캐싱 — 동일 요청은 API를 호출하지 않는다

```java
@Service
@RequiredArgsConstructor
public class CachedAiService {

    private final ChatClient chatClient;
    private final RedisTemplate<String, String> redisTemplate;

    private static final Duration CACHE_TTL = Duration.ofHours(24);

    public String ask(String question) {
        String cacheKey = "ai:cache:" + DigestUtils.md5DigestAsHex(question.getBytes());
        
        // 캐시 히트
        String cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached != null) {
            return cached;
        }
        
        // 캐시 미스 → API 호출
        String response = chatClient.prompt()
                .user(question)
                .call()
                .content();
        
        redisTemplate.opsForValue().set(cacheKey, response, CACHE_TTL);
        return response;
    }
}
```

### 모델 티어링 — 요청 복잡도에 따라 모델 선택

```java
@Service
public class TieredAiService {

    private final ChatClient fastClient;   // gpt-4o-mini (저비용)
    private final ChatClient powerClient;  // claude-sonnet-4-6 (고성능)

    public String process(String request, RequestComplexity complexity) {
        return switch (complexity) {
            case SIMPLE -> fastClient.prompt().user(request).call().content();
            case COMPLEX -> powerClient.prompt().user(request).call().content();
        };
    }

    public RequestComplexity estimateComplexity(String request) {
        // 단순 분류, 키워드 추출 → SIMPLE
        // 긴 문서 분석, 다단계 추론 → COMPLEX
        return request.length() > 500 ? RequestComplexity.COMPLEX : RequestComplexity.SIMPLE;
    }
}
```

---

## 장애 대응 — Fallback과 재시도

LLM API는 간헐적 장애, 타임아웃, 속도 제한이 발생합니다.

```java
@Service
public class ResilientAiService {

    private final ChatClient primaryClient;   // Claude
    private final ChatClient fallbackClient;  // OpenAI

    public String ask(String question) {
        try {
            return primaryClient.prompt()
                    .user(question)
                    .call()
                    .content();
        } catch (Exception e) {
            log.warn("Primary AI model failed, falling back: {}", e.getMessage());
            return fallbackClient.prompt()
                    .user(question)
                    .call()
                    .content();
        }
    }
}
```

### Resilience4j 재시도 + 서킷 브레이커

```java
@Service
public class ResilientAiService {

    private final ChatClient chatClient;
    private final RetryRegistry retryRegistry;
    private final CircuitBreakerRegistry circuitBreakerRegistry;

    public String ask(String question) {
        Retry retry = retryRegistry.retry("ai-service");
        CircuitBreaker circuitBreaker = circuitBreakerRegistry.circuitBreaker("ai-service");

        Supplier<String> decorated = CircuitBreaker.decorateSupplier(
                circuitBreaker,
                Retry.decorateSupplier(retry, () ->
                        chatClient.prompt().user(question).call().content()
                )
        );

        return Try.ofSupplier(decorated)
                .recover(throwable -> "죄송합니다. 현재 AI 서비스를 이용할 수 없습니다. 잠시 후 다시 시도해주세요.")
                .get();
    }
}
```

```yaml
# application.yml
resilience4j:
  retry:
    instances:
      ai-service:
        max-attempts: 3
        wait-duration: 1s
        retry-exceptions:
          - org.springframework.web.client.HttpServerErrorException
  circuit-breaker:
    instances:
      ai-service:
        failure-rate-threshold: 50
        wait-duration-in-open-state: 30s
```

---

## 타임아웃 설정

```yaml
spring:
  ai:
    openai:
      api-key: ${OPENAI_API_KEY}
      chat:
        options:
          model: gpt-4o
    # 커스텀 RestClient 설정
  mvc:
    async:
      request-timeout: 30000  # 30초
```

```java
@Configuration
public class AiClientConfig {

    @Bean
    public RestClient.Builder restClientBuilder() {
        return RestClient.builder()
                .requestFactory(new HttpComponentsClientHttpRequestFactory(
                        HttpClients.custom()
                                .setConnectionRequestTimeout(Timeout.ofSeconds(5))
                                .setResponseTimeout(Timeout.ofSeconds(25))
                                .build()
                ));
    }
}
```

---

## 모니터링 — 무슨 일이 일어나고 있는지 알아야 한다

### 사용량 추적

```java
@Aspect
@Component
@RequiredArgsConstructor
@Slf4j
public class AiUsageAspect {

    private final MeterRegistry meterRegistry;

    @Around("@annotation(TrackAiUsage)")
    public Object trackUsage(ProceedingJoinPoint joinPoint) throws Throwable {
        Timer.Sample sample = Timer.start(meterRegistry);
        
        try {
            Object result = joinPoint.proceed();
            
            sample.stop(meterRegistry.timer("ai.request",
                    "status", "success",
                    "method", joinPoint.getSignature().getName()
            ));
            
            meterRegistry.counter("ai.request.success").increment();
            return result;
            
        } catch (Exception e) {
            sample.stop(meterRegistry.timer("ai.request",
                    "status", "error",
                    "method", joinPoint.getSignature().getName()
            ));
            meterRegistry.counter("ai.request.error").increment();
            throw e;
        }
    }
}
```

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface TrackAiUsage {}
```

```java
@TrackAiUsage
public String analyzeReview(String review) {
    return chatClient.prompt().user(review).call().content();
}
```

### 입력·출력 로깅 (감사 목적)

```java
@Component
@Slf4j
public class AiAuditLogger {

    public void log(String sessionId, String input, String output, long durationMs) {
        // 개인정보는 마스킹 처리
        String maskedInput = maskPii(input);
        
        log.info("AI_AUDIT sessionId={} durationMs={} inputLength={} outputLength={}",
                sessionId, durationMs, input.length(), output.length());
        
        // 별도 감사 테이블에 저장 (선택)
    }

    private String maskPii(String text) {
        // 이메일, 전화번호 등 개인정보 마스킹
        return text.replaceAll("[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}", "[EMAIL]")
                   .replaceAll("\\d{3}-\\d{4}-\\d{4}", "[PHONE]");
    }
}
```

---

## 비동기 처리 — 응답 시간이 SLA를 초과하는 경우

```java
@Service
@RequiredArgsConstructor
public class AsyncAiService {

    private final ChatClient chatClient;

    @Async
    public CompletableFuture<String> analyzeAsync(String content) {
        String result = chatClient.prompt()
                .user(content)
                .call()
                .content();
        return CompletableFuture.completedFuture(result);
    }
}
```

```java
// 컨트롤러: 즉시 응답 후 결과는 웹소켓/폴링으로 전달
@PostMapping("/analyze")
public ResponseEntity<Map<String, String>> startAnalysis(@RequestBody String content) {
    String jobId = UUID.randomUUID().toString();
    
    asyncAiService.analyzeAsync(content)
            .thenAccept(result -> resultStore.put(jobId, result));
    
    return ResponseEntity.accepted().body(Map.of("jobId", jobId));
}

@GetMapping("/analyze/{jobId}")
public ResponseEntity<String> getResult(@PathVariable String jobId) {
    String result = resultStore.get(jobId);
    if (result == null) return ResponseEntity.accepted().build();  // 아직 처리 중
    return ResponseEntity.ok(result);
}
```

---

## 엔터프라이즈 통합 체크리스트

```
[ ] API 키를 환경변수/Secrets Manager로 관리
[ ] 재시도 + 서킷 브레이커 설정
[ ] 타임아웃 설정 (기본값은 너무 길다)
[ ] 응답 캐싱 (동일 요청 반복 방지)
[ ] 모델 티어링 (복잡도별 모델 선택)
[ ] 사용량 메트릭 수집 (Prometheus + Grafana)
[ ] 입력·출력 감사 로그
[ ] 개인정보 마스킹
[ ] 비용 알림 임계값 설정
[ ] Fallback 응답 정의
```

---

> LLM은 외부 의존성입니다. 데이터베이스가 장애날 때를 대비하듯, AI 서비스가 장애날 때도 대비해야 합니다. 그게 엔터프라이즈 수준입니다.
