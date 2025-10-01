# Spring Boot 개발자를 위한 HTTP 인증과 쿠키 관련 질문

## 쿠키와 세션 관련 (11장 기반)

### 1. Spring Session과 쿠키 설정
**Q: Spring Boot에서 세션 쿠키의 SameSite 속성을 Strict로 설정했을 때, OAuth2 소셜 로그인이 실패하는 이유는 무엇이고 어떻게 해결할 수 있나요?**

**A:** OAuth2 플로우에서 소셜 로그인 제공자(Google, GitHub 등)가 콜백 URL로 리다이렉트할 때 이는 크로스 사이트 요청입니다. SameSite=Strict는 모든 크로스 사이트 요청에서 쿠키 전송을 차단하므로 세션 쿠키가 전송되지 않아 인증이 실패합니다.

해결 방법:
```yaml
# application.yml
server:
  servlet:
    session:
      cookie:
        same-site: lax  # Strict 대신 Lax 사용
```

또는 경로별 다른 설정:
```java
@Configuration
public class CookieConfig {
    @Bean
    public CookieSameSiteSupplier cookieSameSiteSupplier() {
        return CookieSameSiteSupplier.ofLax()
            .whenHasPath("/oauth2", CookieSameSiteSupplier.ofNone());
    }
}

### 2. 스케일아웃 환경에서의 세션 관리
**Q: 여러 서버 인스턴스가 로드밸런서 뒤에 있을 때, 세션 쿠키만으로 사용자 상태를 유지하는 것의 한계점과 Spring에서의 해결 방법은?**

**A:** 세션이 각 서버 인스턴스에 로컬로 저장되면 사용자가 다른 서버로 라우팅될 때 세션 정보를 찾을 수 없습니다.

해결 방법:
```java
// Spring Session Redis 설정
@Configuration
@EnableRedisHttpSession
public class SessionConfig {
    @Bean
    public LettuceConnectionFactory connectionFactory() {
        return new LettuceConnectionFactory("redis-server", 6379);
    }
}
```
```yaml
# application.yml
spring:
  session:
    store-type: redis
    redis:
      namespace: spring:session
    timeout: 30m
```

Sticky Session의 문제점:
- 특정 서버 장애 시 세션 손실
- 부하 분산 불균형
- 오토스케일링 제한

### 3. 쿠키 보안 설정
**Q: application.yml에서 server.servlet.session.cookie.secure=true로 설정했는데 개발 환경(HTTP)에서 로그인이 안 되는 이유는?**

**A:** Secure 플래그가 true이면 브라우저는 HTTPS 연결에서만 쿠키를 전송합니다. HTTP로 접속한 개발 환경에서는 쿠키가 전송되지 않아 세션 유지가 불가능합니다.

해결 방법 (Profile별 설정):
```yaml
# application-dev.yml
server:
  servlet:
    session:
      cookie:
        secure: false  # 개발 환경

# application-prod.yml
server:
  servlet:
    session:
      cookie:
        secure: true   # 운영 환경
        http-only: true
        same-site: strict
```

### 4. HttpOnly와 XSS
**Q: React SPA + Spring Boot API 구조에서 JWT를 쿠키에 저장할 때 HttpOnly를 설정하면 프론트엔드에서 토큰을 읽을 수 없는데, 이 상황에서 Authorization 헤더는 어떻게 설정하나요?**

**A:** HttpOnly 쿠키를 사용하면 Authorization 헤더를 명시적으로 설정할 필요가 없습니다. 브라우저가 자동으로 쿠키를 포함합니다.

```java
// Spring Boot 설정
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                  HttpServletResponse response,
                                  FilterChain chain) {
        // 쿠키에서 JWT 읽기
        Cookie[] cookies = request.getCookies();
        if (cookies != null) {
            String jwt = Arrays.stream(cookies)
                .filter(c -> "jwt".equals(c.getName()))
                .map(Cookie::getValue)
                .findFirst()
                .orElse(null);
            // JWT 검증 및 인증 처리
        }
    }
}

// CSRF 보호
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) {
        return http
            .csrf(csrf -> csrf
                .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse()))
            .build();
    }
}
```

## 기본 인증 관련 (12장 기반)

### 5. Spring Security와 Basic Auth
**Q: Spring Security에서 Basic Authentication을 구현할 때, 매 요청마다 DB를 조회하는 것의 성능 문제를 어떻게 해결할 수 있나요?**

**A:** Spring Cache를 활용하여 UserDetailsService를 캐싱합니다.

```java
@Service
public class CachedUserDetailsService implements UserDetailsService {
    @Autowired
    private UserRepository userRepository;

    @Override
    @Cacheable(value = "users", key = "#username")
    public UserDetails loadUserByUsername(String username) {
        return userRepository.findByUsername(username)
            .map(user -> User.builder()
                .username(user.getUsername())
                .password(user.getPassword())
                .authorities(user.getAuthorities())
                .build())
            .orElseThrow(() -> new UsernameNotFoundException(username));
    }

    @CacheEvict(value = "users", key = "#username")
    public void evictUser(String username) {
        // 비밀번호 변경시 캐시 무효화
    }
}

// Redis 캐시 설정
@Configuration
@EnableCaching
public class CacheConfig {
    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory factory) {
        return RedisCacheManager.builder(factory)
            .cacheDefaults(RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(5))  // 5분 TTL
                .disableCachingNullValues())
            .build();
    }
}
```

### 6. REST API 인증 전략
**Q: MSA 환경에서 서비스 간 통신에 Basic Auth를 사용하는 것과 API Key를 사용하는 것의 차이점은?**

**A:**
| 구분 | Basic Auth | API Key |
|------|------------|----------|
| 표준화 | HTTP 표준 스펙 | 비표준, 커스텀 구현 |
| 보안 | Base64 인코딩 (HTTPS 필수) | 해시/암호화 가능 |
| 관리 | 사용자 계정 관리 | 키 생성/폐기/로테이션 |
| 적용 | 단순 인증 | Rate Limiting, 세밀한 권한 |

```java
// API Key 인증 구현
@Component
public class ApiKeyAuthFilter extends OncePerRequestFilter {
    @Value("${api.keys}")
    private Map<String, String> apiKeys; // key: service-name, value: api-key

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                  HttpServletResponse response,
                                  FilterChain chain) {
        String apiKey = request.getHeader("X-API-Key");

        if (apiKeys.containsValue(apiKey)) {
            String serviceName = getServiceName(apiKey);
            // Rate limiting, 권한 체크 등
            request.setAttribute("service", serviceName);
            chain.doFilter(request, response);
        } else {
            response.setStatus(401);
        }
    }
}
```

**mTLS 고려:** 서비스 메시(Istio)에서 mTLS를 자동 처리하면 애플리케이션 레벨 인증 부담 경감

### 7. 401 vs 403
**Q: Spring Security에서 인증되지 않은 사용자와 권한이 없는 사용자를 구분하여 401과 403을 정확히 반환하는 방법은?**

**A:**
- **401 Unauthorized**: 인증되지 않은 사용자 (AuthenticationException)
- **403 Forbidden**: 인증되었지만 권한 없음 (AccessDeniedException)

```java
@Component
public class CustomAuthenticationEntryPoint implements AuthenticationEntryPoint {
    @Override
    public void commence(HttpServletRequest request,
                       HttpServletResponse response,
                       AuthenticationException authException) {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setHeader("WWW-Authenticate", "Basic realm=\"API\"");
        response.getWriter().write("Authentication required");
    }
}

@Component
public class CustomAccessDeniedHandler implements AccessDeniedHandler {
    @Override
    public void handle(HttpServletRequest request,
                      HttpServletResponse response,
                      AccessDeniedException accessDeniedException) {
        response.setStatus(HttpServletResponse.SC_FORBIDDEN);
        response.getWriter().write("Access denied - insufficient privileges");
    }
}

@Configuration
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http,
            CustomAuthenticationEntryPoint authEntryPoint,
            CustomAccessDeniedHandler accessDeniedHandler) {
        return http
            .exceptionHandling(ex -> ex
                .authenticationEntryPoint(authEntryPoint)     // 401
                .accessDeniedHandler(accessDeniedHandler))    // 403
            .build();
    }
}
```

### 8. Realm 활용
**Q: 하나의 Spring Boot 애플리케이션에서 관리자 영역과 사용자 영역에 다른 인증 방식을 적용하려면 어떻게 해야 하나요?**

**A:** Multiple SecurityFilterChain을 사용하여 경로별 다른 인증을 적용합니다.

```java
@Configuration
@EnableWebSecurity
public class MultipleAuthConfig {

    // 관리자 영역 - Basic Auth
    @Bean
    @Order(1)
    public SecurityFilterChain adminFilterChain(HttpSecurity http) throws Exception {
        return http
            .securityMatcher("/admin/**")
            .authorizeHttpRequests(auth -> auth.anyRequest().hasRole("ADMIN"))
            .httpBasic(basic -> basic.realmName("Admin Area"))
            .build();
    }

    // 사용자 영역 - JWT
    @Bean
    @Order(2)
    public SecurityFilterChain userFilterChain(HttpSecurity http) throws Exception {
        return http
            .securityMatcher("/api/**")
            .authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
            .oauth2ResourceServer(OAuth2ResourceServerConfigurer::jwt)
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .build();
    }

    // 기본 영역 - Form Login
    @Bean
    @Order(3)
    public SecurityFilterChain defaultFilterChain(HttpSecurity http) throws Exception {
        return http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/public/**").permitAll()
                .anyRequest().authenticated())
            .formLogin(Customizer.withDefaults())
            .build();
    }
}
```

## 통합 질문

### 9. 세션 vs 토큰
**Q: Spring Boot에서 전통적인 세션 기반 인증(JSESSIONID)과 JWT 토큰 기반 인증을 함께 사용해야 하는 경우는 언제이고, 어떻게 구현하나요?**

**A:** 웹 페이지는 세션, REST API는 JWT를 사용하는 하이브리드 구조가 일반적입니다.

```java
@Component
public class HybridAuthenticationFilter extends OncePerRequestFilter {
    @Autowired
    private JwtTokenProvider jwtProvider;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                  HttpServletResponse response,
                                  FilterChain chain) {
        String path = request.getRequestURI();

        if (path.startsWith("/api/")) {
            // JWT 인증
            String token = extractToken(request);
            if (token != null && jwtProvider.validateToken(token)) {
                Authentication auth = jwtProvider.getAuthentication(token);
                SecurityContextHolder.getContext().setAuthentication(auth);
            }
        }
        // 세션 기반 인증은 Spring Security가 자동 처리

        chain.doFilter(request, response);
    }

    private String extractToken(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }
}
```

### 10. 쿠키 동의와 GDPR
**Q: Spring Boot 애플리케이션에서 GDPR 준수를 위해 쿠키 동의 전에는 필수 쿠키만 설정하고, 동의 후 분석 쿠키를 추가하는 방법은?**

**A:** 쿠키 동의 상태를 체크하여 조건부로 쿠키를 설정합니다.

```java
@Service
public class CookieConsentService {
    private static final String CONSENT_COOKIE = "cookie-consent";

    public boolean hasConsent(HttpServletRequest request) {
        return Arrays.stream(request.getCookies() != null ?
                request.getCookies() : new Cookie[0])
            .anyMatch(c -> CONSENT_COOKIE.equals(c.getName())
                && "accepted".equals(c.getValue()));
    }

    public void setAnalyticsCookie(HttpServletRequest request,
                                  HttpServletResponse response) {
        if (hasConsent(request)) {
            Cookie analytics = new Cookie("_ga", generateAnalyticsId());
            analytics.setMaxAge(60 * 60 * 24 * 365); // 1년
            analytics.setPath("/");
            analytics.setSecure(true);
            analytics.setSameSite("Lax");
            response.addCookie(analytics);
        }
    }

    public void acceptCookies(HttpServletResponse response) {
        Cookie consent = new Cookie(CONSENT_COOKIE, "accepted");
        consent.setMaxAge(60 * 60 * 24 * 365);
        consent.setPath("/");
        consent.setHttpOnly(true);
        consent.setSecure(true);
        response.addCookie(consent);
    }
}

@Controller
public class CookieConsentController {
    @PostMapping("/cookie-consent")
    public String acceptCookies(HttpServletResponse response) {
        cookieConsentService.acceptCookies(response);
        // 동의 후 분석 쿠키 설정
        cookieConsentService.setAnalyticsCookie(request, response);
        return "redirect:/";
    }
}
```

### 11. 프록시 환경에서의 인증
**Q: Kubernetes Ingress나 API Gateway 뒤에 있는 Spring Boot 애플리케이션에서 클라이언트 IP 기반 제한을 구현할 때의 주의사항은?**

**A:** 프록시를 통해 전달된 X-Forwarded-For 헤더를 신뢰할 수 있는지 확인해야 합니다.

```yaml
# application.yml
server:
  forward-headers-strategy: framework  # 또는 native
  # native: Tomcat의 RemoteIpValve 사용
  # framework: Spring의 ForwardedHeaderFilter 사용

spring:
  cloud:
    gateway:
      forwarded:
        enabled: true

# 신뢰할 프록시 설정
server:
  tomcat:
    remoteip:
      internal-proxies: "10\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}|192\\.168\\.\\d{1,3}\\.\\d{1,3}"
      remote-ip-header: "X-Forwarded-For"
      protocol-header: "X-Forwarded-Proto"
```

```java
@Component
public class IpBasedRateLimiter {
    private final Map<String, RateLimiter> limiters = new ConcurrentHashMap<>();

    public boolean allowRequest(HttpServletRequest request) {
        String clientIp = getClientIp(request);
        RateLimiter limiter = limiters.computeIfAbsent(clientIp,
            ip -> RateLimiter.create(100.0)); // 100 req/sec

        return limiter.tryAcquire();
    }

    private String getClientIp(HttpServletRequest request) {
        // Spring이 처리한 실제 IP 가져오기
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }

        String xRealIp = request.getHeader("X-Real-IP");
        if (xRealIp != null && !xRealIp.isEmpty()) {
            return xRealIp;
        }

        return request.getRemoteAddr();
    }
}
```

### 12. 로그아웃 구현
**Q: Basic Auth는 로그아웃 메커니즘이 없다고 하는데, Spring Security에서 Basic Auth 사용 시 로그아웃을 구현하는 방법은?**

**A:** Basic Auth는 브라우저가 자격증명을 캐싱하므로 완전한 로그아웃은 불가능합니다. 대신 401 응답으로 재인증을 유도합니다.

```java
@RestController
public class LogoutController {

    // 방법 1: 401 응답으로 브라우저 캐시 무효화 시도
    @PostMapping("/logout")
    public ResponseEntity<String> logout() {
        return ResponseEntity
            .status(HttpStatus.UNAUTHORIZED)
            .header("WWW-Authenticate", "Basic realm=\"Logout\"")
            .body("You have been logged out");
    }

    // 방법 2: 세션 기반 + Basic Auth 하이브리드
    @PostMapping("/secure-logout")
    public String secureLogout(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        if (session != null) {
            session.invalidate();
        }
        SecurityContextHolder.clearContext();
        return "redirect:/login?logout";
    }
}

// JavaScript로 브라우저 캐시 강제 초기화 (제한적)
function logout() {
    // 잘못된 자격증명으로 401 유도
    fetch('/api/logout', {
        headers: {
            'Authorization': 'Basic ' + btoa('invalid:invalid')
        }
    }).then(() => {
        window.location.href = '/login';
    });
}
```

**베스트 프랙티스:** Basic Auth 대신 토큰 기반 인증을 사용하여 명확한 로그아웃 기능 구현

## 토론 주제

### 성능과 보안의 균형
**Q: 대용량 트래픽 서비스에서 모든 API 요청에 대해 인증/인가를 수행하는 것의 오버헤드를 줄이면서도 보안을 유지하는 방법은?**

**A:**
1. **토큰 캐싱**: JWT 검증 결과를 짧은 시간 캐싱 (Redis, 5-10초)
2. **게이트웨이 인증**: API Gateway에서 한 번만 인증, 내부 서비스는 신뢰
3. **비대칭 키**: RSA 공개키로 JWT 검증 (DB 조회 불필요)
4. **Rate Limiting**: IP/User별 요청 제한으로 부하 분산

### 마이크로서비스 인증
**Q: Spring Cloud Gateway에서 인증을 중앙화하고 다운스트림 서비스로 인증 정보를 전달하는 베스트 프랙티스는?**

**A:**
```java
// Gateway에서 JWT 검증 후 내부 헤더로 전달
@Component
public class AuthenticationGatewayFilter extends AbstractGatewayFilterFactory<Config> {
    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            // JWT 검증
            String jwt = extractJwt(exchange.getRequest());
            Claims claims = validateJwt(jwt);

            // 내부 헤더로 사용자 정보 전달
            ServerHttpRequest request = exchange.getRequest().mutate()
                .header("X-User-Id", claims.getSubject())
                .header("X-User-Roles", claims.get("roles", String.class))
                .build();

            return chain.filter(exchange.mutate().request(request).build());
        };
    }
}
```

### 쿠키리스 아키텍처
**Q: 최근 브라우저들의 서드파티 쿠키 제한과 SameSite 기본값 변경이 Spring Boot 애플리케이션 설계에 미치는 영향은?**

**A:**
1. **토큰 기반 인증 선호**: LocalStorage/SessionStorage + Bearer Token
2. **First-party 도메인 통합**: 서브도메인 활용으로 쿠키 공유
3. **CORS 정책 강화**: 명시적 Origin 허용 필요
4. **OAuth2 PKCE**: 쿠키 없는 OAuth2 플로우 채택

```java
// 쿠키리스 JWT 구현
@RestController
public class AuthController {
    @PostMapping("/auth/login")
    public ResponseEntity<TokenResponse> login(@RequestBody LoginRequest request) {
        // 인증 처리
        String accessToken = generateAccessToken(user);
        String refreshToken = generateRefreshToken(user);

        // 토큰을 응답 본문으로 전달 (쿠키 대신)
        return ResponseEntity.ok(new TokenResponse(accessToken, refreshToken));
    }
}
```