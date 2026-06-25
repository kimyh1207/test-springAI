---
title: "19-3. 인증 · 비용 · 모니터링까지 고려한 설계"
order: 193
tags: [security, jwt, cost-management, monitoring, observability]
status: draft
author: vivace
wikidocs_id: ""
tistory_id: ""
---

# 19-3. 인증 · 비용 · 모니터링까지 고려한 설계

## 인증 설계

AI 서비스는 Spring Boot를 통해서만 접근 가능하다. FastAPI는 내부 네트워크에서만 노출된다.

```
인터넷 → Spring Boot (공개) → FastAPI (내부 전용)
                              MCP Server (내부 전용)
                              Chroma (내부 전용)
```

### JWT 흐름

```java
// Spring Security 설정
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {
    
    private final JwtAuthFilter jwtAuthFilter;
    
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/api/auth/**").permitAll()
                        .requestMatchers("/actuator/health").permitAll()
                        .requestMatchers("/api/chat/**").authenticated()
                        .requestMatchers("/api/admin/**").hasRole("ADMIN")
                        .anyRequest().authenticated()
                )
                .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class)
                .build();
    }
}
```

```java
// JWT 생성 및 검증
@Service
public class JwtService {
    
    @Value("${jwt.secret}")
    private String secret;
    
    private static final long EXPIRATION_MS = 86_400_000; // 24시간
    
    public String generate(String userId, List<String> roles) {
        return Jwts.builder()
                .subject(userId)
                .claim("roles", roles)
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + EXPIRATION_MS))
                .signWith(Keys.hmacShaKeyFor(secret.getBytes()))
                .compact();
    }
    
    public Claims validate(String token) {
        return Jwts.parser()
                .verifyWith(Keys.hmacShaKeyFor(secret.getBytes()))
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}
```

### FastAPI 내부 인증 (서비스 간)

```python
# FastAPI — 내부 서비스 토큰 검증
import os
from fastapi import Header, HTTPException

INTERNAL_TOKEN = os.environ["INTERNAL_SERVICE_TOKEN"]

async def verify_internal_token(x_internal_token: str = Header(...)):
    """Spring Boot → FastAPI 호출 시 서비스 토큰 검증."""
    if x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="내부 서비스 토큰 불일치")
```

```java
// Spring Boot — FastAPI 호출 시 토큰 첨부
@Bean
public WebClient aiServiceClient(
        @Value("${ai.service.base-url}") String baseUrl,
        @Value("${ai.service.internal-token}") String token) {
    return WebClient.builder()
            .baseUrl(baseUrl)
            .defaultHeader("X-Internal-Token", token)
            .build();
}
```

---

## 비용 관리 설계

### 계층별 모델 선택

```python
# 복잡도에 따라 모델을 다르게 선택한다
def select_model(query: str, context_size: int) -> str:
    """
    단순 분류/요약 → Haiku (저렴)
    일반 QA → Sonnet (균형)
    복잡한 멀티스텝 에이전트 → Opus (고품질)
    """
    if context_size < 1000 and is_simple_query(query):
        return "claude-haiku-4-5-20251001"  # $0.25/1M input
    elif context_size < 10000:
        return "claude-sonnet-4-6"           # $3/1M input
    else:
        return "claude-opus-4-8"             # $15/1M input


def is_simple_query(query: str) -> bool:
    """단순 질문 판단: 도구 호출 없이 정책 답변 가능."""
    simple_patterns = ["언제", "어디서", "얼마", "몇 시", "전화번호"]
    return any(p in query for p in simple_patterns)
```

### 비용 한도 설정

```java
// Redis 기반 일일 비용 추적
@Service
@RequiredArgsConstructor
public class CostLimiter {
    
    private final RedisTemplate<String, String> redis;
    
    private static final double DAILY_LIMIT_USD = 50.0;
    private static final double PER_USER_DAILY_LIMIT_USD = 1.0;
    
    public boolean checkGlobalLimit() {
        String key = "cost:global:" + LocalDate.now();
        String value = redis.opsForValue().get(key);
        double current = value != null ? Double.parseDouble(value) : 0.0;
        return current < DAILY_LIMIT_USD;
    }
    
    public boolean checkUserLimit(String userId) {
        String key = "cost:user:" + userId + ":" + LocalDate.now();
        String value = redis.opsForValue().get(key);
        double current = value != null ? Double.parseDouble(value) : 0.0;
        return current < PER_USER_DAILY_LIMIT_USD;
    }
    
    public void recordCost(String userId, double costUsd) {
        Duration ttl = Duration.ofDays(2);
        
        redis.opsForValue().increment("cost:global:" + LocalDate.now(),
                (long)(costUsd * 10000));  // 소수점 처리: × 10000
        redis.expire("cost:global:" + LocalDate.now(), ttl);
        
        redis.opsForValue().increment("cost:user:" + userId + ":" + LocalDate.now(),
                (long)(costUsd * 10000));
        redis.expire("cost:user:" + userId + ":" + LocalDate.now(), ttl);
    }
}
```

### 응답 캐싱으로 비용 절감

```java
// 동일 쿼리 반복 → LLM 호출 없이 캐시 반환
@Service
@RequiredArgsConstructor
public class ResponseCache {
    
    private final RedisTemplate<String, String> redis;
    private static final Duration TTL = Duration.ofMinutes(30);
    
    public Optional<String> get(String queryHash) {
        String value = redis.opsForValue().get("cache:response:" + queryHash);
        return Optional.ofNullable(value);
    }
    
    public void put(String queryHash, String response) {
        redis.opsForValue().set(
                "cache:response:" + queryHash,
                response,
                TTL
        );
    }
    
    public String hashQuery(String query, String sessionId) {
        // 세션 무관한 질문만 캐싱 (주문 조회 등 개인 정보 포함 제외)
        if (isPersonalQuery(query)) return null;
        return DigestUtils.md5Hex(query.toLowerCase().strip());
    }
    
    private boolean isPersonalQuery(String query) {
        return query.contains("내 주문") || query.contains("나의") 
                || query.matches(".*ORD-\\d+.*");
    }
}
```

---

## 모니터링 설계

### 메트릭 분류

```
비즈니스 메트릭:
  - 일일 채팅 세션 수
  - 질문 유형별 분포 (반품/주문/상품)
  - 사용자 만족도 (엄지 척 피드백)
  - 도구 호출 성공률

기술 메트릭:
  - P50/P95/P99 응답 시간
  - LLM API 호출 수 / 오류율
  - 캐시 히트율
  - 토큰 사용량 추이

인프라 메트릭:
  - CPU / 메모리 사용률
  - Redis 연결 수
  - Kafka 메시지 지연
```

### Spring Boot Actuator + Micrometer

```java
// 커스텀 메트릭 등록
@Component
@RequiredArgsConstructor
public class ChatMetrics {
    
    private final MeterRegistry registry;
    
    private final Counter chatRequestsTotal;
    private final Timer chatLatency;
    private final Counter cacheMissTotal;
    
    @PostConstruct
    public void init() {
        Counter.builder("chat.requests.total")
                .tag("status", "success")
                .register(registry);
        
        Timer.builder("chat.latency.seconds")
                .publishPercentiles(0.5, 0.95, 0.99)
                .register(registry);
    }
    
    public void recordRequest(String status, long durationMs) {
        registry.counter("chat.requests.total", "status", status).increment();
        registry.timer("chat.latency.seconds")
                .record(durationMs, TimeUnit.MILLISECONDS);
    }
    
    public void recordCacheMiss() {
        registry.counter("chat.cache.miss.total").increment();
    }
}
```

### Grafana 대시보드 패널 정의

```json
{
  "panels": [
    {
      "title": "평균 응답 시간",
      "type": "gauge",
      "targets": [{
        "expr": "histogram_quantile(0.95, rate(chat_latency_seconds_bucket[5m]))"
      }],
      "thresholds": {"steps": [
        {"color": "green", "value": 0},
        {"color": "yellow", "value": 3},
        {"color": "red", "value": 5}
      ]}
    },
    {
      "title": "일일 LLM 비용 ($)",
      "type": "stat",
      "targets": [{
        "expr": "sum(ai_cost_usd_total) by (model)"
      }]
    },
    {
      "title": "도구 호출 분포",
      "type": "piechart",
      "targets": [{
        "expr": "sum by (tool_name) (rate(tool_calls_total[1h]))"
      }]
    }
  ]
}
```

---

## 알림 설정

```yaml
# alertmanager 규칙
groups:
  - name: ai-service-alerts
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(chat_latency_seconds_bucket[5m])) > 5
        for: 2m
        annotations:
          summary: "AI 응답 P95가 5초 초과"
          
      - alert: DailyCostLimit
        expr: sum(ai_cost_usd_total) > 45
        annotations:
          summary: "일일 LLM 비용이 $45 초과 (한도 $50)"
          
      - alert: HighErrorRate
        expr: rate(chat_requests_total{status="error"}[5m]) > 0.1
        for: 1m
        annotations:
          summary: "AI 서비스 오류율 10% 초과"
```

---

## 설계 요약

```
인증:
  외부 → Spring (JWT) → 내부 → FastAPI (서비스 토큰)
  개인 정보는 Spring 레이어에서만 처리

비용:
  모델 계층화: Haiku < Sonnet < Opus
  캐싱: 동일 질문 30분 재사용
  한도: 전체 $50/일, 사용자 $1/일

모니터링:
  메트릭: Prometheus + Micrometer
  시각화: Grafana 대시보드
  알림: 지연·비용·오류율 임계값
  로그: structlog JSON (PII 제외)
```

> "AI 서비스에서 모니터링은 선택이 아니다 — 토큰 비용은 트래픽과 함께 폭발한다."
