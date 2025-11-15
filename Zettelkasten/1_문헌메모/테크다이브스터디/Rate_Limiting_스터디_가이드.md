Rate Limiting 알고리즘 스터디 가이드

4가지 Rate Limiting 알고리즘을 단계적으로 이해하고 구현하는 스터디 자료입니다.
각 담당자는 이전 알고리즘의 문제점을 해결하는 흐름으로 발표합니다.

기술 스택: Spring Cloud Gateway + Redis + Lua Script

---

## 스터디 진행 순서

1. (A) 고정 윈도우 → 가장 단순하지만 치명적 결함 존재
2. (B) 슬라이딩 윈도우 → (A)의 문제를 해결하지만 메모리/복잡도 증가
3. (C) 토큰 버킷 → 완전히 다른 접근, 버스트 트래픽 허용
4. (D) 리키 버킷 → (C)와 한 줄 차이, 트래픽 평탄화

---

## 공통 환경 설정

### build.gradle

```gradle
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.2.0'
    id 'io.spring.dependency-management' version '1.1.4'
}

group = 'com.techdive'
version = '0.0.1-SNAPSHOT'
sourceCompatibility = '17'

repositories {
    mavenCentral()
}

dependencies {
    implementation 'org.springframework.cloud:spring-cloud-starter-gateway'
    implementation 'org.springframework.boot:spring-boot-starter-data-redis-reactive'
    implementation 'org.springframework.boot:spring-boot-starter-webflux'

    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'
}

dependencyManagement {
    imports {
        mavenBom "org.springframework.cloud:spring-cloud-dependencies:2023.0.0"
    }
}
```

### application.yml

```yaml
spring:
  application:
    name: rate-limit-gateway
  data:
    redis:
      host: localhost
      port: 6379
  cloud:
    gateway:
      routes:
        - id: api-route
          uri: http://localhost:8081
          predicates:
            - Path=/api/**
          filters:
            - name: RateLimiter
              args:
                key-resolver: "#{@userKeyResolver}"

server:
  port: 8080

logging:
  level:
    org.springframework.cloud.gateway: DEBUG
```

### KeyResolver 설정

```java
package com.techdive.gateway.config;

import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Mono;

@Configuration
public class KeyResolverConfig {

    @Bean
    public KeyResolver userKeyResolver() {
        return exchange -> {
            // X-User-Id 헤더에서 사용자 ID 추출
            String userId = exchange.getRequest()
                .getHeaders()
                .getFirst("X-User-Id");

            return Mono.justOrEmpty(userId)
                .defaultIfEmpty("anonymous");
        };
    }
}
```

---

## (A) 고정 윈도우 (Fixed Window) 담당자

### 미션
"1시간에 100회 제한"을 Redis로 구현하는 가장 간단하고 멍청한 방법을 준비하세요.

### 핵심 아이디어
- Redis String 타입 + INCR + EXPIRE
- 시간 윈도우를 고정된 단위로 나눔 (예: 매 시각 정각 기준)
- 윈도우마다 카운터 초기화

### Spring Cloud Gateway 구현

```java
package com.techdive.gateway.filter;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.time.Instant;

@Slf4j
@Component
@RequiredArgsConstructor
public class FixedWindowRateLimiterGatewayFilterFactory
    extends AbstractGatewayFilterFactory<FixedWindowRateLimiterGatewayFilterFactory.Config> {

    private final ReactiveStringRedisTemplate redisTemplate;

    public FixedWindowRateLimiterGatewayFilterFactory() {
        super(Config.class);
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            String userId = exchange.getRequest()
                .getHeaders()
                .getFirst("X-User-Id");

            if (userId == null) {
                userId = "anonymous";
            }

            return isAllowed(userId, config.getLimit(), config.getWindowSeconds())
                .flatMap(allowed -> {
                    if (allowed) {
                        return chain.filter(exchange);
                    } else {
                        exchange.getResponse().setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
                        return exchange.getResponse().setComplete();
                    }
                });
        };
    }

    private Mono<Boolean> isAllowed(String userId, int limit, int windowSeconds) {
        long currentWindow = Instant.now().getEpochSecond() / windowSeconds;
        String key = String.format("rate_limit:fixed:%s:%d", userId, currentWindow);

        return redisTemplate.opsForValue()
            .get(key)
            .flatMap(currentCount -> {
                int count = Integer.parseInt(currentCount);
                if (count < limit) {
                    // 제한 이내 - 카운터 증가
                    return redisTemplate.opsForValue()
                        .increment(key)
                        .map(newCount -> true);
                } else {
                    // 제한 초과
                    return Mono.just(false);
                }
            })
            .switchIfEmpty(
                // 첫 요청 - 카운터 생성 및 TTL 설정
                redisTemplate.opsForValue()
                    .set(key, "1", Duration.ofSeconds(windowSeconds))
                    .thenReturn(true)
            );
    }

    public static class Config {
        private int limit = 100;
        private int windowSeconds = 3600; // 1시간

        public int getLimit() {
            return limit;
        }

        public void setLimit(int limit) {
            this.limit = limit;
        }

        public int getWindowSeconds() {
            return windowSeconds;
        }

        public void setWindowSeconds(int windowSeconds) {
            this.windowSeconds = windowSeconds;
        }
    }
}
```

### 구조 설명

```
윈도우 구분:
09:00:00 - 09:59:59 → window_id = 1234567 (고정)
10:00:00 - 10:59:59 → window_id = 1234568 (고정)
11:00:00 - 11:59:59 → window_id = 1234569 (고정)

Redis 키:
rate_limit:fixed:user123:1234567 → count=100 (TTL 3600초)
rate_limit:fixed:user123:1234568 → count=50  (TTL 3600초)
```

### 치명적 문제점 (다음 담당자에게 던질 포인트)

#### 문제 1: 윈도우 경계 문제 (Boundary Issue)

```
시나리오:
09:59:50 ~ 10:00:10 사이 20초 동안 200회 요청

09:59:50 - 09:59:59 (10초) → 100회 허용 (윈도우 1)
10:00:00 - 10:00:10 (10초) → 100회 허용 (윈도우 2)

결과: 20초 동안 200회 허용!
→ "1시간 100회" 정책 위반
```

#### 문제 2: 트래픽 급증 가능성

```
타임라인:
10:00:00 - 100회 요청 (모두 허용)
10:01:00 ~ 10:59:59 - 0회 요청
11:00:00 - 100회 요청 (모두 허용)

→ 2분 안에 200회 허용 (실제로는 초당 평균 1.67회인데 순간 100회)
```

### 발표 시 강조할 점

1. 구현 단순성
   - Redis 명령어 3개만 사용 (GET, SET, INCR)
   - 메모리 효율적 (윈도우당 1개 키)
   - 성능 우수 (O(1) 시간 복잡도)

2. 치명적 결함
   - 윈도우 경계에서 2배 트래픽 허용
   - 트래픽 분산 효과 없음
   - 시간대별 불균형

3. 질문 던지기
   - "윈도우 경계 문제를 어떻게 해결할 수 있을까요?"
   - "(B) 담당자님, 슬라이딩 윈도우가 이걸 어떻게 해결하나요?"

---

## (B) 슬라이딩 윈도우 (Sliding Window) 담당자

### 미션
(A)의 윈도우 경계 문제를 해결하는 2가지 방법을 준비하세요.

### 핵심 아이디어
- Log 방식: 모든 요청 시간을 저장 (정확하지만 메모리 많이 사용)
- Counter 방식: 이전 윈도우 + 현재 윈도우 가중 평균 (근사치, 메모리 효율적)

### 방법 1: Sliding Window Log (정확한 방법)

```java
package com.techdive.gateway.filter;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.data.redis.core.ReactiveRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.time.Instant;

@Slf4j
@Component
@RequiredArgsConstructor
public class SlidingWindowLogRateLimiterGatewayFilterFactory
    extends AbstractGatewayFilterFactory<SlidingWindowLogRateLimiterGatewayFilterFactory.Config> {

    private final ReactiveRedisTemplate<String, String> redisTemplate;

    public SlidingWindowLogRateLimiterGatewayFilterFactory() {
        super(Config.class);
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            String userId = exchange.getRequest()
                .getHeaders()
                .getFirst("X-User-Id");

            if (userId == null) {
                userId = "anonymous";
            }

            return isAllowed(userId, config.getLimit(), config.getWindowSeconds())
                .flatMap(allowed -> {
                    if (allowed) {
                        return chain.filter(exchange);
                    } else {
                        exchange.getResponse().setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
                        return exchange.getResponse().setComplete();
                    }
                });
        };
    }

    private Mono<Boolean> isAllowed(String userId, int limit, int windowSeconds) {
        String key = String.format("rate_limit:log:%s", userId);
        double now = Instant.now().toEpochMilli() / 1000.0;
        double windowStart = now - windowSeconds;

        return redisTemplate.opsForZSet()
            // 1. 윈도우 밖의 오래된 요청 제거
            .removeRangeByScore(key, 0, windowStart)
            .then(redisTemplate.opsForZSet().count(key, windowStart, now))
            .flatMap(count -> {
                if (count < limit) {
                    // 2. 현재 요청 추가
                    return redisTemplate.opsForZSet()
                        .add(key, String.valueOf(now), now)
                        .then(redisTemplate.expire(key, Duration.ofSeconds(windowSeconds + 60)))
                        .thenReturn(true);
                } else {
                    return Mono.just(false);
                }
            });
    }

    public static class Config {
        private int limit = 100;
        private int windowSeconds = 3600;

        public int getLimit() {
            return limit;
        }

        public void setLimit(int limit) {
            this.limit = limit;
        }

        public int getWindowSeconds() {
            return windowSeconds;
        }

        public void setWindowSeconds(int windowSeconds) {
            this.windowSeconds = windowSeconds;
        }
    }
}
```

#### Redis 데이터 구조

```
Sorted Set:
rate_limit:log:user456

Score (timestamp)       Member (timestamp)
1699999990.123   →      "1699999990.123"
1699999991.456   →      "1699999991.456"
1699999992.789   →      "1699999992.789"
...
(최대 100개 유지)

명령어:
ZREMRANGEBYSCORE rate_limit:log:user456 0 (now - 3600)
ZCOUNT rate_limit:log:user456 (now - 3600) now
ZADD rate_limit:log:user456 1699999990.123 "1699999990.123"
```

#### 장점
- 정확함: 실제 윈도우 내 요청 개수를 정확히 파악
- 윈도우 경계 문제 없음: 항상 "현재 시간 기준 과거 1시간" 계산

#### 단점
- 메모리 소비: 요청마다 타임스탬프 저장 (100회 × 16바이트 = 1.6KB)
- 대규모 트래픽 시 문제: 사용자 1만 명이면 16MB
- 계산 복잡도: ZREMRANGEBYSCORE는 O(log N + M)

### 방법 2: Sliding Window Counter (근사치 방법)

#### 핵심 아이디어

```
현재 시간: 10:30:00 (윈도우 중간)

이전 윈도우 (09:00 ~ 10:00): 80회
현재 윈도우 (10:00 ~ 11:00): 40회

예상 요청 수 = 이전 윈도우 × (남은 비율) + 현재 윈도우
             = 80 × (30/60) + 40
             = 40 + 40
             = 80회

→ 100회 제한이므로 허용
```

#### Spring Cloud Gateway 구현

```java
package com.techdive.gateway.filter;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.time.Instant;

@Slf4j
@Component
@RequiredArgsConstructor
public class SlidingWindowCounterRateLimiterGatewayFilterFactory
    extends AbstractGatewayFilterFactory<SlidingWindowCounterRateLimiterGatewayFilterFactory.Config> {

    private final ReactiveStringRedisTemplate redisTemplate;

    public SlidingWindowCounterRateLimiterGatewayFilterFactory() {
        super(Config.class);
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            String userId = exchange.getRequest()
                .getHeaders()
                .getFirst("X-User-Id");

            if (userId == null) {
                userId = "anonymous";
            }

            return isAllowed(userId, config.getLimit(), config.getWindowSeconds())
                .flatMap(allowed -> {
                    if (allowed) {
                        return chain.filter(exchange);
                    } else {
                        exchange.getResponse().setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
                        return exchange.getResponse().setComplete();
                    }
                });
        };
    }

    private Mono<Boolean> isAllowed(String userId, int limit, int windowSeconds) {
        long now = Instant.now().getEpochSecond();
        long currentWindow = (now / windowSeconds) * windowSeconds;
        long previousWindow = currentWindow - windowSeconds;

        String currentKey = String.format("rate_limit:counter:%s:%d", userId, currentWindow);
        String previousKey = String.format("rate_limit:counter:%s:%d", userId, previousWindow);

        // 현재 윈도우 내 진행 비율
        double elapsedTimeInWindow = now - currentWindow;
        double windowProgress = elapsedTimeInWindow / windowSeconds;
        double previousWindowWeight = 1 - windowProgress;

        return Mono.zip(
            redisTemplate.opsForValue().get(currentKey).defaultIfEmpty("0"),
            redisTemplate.opsForValue().get(previousKey).defaultIfEmpty("0")
        ).flatMap(tuple -> {
            int currentCount = Integer.parseInt(tuple.getT1());
            int previousCount = Integer.parseInt(tuple.getT2());

            double estimatedCount = (previousCount * previousWindowWeight) + currentCount;

            log.debug("이전 윈도우: {}회 (가중치 {})", previousCount, previousWindowWeight);
            log.debug("현재 윈도우: {}회", currentCount);
            log.debug("예상 총합: {}회", estimatedCount);

            if (estimatedCount < limit) {
                // 허용 - 현재 윈도우 카운터 증가
                return redisTemplate.opsForValue()
                    .increment(currentKey)
                    .then(redisTemplate.expire(currentKey, Duration.ofSeconds(windowSeconds * 2)))
                    .thenReturn(true);
            } else {
                return Mono.just(false);
            }
        });
    }

    public static class Config {
        private int limit = 100;
        private int windowSeconds = 3600;

        public int getLimit() {
            return limit;
        }

        public void setLimit(int limit) {
            this.limit = limit;
        }

        public int getWindowSeconds() {
            return windowSeconds;
        }

        public void setWindowSeconds(int windowSeconds) {
            this.windowSeconds = windowSeconds;
        }
    }
}
```

#### 장점
- 메모리 효율적: 윈도우당 1개 카운터만 저장
- 성능 우수: O(1) 시간 복잡도
- (A) 고정 윈도우보다 정확: 윈도우 경계 문제 완화

#### 단점
- 근사치: 완벽하게 정확하지 않음
- 최대 오차: 이전 윈도우 트래픽이 몰린 경우 2배까지 허용 가능

### 두 방법 비교표

| 항목 | Log 방식 | Counter 방식 |
|------|----------|--------------|
| 정확도 | 100% 정확 | 근사치 (오차 ~10%) |
| 메모리 | 높음 (요청×16B) | 낮음 (윈도우×2개) |
| 시간 복잡도 | O(log N + M) | O(1) |
| 확장성 | 트래픽 증가 시 부담 | 우수 |
| 적용 상황 | 정확도 중요 (결제 등) | 일반적인 API |

---

## (C) 토큰 버킷 (Token Bucket) 담당자

### 미션
'윈도우'와는 완전히 다른 '버킷' 개념을 설명하고, Race Condition을 Lua 스크립트로 해결하세요.

### 핵심 아이디어
- 버킷에 토큰이 일정 속도로 채워짐
- 요청 시 토큰 1개 소비
- 토큰 없으면 거부
- 버스트 트래픽 허용 (버킷이 가득 차 있으면)

### 왜 Race Condition이 발생하는가?

```
잘못된 구현 (순차적 Redis 명령어):

시간    요청A                    요청B                  실제 토큰
----    -----                    -----                  --------
T0      HGET tokens=1                                      1
T1                              HGET tokens=1               1
T2      HSET tokens=0                                      0
T3                              HSET tokens=0               0

결과: 토큰 1개로 2개 요청 허용! (잘못됨)
```

### Lua 스크립트로 해결

#### TokenBucketScript.lua

```lua
-- KEYS[1]: rate_limit:token:{userId}
-- ARGV[1]: capacity (버킷 용량)
-- ARGV[2]: refill_rate (초당 토큰 재충전 속도)
-- ARGV[3]: now (현재 시간)

local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

-- 현재 토큰 수와 마지막 업데이트 시간 조회
local tokens = tonumber(redis.call('HGET', key, 'tokens'))
local last_updated = tonumber(redis.call('HGET', key, 'last_updated'))

-- 초기화
if tokens == nil then
    tokens = capacity
    last_updated = now
end

-- 경과 시간 계산
local elapsed = now - last_updated

-- 토큰 재충전 (게으른 계산)
tokens = math.min(capacity, tokens + elapsed * refill_rate)

-- 토큰 소비 가능 여부 확인
if tokens >= 1 then
    -- 토큰 소비
    tokens = tokens - 1

    -- 업데이트
    redis.call('HSET', key, 'tokens', tokens)
    redis.call('HSET', key, 'last_updated', now)
    redis.call('EXPIRE', key, 3600)

    return 1  -- 허용
else
    return 0  -- 거부
end
```

#### Spring Cloud Gateway 구현

```java
package com.techdive.gateway.filter;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.core.io.ClassPathResource;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.http.HttpStatus;
import org.springframework.scripting.support.ResourceScriptSource;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

import javax.annotation.PostConstruct;
import java.io.IOException;
import java.time.Instant;
import java.util.Collections;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class TokenBucketRateLimiterGatewayFilterFactory
    extends AbstractGatewayFilterFactory<TokenBucketRateLimiterGatewayFilterFactory.Config> {

    private final ReactiveStringRedisTemplate redisTemplate;
    private RedisScript<Long> script;

    public TokenBucketRateLimiterGatewayFilterFactory() {
        super(Config.class);
    }

    @PostConstruct
    public void init() throws IOException {
        // Lua 스크립트 로드
        ResourceScriptSource scriptSource = new ResourceScriptSource(
            new ClassPathResource("scripts/token-bucket.lua")
        );
        this.script = RedisScript.of(scriptSource.getScriptAsString(), Long.class);
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            String userId = exchange.getRequest()
                .getHeaders()
                .getFirst("X-User-Id");

            if (userId == null) {
                userId = "anonymous";
            }

            return isAllowed(userId, config.getCapacity(), config.getRefillRate())
                .flatMap(allowed -> {
                    if (allowed) {
                        return chain.filter(exchange);
                    } else {
                        exchange.getResponse().setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
                        return exchange.getResponse().setComplete();
                    }
                });
        };
    }

    private Mono<Boolean> isAllowed(String userId, int capacity, int refillRate) {
        String key = String.format("rate_limit:token:%s", userId);
        double now = Instant.now().toEpochMilli() / 1000.0;

        List<String> keys = Collections.singletonList(key);
        List<String> args = List.of(
            String.valueOf(capacity),
            String.valueOf(refillRate),
            String.valueOf(now)
        );

        return redisTemplate.execute(script, keys, args)
            .next()
            .map(result -> result == 1L)
            .defaultIfEmpty(false);
    }

    public static class Config {
        private int capacity = 100;     // 버킷 용량
        private int refillRate = 10;    // 초당 토큰 재충전 속도

        public int getCapacity() {
            return capacity;
        }

        public void setCapacity(int capacity) {
            this.capacity = capacity;
        }

        public int getRefillRate() {
            return refillRate;
        }

        public void setRefillRate(int refillRate) {
            this.refillRate = refillRate;
        }
    }
}
```

### 게으른 계산 (Lazy Calculation) 설명

```
전통적 방법 (백그라운드 작업):
- 1초마다 모든 사용자 토큰 +10
- 사용자 100만 명이면 100만 번 업데이트
- Redis 부하 큼

게으른 계산:
- 요청이 올 때만 계산
- "마지막 업데이트 이후 몇 초 지났나?" → 토큰 계산
- Redis 업데이트 최소화

예시:
마지막 업데이트: 10:00:00 (토큰 50개)
현재 요청: 10:00:05 (5초 경과)
계산: 50 + (5초 × 10개/초) = 100개
```

---

## (D) 리키 버킷 (Leaky Bucket) 담당자

### 미션
토큰 버킷 Lua 스크립트를 딱 한 줄만 바꿔서 리키 버킷으로 만들고, 차이점을 설명하세요.

### 핵심 아이디어
- 버킷에 물(요청)이 쌓임
- 버킷 바닥에 구멍이 있어서 일정 속도로 물이 샘
- 버킷 넘치면 거부
- 트래픽 완전 평탄화

### Lua 스크립트 비교

#### 토큰 버킷 (C 담당자 코드)

```lua
-- 토큰 재충전
tokens = math.min(capacity, tokens + elapsed * refill_rate)

-- 토큰 소비
if tokens >= 1 then
    tokens = tokens - 1  -- ← 감소 (-)
    return 1
else
    return 0
end
```

#### 리키 버킷 (한 줄만 변경!)

```lua
-- 물 누수
water_level = math.max(0, water_level - elapsed * leak_rate)

-- 요청 추가
if water_level + 1 <= capacity then
    water_level = water_level + 1  -- ← 증가 (+)
    return 1
else
    return 0
end
```

### LeakyBucketScript.lua

```lua
-- KEYS[1]: rate_limit:leaky:{userId}
-- ARGV[1]: capacity (버킷 용량)
-- ARGV[2]: leak_rate (초당 누수 속도)
-- ARGV[3]: now (현재 시간)

local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local leak_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

-- 현재 물 높이와 마지막 업데이트 시간 조회
local water_level = tonumber(redis.call('HGET', key, 'water_level'))
local last_updated = tonumber(redis.call('HGET', key, 'last_updated'))

-- 초기화
if water_level == nil then
    water_level = 0
    last_updated = now
end

-- 경과 시간 계산
local elapsed = now - last_updated

-- 물 누수 (게으른 계산)
water_level = math.max(0, water_level - elapsed * leak_rate)

-- 요청 추가 가능 여부 확인
if water_level + 1 <= capacity then
    -- 요청 추가
    water_level = water_level + 1

    -- 업데이트
    redis.call('HSET', key, 'water_level', water_level)
    redis.call('HSET', key, 'last_updated', now)
    redis.call('EXPIRE', key, 3600)

    return 1  -- 허용
else
    return 0  -- 거부 (버킷 넘침)
end
```

### Spring Cloud Gateway 구현

```java
package com.techdive.gateway.filter;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.core.io.ClassPathResource;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.http.HttpStatus;
import org.springframework.scripting.support.ResourceScriptSource;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

import javax.annotation.PostConstruct;
import java.io.IOException;
import java.time.Instant;
import java.util.Collections;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class LeakyBucketRateLimiterGatewayFilterFactory
    extends AbstractGatewayFilterFactory<LeakyBucketRateLimiterGatewayFilterFactory.Config> {

    private final ReactiveStringRedisTemplate redisTemplate;
    private RedisScript<Long> script;

    public LeakyBucketRateLimiterGatewayFilterFactory() {
        super(Config.class);
    }

    @PostConstruct
    public void init() throws IOException {
        ResourceScriptSource scriptSource = new ResourceScriptSource(
            new ClassPathResource("scripts/leaky-bucket.lua")
        );
        this.script = RedisScript.of(scriptSource.getScriptAsString(), Long.class);
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            String userId = exchange.getRequest()
                .getHeaders()
                .getFirst("X-User-Id");

            if (userId == null) {
                userId = "anonymous";
            }

            return isAllowed(userId, config.getCapacity(), config.getLeakRate())
                .flatMap(allowed -> {
                    if (allowed) {
                        return chain.filter(exchange);
                    } else {
                        exchange.getResponse().setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
                        return exchange.getResponse().setComplete();
                    }
                });
        };
    }

    private Mono<Boolean> isAllowed(String userId, int capacity, int leakRate) {
        String key = String.format("rate_limit:leaky:%s", userId);
        double now = Instant.now().toEpochMilli() / 1000.0;

        List<String> keys = Collections.singletonList(key);
        List<String> args = List.of(
            String.valueOf(capacity),
            String.valueOf(leakRate),
            String.valueOf(now)
        );

        return redisTemplate.execute(script, keys, args)
            .next()
            .map(result -> result == 1L)
            .defaultIfEmpty(false);
    }

    public static class Config {
        private int capacity = 100;
        private int leakRate = 10;  // 초당 누수 속도

        public int getCapacity() {
            return capacity;
        }

        public void setCapacity(int capacity) {
            this.capacity = capacity;
        }

        public int getLeakRate() {
            return leakRate;
        }

        public void setLeakRate(int leakRate) {
            this.leakRate = leakRate;
        }
    }
}
```

### 차이점 정리

| 항목 | 토큰 버킷 | 리키 버킷 |
|------|-----------|-----------|
| 메타포 | 토큰이 채워짐 | 물이 새어나감 |
| 버스트 | 허용 ✓ | 거부 ✗ |
| 트래픽 | 변동 가능 | 평탄화 |
| 처리 방식 | 즉시 처리 | 큐잉 |
| 사용 사례 | API 제한 | 네트워크 스위치 |
| Lua 차이 | `tokens - 1` | `water + 1` |

### 실제 사용 예시

#### 토큰 버킷 적합
- API Rate Limiting (순간 트래픽 허용)
- 사용자 요청 제한 (UX 중요)
- Spring Cloud Gateway (대부분 토큰 버킷 사용)

#### 리키 버킷 적합
- 네트워크 트래픽 제어
- 메시지 큐 (Kafka, RabbitMQ)
- 백그라운드 작업 처리
- DDoS 방어

---

## 스터디 진행 가이드

### 타임라인 (총 90분)

1. (A) 고정 윈도우 - 20분
2. (B) 슬라이딩 윈도우 - 25분
3. (C) 토큰 버킷 - 25분
4. (D) 리키 버킷 - 15분
5. 종합 토론 - 5분

### 실습 환경 설정

```bash
# Redis 설치 (Docker)
docker run -d -p 6379:6379 redis:latest

# Spring Boot 프로젝트 실행
./gradlew bootRun

# 테스트
curl -H "X-User-Id: user123" http://localhost:8080/api/test
```

---

## 참고 자료

실제 서비스 사례
- AWS API Gateway: Token Bucket
- Stripe API: Token Bucket
- GitHub API: Token Bucket
- Spring Cloud Gateway: Token Bucket (RequestRateLimiter)
- CloudFlare: Hybrid (여러 알고리즘 조합)

Spring Cloud Gateway 공식 문서
- RequestRateLimiter Filter: https://docs.spring.io/spring-cloud-gateway/docs/current/reference/html/#the-requestratelimiter-gatewayfilter-factory
- Redis RateLimiter: https://docs.spring.io/spring-cloud-gateway/docs/current/reference/html/#the-redis-ratelimiter

---
