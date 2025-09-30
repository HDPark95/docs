# 자동 회고 스크립트

Ollama를 사용하여 완료된 작업을 분석하고 주간/월간 회고를 자동으로 생성합니다.

## 필요 패키지 설치

```bash
pip install ollama
```

## 사용 방법

### 1. 주간 회고 생성

```bash
python3 scripts/weekly_review.py
```

- 이번 주 월요일~일요일의 완료된 작업 수집
- Ollama로 회고 생성
- `PARA/3_Resources/Think/review/weekly/YYYY-Www.md` 파일 생성

### 2. 월간 회고 생성

```bash
python3 scripts/monthly_review.py
```

- 이번 달의 완료된 작업 수집
- Ollama로 회고 생성
- `PARA/3_Resources/Think/review/monthly/YYYY-MM.md` 파일 생성

## 자동 실행 설정 (Cron)

### macOS/Linux

crontab 편집:
```bash
crontab -e
```

다음 내용 추가:

```bash
# 매주 일요일 오후 8시에 주간 회고 생성
0 20 * * 0 cd /Users/hyundoopark/Documents/GitHub/docs && /usr/bin/python3 scripts/weekly_review.py >> logs/weekly_review.log 2>&1

# 매월 마지막 날 오후 9시에 월간 회고 생성
0 21 28-31 * * [ $(date -d tomorrow +\%d) -eq 01 ] && cd /Users/hyundoopark/Documents/GitHub/docs && /usr/bin/python3 scripts/monthly_review.py >> logs/monthly_review.log 2>&1
```

**참고**: 경로를 실제 환경에 맞게 수정하세요.

### Python 경로 찾기

```bash
which python3
```

### 로그 디렉토리 생성

```bash
mkdir -p logs
```

### Cron 작동 확인

```bash
# Cron 서비스 확인 (macOS)
sudo launchctl list | grep cron

# Cron 로그 확인
tail -f logs/weekly_review.log
```

## 설정

스크립트 상단의 설정 변경:

```python
OLLAMA_MODEL = "llama3.2"  # 사용할 Ollama 모델
```

다른 모델 사용 가능:
- `llama3.2` (추천 - 빠르고 정확)
- `llama3`
- `mistral`
- `gemma`

## 수동 실행 권한 부여

```bash
chmod +x scripts/weekly_review.py
chmod +x scripts/monthly_review.py
```

실행:
```bash
./scripts/weekly_review.py
./scripts/monthly_review.py
```

## 문제 해결

### Ollama 연결 오류
- Ollama가 실행 중인지 확인: `ollama serve`
- 모델이 다운로드되어 있는지 확인: `ollama list`
- 모델 다운로드: `ollama pull llama3.2`

### Cron이 작동하지 않음
- macOS에서 Cron에 Full Disk Access 권한 부여 필요
- System Preferences → Security & Privacy → Privacy → Full Disk Access → cron 추가

### 경로 오류
- 스크립트의 `DOCS_ROOT` 경로 확인
- 절대 경로 사용 권장

## 생성되는 파일 형식

### 주간 리뷰
```
PARA/3_Resources/Think/review/weekly/2025-W39.md
```

### 월간 리뷰
```
PARA/3_Resources/Think/review/monthly/2025-09.md
```

## 참고

- 완료된 작업은 `- [x]` 형식으로 체크된 항목만 인식
- Tasks 플러그인의 `✅ YYYY-MM-DD` 완료 날짜 마크 지원
- 프로젝트별로 작업을 자동 그룹화
- AI 회고는 참고용이며, 필요시 수동으로 수정 권장