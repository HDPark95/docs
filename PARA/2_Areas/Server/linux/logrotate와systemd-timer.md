# Logrotate와 Systemd Timer 가이드

## Logrotate 개요

### Logrotate란?
Logrotate는 Linux 시스템에서 로그 파일을 자동으로 관리하는 유틸리티이다.

### 주요 기능
- **로그 회전**: 일정 크기나 기간이 지나면 새 로그 파일 생성
- **압축**: 오래된 로그 파일을 gzip으로 압축
- **삭제**: 보관 기간이 지난 로그 자동 삭제

## Logrotate 설정

### 설정 파일 구조
```bash
/etc/logrotate.conf          # 메인 설정 파일
/etc/logrotate.d/            # 애플리케이션별 설정 디렉토리
├── tomcat
└── mssql
```

### 설정 예제
```bash
# /etc/logrotate.d/myapp
/var/log/myapp/*.log {
    daily                    # 매일 로테이션
    rotate 14               # 14개 파일 보관
    compress                # gzip 압축
    delaycompress          # 다음 로테이션까지 압축 지연
    notifempty             # 빈 파일은 로테이션 안함
    create 0644 root root  # 새 파일 생성 시 권한 설정
    sharedscripts          # 스크립트를 한 번만 실행
    postrotate             # 로테이션 후 실행할 명령
        /usr/bin/systemctl reload myapp
    endscript
}
```

### 주요 옵션 설명
```bash
# 시간 기반 옵션
daily                      # 매일
weekly                     # 매주
monthly                    # 매월
yearly                     # 매년

# 크기 기반 옵션
size 100M                  # 100MB 초과 시 로테이션
maxsize 500M              # 최대 크기 제한

# 보관 옵션
rotate 7                   # 7개 파일 보관
maxage 30                 # 30일 이상된 파일 삭제

# 압축 옵션
compress                   # gzip 압축
nocompress                # 압축 안함
compresscmd /usr/bin/xz  # 압축 명령 지정
delaycompress             # 한 주기 뒤에 압축

```

## Systemd Timer로 Logrotate 실행

### Systemd Timer 구조
Systemd는 cron의 대안으로 timer 유닛을 제공. 
Logrotate는 기본적으로 systemd timer로 실행됨.

```bash
# Timer 유닛 파일
/usr/lib/systemd/system/logrotate.timer
/usr/lib/systemd/system/logrotate.service
```

### logrotate.timer 내용
```ini
[Unit]
Description=Daily rotation of log files
Documentation=man:logrotate(8) man:logrotate.conf(5)

[Timer]
OnCalendar=daily
AccuracySec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

### logrotate.service 내용
```ini
[Unit]
Description=Rotate log files
Documentation=man:logrotate(8) man:logrotate.conf(5)

[Service]
Type=oneshot
ExecStart=/usr/sbin/logrotate /etc/logrotate.conf
Nice=19
IOSchedulingClass=best-effort
IOSchedulingPriority=7

# 보안 강화 옵션
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
```

### Timer 관리 명령어
```bash
# Timer 상태 확인
systemctl status logrotate.timer
systemctl list-timers --all

# Timer 활성화/비활성화
systemctl enable logrotate.timer
systemctl disable logrotate.timer

# Timer 시작/중지
systemctl start logrotate.timer
systemctl stop logrotate.timer

# 수동으로 서비스 실행
systemctl start logrotate.service

# 다음 실행 시간 확인
systemctl list-timers logrotate.timer
```

## 트러블슈팅

### 디버깅 명령어
```bash
# Dry run (실제 실행 안함)
logrotate -d /etc/logrotate.conf

# 강제 실행
logrotate -f /etc/logrotate.conf

# Verbose 모드
logrotate -v /etc/logrotate.conf

# 상태 파일 확인
cat /var/lib/logrotate/logrotate.status
```

### 로그 확인 명령어(journalctl)

```bash
# logrotate 서비스 로그 확인
journalctl -u logrotate.service

# 최근 50줄만 확인
journalctl -u logrotate.service -n 50

# 실시간 로그 확인 (tail -f 처럼)
journalctl -u logrotate.service -f

# 특정 기간 로그 확인
journalctl -u logrotate.service --since "2024-01-01" --until "2024-01-31"
journalctl -u logrotate.service --since "1 hour ago"
journalctl -u logrotate.service --since yesterday

# Timer 로그 확인
journalctl -u logrotate.timer

# 에러만 필터링
journalctl -u logrotate.service -p err

# 상세 로그 출력 (verbose)
journalctl -u logrotate.service -o verbose

# JSON 형식으로 출력 (파싱용)
journalctl -u logrotate.service -o json

# 부팅 이후 로그만 확인
journalctl -u logrotate.service -b

# 이전 부팅 시 로그 확인
journalctl -u logrotate.service -b -1

# 로그 우선순위별 확인
# 0: emerg, 1: alert, 2: crit, 3: err, 4: warning, 5: notice, 6: info, 7: debug
journalctl -u logrotate.service -p warning

# 여러 유닛 동시 확인
journalctl -u logrotate.service -u logrotate.timer

# 특정 필드로 필터링
journalctl -u logrotate.service _PID=1234
journalctl -u logrotate.service _SYSTEMD_UNIT=logrotate.service

# 로그 용량 확인
journalctl --disk-usage

# 오래된 로그 정리 (100MB만 유지)
sudo journalctl --vacuum-size=100M

# 30일 이상 오래된 로그 삭제
sudo journalctl --vacuum-time=30d
```

#### 자주 발생하는 로그 메시지 해석
```bash
# 정상 실행
"Started Rotate log files."
"logrotate.service: Succeeded."

# 경고/에러 메시지
"error: skipping \"/var/log/myapp.log\" because parent directory has insecure permissions"
# → 상위 디렉토리 권한 문제

"error: stat of /var/log/nginx/access.log failed: No such file or directory"
# → 로그 파일이 존재하지 않음 (missingok 옵션 필요)

"error: unable to open /var/lib/logrotate/logrotate.status.tmp for writing: Read-only file system"
# → ProtectSystem 설정으로 인한 쓰기 권한 문제

```

### ProtectSystem=full 설정과 Systemd 샌드박스

#### Systemd의 파일시스템 보호 메커니즘
Systemd는 서비스의 보안을 강화하기 위해 파일시스템 접근을 제한하는 샌드박스 기능을 제공함.
`ProtectSystem` 옵션으로 이를 제공함.

```ini
# /usr/lib/systemd/system/logrotate.service
[Service]
Type=oneshot
ExecStart=/usr/sbin/logrotate /etc/logrotate.conf

# 보안 샌드박스 설정
ProtectSystem=full      # /usr, /boot, /etc를 읽기 전용으로
ProtectHome=true        # /home, /root, /run/user 접근 차단
PrivateTmp=true         # 격리된 /tmp 네임스페이스 사용
```

#### ProtectSystem 옵션별 동작
```ini
# ProtectSystem=false (기본값)
# 보호 없음, 모든 파일시스템 쓰기 가능

# ProtectSystem=true
# /usr, /boot, /efi 디렉토리를 읽기 전용으로 마운트
# /etc, /var 등은 쓰기 가능

# ProtectSystem=full
# true + /etc도 읽기 전용으로 마운트

# ProtectSystem=strict
# 모든 파일시스템을 읽기 전용으로 마운트
```

#### logrotate에서 ProtectSystem 문제 해결
```bash
systemctl show logrotate.service | grep Protect

sudo systemctl edit logrotate.service

[Service]
# strict 유지하면서 필요한 경로만 허용
ProtectSystem=strict
ReadWritePaths=/var/log /var/lib/logrotate /run
```
