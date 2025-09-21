# Nginx 웹서버

## 개요
Nginx(엔진엑스)는 2004년 Igor Sysoev가 개발한 고성능 웹서버이자 리버스 프록시 서버입니다. C10K 문제(동시 접속 1만개 처리)를 해결하기 위해 설계되었습니다.

## 핵심 아키텍처

### Event-Driven 비동기 모델
```
Master Process
    ├── Worker Process 1 (이벤트 루프)
    ├── Worker Process 2 (이벤트 루프)
    ├── Worker Process 3 (이벤트 루프)
    └── Cache Manager Process
```

### 프로세스 구조
- **Master Process**: 설정 읽기, Worker 프로세스 관리
- **Worker Process**: 실제 요청 처리 (CPU 코어당 1개 권장)
- **Cache Manager**: 캐시 관리

## 스레드 모델

### Single-Threaded Event Loop
```c
// Worker 프로세스의 이벤트 루프 (의사코드)
while (true) {
    events = epoll_wait();  // I/O 이벤트 대기
    for (event in events) {
        if (event.type == NEW_CONNECTION) {
            accept_connection();
        } else if (event.type == READ_READY) {
            read_request();
        } else if (event.type == WRITE_READY) {
            send_response();
        }
    }
}
```

### 특징
1. **Non-blocking I/O**: 모든 I/O 작업이 비차단
2. **Event Notification**: epoll(Linux), kqueue(BSD) 사용
3. **적은 메모리**: 연결당 2-3KB 메모리 사용
4. **CPU 효율성**: Context switching 최소화

## 요청 처리 흐름

```
Client → [연결] → Worker Process
                      ↓
                  Event Loop
                      ↓
              [비동기 I/O 처리]
                      ↓
              파일 읽기/백엔드 프록시
                      ↓
                  [응답 전송]
```

## 설정 예제

```nginx
# nginx.conf
worker_processes auto;  # CPU 코어 수만큼 자동 설정
worker_connections 1024;  # Worker당 최대 연결 수

events {
    use epoll;  # Linux에서 epoll 사용
    multi_accept on;  # 한 번에 여러 연결 수락
}

http {
    sendfile on;  # 커널 레벨 파일 전송
    tcp_nopush on;  # 패킷 최적화
    keepalive_timeout 65;  # Keep-alive 연결 유지 시간
    
    server {
        listen 80;
        server_name example.com;
        
        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
        }
    }
}
```

## 장점
- **높은 동시성**: 수만 개의 동시 연결 처리 가능
- **낮은 메모리 사용**: 연결당 메모리 사용량 적음
- **정적 파일 서빙 우수**: 효율적인 파일 전송
- **리버스 프록시**: 로드 밸런싱, 캐싱 기능 내장

## 단점
- **동적 콘텐츠 처리**: 외부 프로세스(PHP-FPM 등) 필요
- **모듈 동적 로딩**: 대부분 컴파일 시 포함 필요
- **설정 복잡도**: 초기 학습 곡선 존재

## 사용 사례
- 정적 파일 서빙
- 리버스 프록시
- 로드 밸런서
- API 게이트웨이
- 마이크로서비스 라우팅