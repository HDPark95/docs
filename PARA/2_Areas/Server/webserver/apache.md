# Apache 웹서버

## 개요
Apache HTTP Server는 1995년부터 개발된 세계에서 가장 널리 사용되는 웹서버입니다. 모듈식 구조와 유연한 설정으로 다양한 환경에서 활용됩니다.

## 핵심 아키텍처

### MPM (Multi-Processing Module) 구조
Apache는 다양한 MPM을 통해 요청을 처리합니다:

```
Apache Master Process
    ├── MPM (선택 가능)
    │   ├── Prefork MPM
    │   ├── Worker MPM
    │   └── Event MPM
    └── 모듈 시스템
```

## 스레드 모델 (MPM별)

### 1. Prefork MPM (프로세스 기반)
```
Master Process
    ├── Child Process 1 (단일 스레드)
    ├── Child Process 2 (단일 스레드)
    ├── Child Process 3 (단일 스레드)
    └── Child Process N
```

**특징:**
- 각 프로세스가 하나의 요청 처리
- 스레드 안전하지 않은 모듈과 호환
- 메모리 사용량 높음
- 안정성 우수 (프로세스 격리)

### 2. Worker MPM (하이브리드)
```
Master Process
    ├── Child Process 1
    │   ├── Thread 1
    │   ├── Thread 2
    │   └── Thread N (기본 25개)
    └── Child Process N
```

**특징:**
- 프로세스와 스레드 혼합
- 메모리 효율적
- 더 많은 동시 연결 처리
- 스레드 안전한 모듈 필요

### 3. Event MPM (이벤트 기반)
```
Master Process
    └── Child Process
        ├── Listener Thread (이벤트 처리)
        ├── Worker Thread 1
        ├── Worker Thread 2
        └── Worker Thread N
```

**특징:**
- Keep-alive 연결을 별도 스레드로 처리
- Worker MPM 개선 버전
- 더 효율적인 연결 관리

## 요청 처리 흐름

### Prefork MPM
```
Client → [연결] → Child Process (전용)
                      ↓
                  [요청 처리]
                      ↓
                  [응답 전송]
                      ↓
                  [프로세스 재사용 or 종료]
```

### Worker/Event MPM
```
Client → [연결] → Child Process → Thread Pool
                                      ↓
                                  [스레드 할당]
                                      ↓
                                  [요청 처리]
                                      ↓
                                  [응답 전송]
                                      ↓
                                  [스레드 반환]
```

## 설정 예제

### Prefork MPM 설정
```apache
<IfModule mpm_prefork_module>
    StartServers             5      # 시작 시 생성할 프로세스 수
    MinSpareServers          5      # 최소 유휴 프로세스
    MaxSpareServers          10     # 최대 유휴 프로세스
    MaxRequestWorkers        150    # 최대 동시 요청 수
    MaxConnectionsPerChild   0      # 프로세스당 최대 연결 (0=무제한)
</IfModule>
```

### Worker MPM 설정
```apache
<IfModule mpm_worker_module>
    StartServers             2      # 시작 프로세스 수
    MinSpareThreads          25     # 최소 유휴 스레드
    MaxSpareThreads          75     # 최대 유휴 스레드
    ThreadsPerChild          25     # 프로세스당 스레드 수
    MaxRequestWorkers        150    # 최대 동시 요청 수
    MaxConnectionsPerChild   0      # 프로세스당 최대 연결
</IfModule>
```

### Event MPM 설정
```apache
<IfModule mpm_event_module>
    StartServers             2
    MinSpareThreads          25
    MaxSpareThreads          75
    ThreadsPerChild          25
    MaxRequestWorkers        150
    MaxConnectionsPerChild   0
    AsyncRequestWorkerFactor 2      # 비동기 연결 처리 비율
</IfModule>
```

## 모듈 시스템

### 동적 모듈 로딩
```apache
# httpd.conf
LoadModule rewrite_module modules/mod_rewrite.so
LoadModule php_module modules/libphp.so
LoadModule ssl_module modules/mod_ssl.so
```

### 내장 모듈 활용
```apache
<VirtualHost *:80>
    ServerName example.com
    DocumentRoot /var/www/html
    
    # mod_rewrite 사용
    RewriteEngine On
    RewriteRule ^/old/(.*)$ /new/$1 [R=301,L]
    
    # mod_headers 사용
    Header set X-Frame-Options "SAMEORIGIN"
    
    # mod_deflate 사용 (압축)
    AddOutputFilterByType DEFLATE text/html text/css
</VirtualHost>
```

## 장점
- **모듈 생태계**: 풍부한 모듈과 확장성
- **.htaccess 지원**: 디렉토리별 설정 가능
- **동적 콘텐츠**: PHP, Python 등 직접 처리 가능
- **성숙도**: 오랜 역사와 안정성
- **문서화**: 방대한 문서와 커뮤니티

## 단점
- **메모리 사용량**: Prefork MPM 사용 시 높음
- **동시성 한계**: Nginx 대비 낮은 동시 연결 처리
- **설정 복잡도**: 많은 옵션과 지시어
- **성능**: 정적 파일 서빙에서 Nginx보다 느림

## 사용 사례
- 동적 웹 애플리케이션 (PHP, Python)
- 복잡한 URL 재작성이 필요한 사이트
- .htaccess를 통한 유연한 설정이 필요한 환경
- 레거시 시스템 호환성이 중요한 경우