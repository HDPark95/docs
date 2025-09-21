# Nginx vs Apache: 스레드 사용 관점 비교

## 핵심 차이점

### 동시성 모델 비교
| 구분 | Nginx | Apache |
|------|-------|--------|
| **기본 모델** | Event-driven 비동기 | Process/Thread 기반 동기 |
| **스레드 사용** | Worker당 단일 스레드 | 요청당 프로세스/스레드 |
| **I/O 처리** | Non-blocking I/O | Blocking I/O |
| **컨텍스트 스위칭** | 최소화 | 빈번함 |

## 스레드 모델 상세 비교

### Nginx: 이벤트 기반 단일 스레드
```
Worker Process (단일 스레드)
    ├── epoll/kqueue 이벤트 루프
    ├── 수천 개의 연결을 하나의 스레드로 처리
    └── CPU 코어당 1개 Worker 권장
```

**동작 방식:**
```c
// Nginx Worker의 이벤트 루프
while (1) {
    // 이벤트 대기 (블로킹 없음)
    events = epoll_wait(epfd, events, max_events, timeout);
    
    for (i = 0; i < events; i++) {
        // 비동기로 모든 이벤트 처리
        handle_event(events[i]);  // Non-blocking
    }
}
```

### Apache: 멀티 프로세스/스레드
```
Prefork MPM: 프로세스당 1개 연결
Worker MPM: 프로세스 내 여러 스레드
Event MPM: 스레드 + 이벤트 혼합
```

**동작 방식:**
```c
// Apache Worker MPM의 스레드 처리
void* worker_thread(void* arg) {
    while (1) {
        // 연결 대기 (블로킹)
        client_socket = accept(listen_socket);  // Blocking
        
        // 요청 처리 (동기식)
        handle_request(client_socket);  // Blocking I/O
        
        close(client_socket);
    }
}
```

## 메모리 사용량 비교

### 연결당 메모리 사용
```
Nginx:
- 연결당: 2-4KB
- 10,000 연결: ~40MB

Apache (Prefork):
- 프로세스당: 10-20MB
- 10,000 연결: ~150GB (실제로는 불가능)

Apache (Worker):
- 스레드당: 1-2MB
- 10,000 연결: ~15GB
```

## 성능 특성 비교

### 1. CPU 사용 패턴
```
Nginx:
┌─────────────────────────────┐
│ CPU Core 1: Worker 1 (100%) │  효율적인 CPU 활용
│ CPU Core 2: Worker 2 (100%) │  컨텍스트 스위칭 최소
│ CPU Core 3: Worker 3 (100%) │
│ CPU Core 4: Worker 4 (100%) │
└─────────────────────────────┘

Apache:
┌─────────────────────────────┐
│ CPU Core 1: ████░░░░ (40%)  │  프로세스/스레드 스위칭
│ CPU Core 2: ██████░░ (60%)  │  I/O 대기로 인한 유휴
│ CPU Core 3: ███░░░░░ (30%)  │  불균등한 부하 분산
│ CPU Core 4: █████░░░ (50%)  │
└─────────────────────────────┘
```

### 2. I/O 처리 효율성
```
Nginx (비동기):
요청1 ──┐
요청2 ──┼─→ [Event Loop] ─→ 동시 처리
요청3 ──┘

Apache (동기):
요청1 ─→ [Thread 1] ─→ 완료
요청2 ─→ [Thread 2] ─→ 완료
요청3 ─→ [Thread 3] ─→ 완료
```

## C10K 문제 해결 방식

### Nginx 접근법
```python
# 의사코드
connections = []
while True:
    ready_events = epoll.poll()  # O(1) 복잡도
    for event in ready_events:
        if event.is_readable():
            data = non_blocking_read(event.fd)
            process_data(data)
        elif event.is_writable():
            non_blocking_write(event.fd, response)
```

### Apache 접근법
```python
# Prefork MPM 의사코드
def handle_connection(socket):
    request = blocking_read(socket)  # 스레드 블로킹
    response = process_request(request)
    blocking_write(socket, response)  # 스레드 블로킹

# 각 프로세스/스레드에서 실행
while True:
    client = accept_connection()  # 블로킹
    handle_connection(client)
```

## 실제 사용 시나리오별 비교

### 1. 정적 파일 서빙 (이미지, CSS, JS)
```
Nginx: ★★★★★ (최적)
- 이벤트 기반으로 매우 효율적
- sendfile() 시스템 콜 활용

Apache: ★★★☆☆ (보통)
- 각 요청마다 스레드/프로세스 필요
- 오버헤드 존재
```

### 2. 동적 콘텐츠 (PHP, Python)
```
Nginx: ★★★☆☆ (외부 프로세스 필요)
- FastCGI/uWSGI 프록시 필요
- 추가 설정 복잡도

Apache: ★★★★★ (내장 모듈)
- mod_php, mod_python 직접 실행
- 설정 간단
```

### 3. WebSocket/Long Polling
```
Nginx: ★★★★★ (우수)
- 비동기 처리로 효율적
- 많은 idle 연결 처리 가능

Apache: ★★☆☆☆ (비효율)
- 각 연결이 스레드 점유
- 리소스 낭비 심함
```

## 하이브리드 아키텍처

### 최적의 조합
```
Internet
    ↓
[Nginx: 리버스 프록시]
    ├── 정적 파일 직접 서빙
    ├── 캐싱
    └── 로드 밸런싱
        ↓
[Apache: 애플리케이션 서버]
    └── 동적 콘텐츠 처리 (PHP, Python)
```

## 선택 가이드

### Nginx를 선택해야 할 때
- 높은 동시 접속이 필요한 경우
- 정적 파일 서빙이 주요 용도
- 리버스 프록시/로드 밸런서 필요
- 메모리 제약이 있는 환경
- 마이크로서비스 아키텍처

### Apache를 선택해야 할 때
- 동적 콘텐츠 처리가 주요 용도
- .htaccess 파일 지원 필요
- 다양한 모듈 생태계 활용
- 레거시 시스템 호환성
- 복잡한 URL 재작성 규칙

## 결론

**스레드 효율성**: Nginx > Apache
- Nginx는 이벤트 기반으로 적은 리소스로 많은 연결 처리
- Apache는 전통적인 스레드/프로세스 모델로 안정적이지만 리소스 집약적

**최신 트렌드**: 두 서버의 장점을 결합한 하이브리드 구성이 일반적
- Nginx: 프론트엔드 (정적 파일, 프록시)
- Apache: 백엔드 (동적 콘텐츠)