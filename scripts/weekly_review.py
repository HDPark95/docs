#!/usr/bin/env python3
"""
주간 회고 자동 생성 스크립트
Ollama를 사용하여 완료된 작업을 분석하고 회고를 생성합니다.
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import json

try:
    import ollama
except ImportError:
    print("Error: ollama 패키지가 설치되어 있지 않습니다.")
    print("설치: pip install ollama")
    exit(1)


# 설정
DOCS_ROOT = Path(__file__).parent.parent
PROJECTS_DIR = DOCS_ROOT / "PARA/1_Projects"
REVIEW_DIR = DOCS_ROOT / "PARA/3_Resources/Think/review/weekly"
OLLAMA_MODEL = "llama3.2"  # 사용할 Ollama 모델


def get_week_range():
    """이번 주 월요일과 일요일 날짜 반환"""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_week_number():
    """이번 주차 번호 (YYYY-Www 형식)"""
    today = datetime.now()
    return today.strftime("%Y-W%U")


def find_todo_files(start_date, end_date):
    """주간 범위 내의 모든 할일 파일 찾기"""
    todo_files = []

    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        for file in project_dir.glob("*.md"):
            # 날짜 형식 파일만 (YYYY-MM-DD.md)
            if re.match(r"\d{4}-\d{2}-\d{2}\.md", file.name):
                file_date_str = file.stem
                try:
                    file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                    if start_date <= file_date <= end_date:
                        todo_files.append(file)
                except ValueError:
                    continue

    return todo_files


def extract_completed_tasks(file_path):
    """파일에서 완료된 작업 추출"""
    completed_tasks = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 프로젝트명 추출
        project_name = file_path.parent.name

        # 완료된 작업 찾기 (- [x] 또는 - [X])
        pattern = r'^- \[x\] (.+?)(?:#|$)'
        matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)

        for match in matches:
            task = match.group(1).strip()
            completed_tasks.append({
                'project': project_name,
                'task': task,
                'date': file_path.stem
            })

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return completed_tasks


def generate_review_with_ollama(completed_tasks):
    """Ollama를 사용하여 회고 생성"""

    # 프로젝트별로 그룹화
    tasks_by_project = {}
    for task in completed_tasks:
        project = task['project']
        if project not in tasks_by_project:
            tasks_by_project[project] = []
        tasks_by_project[project].append(task['task'])

    # 프롬프트 생성
    prompt = "다음은 이번 주에 완료한 작업들입니다:\n\n"

    for project, tasks in tasks_by_project.items():
        prompt += f"## {project}\n"
        for task in tasks:
            prompt += f"- {task}\n"
        prompt += "\n"

    prompt += """
위 작업들을 분석하여 다음 항목에 대해 회고를 작성해주세요:

1. **잘한 점**: 이번 주에 잘 진행된 부분
2. **아쉬운 점**: 개선이 필요한 부분이나 어려웠던 점
3. **배운 점**: 이번 주 작업을 통해 배운 기술적/비기술적 인사이트

각 항목을 2-3문장으로 간단명료하게 작성해주세요. 마크다운 형식으로 작성하되, 헤더는 사용하지 마세요.
"""

    try:
        print("Ollama로 회고 생성 중...")
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{
                'role': 'user',
                'content': prompt
            }]
        )

        return response['message']['content']

    except Exception as e:
        print(f"Ollama 호출 오류: {e}")
        return None


def create_weekly_review(completed_tasks, review_content):
    """주간 리뷰 파일 생성"""

    monday, sunday = get_week_range()
    week_num = get_week_number()

    # 파일명
    review_file = REVIEW_DIR / f"{week_num}.md"

    # 프로젝트별 작업 그룹화
    tasks_by_project = {}
    for task in completed_tasks:
        project = task['project']
        if project not in tasks_by_project:
            tasks_by_project[project] = []
        tasks_by_project[project].append(f"- [x] {task['task']}")

    # 마크다운 생성
    content = f"""---
created: {datetime.now().strftime("%Y-%m-%d %H:%M")}
week: {week_num}
tags: #주간리뷰 #review #auto-generated
---

# {monday.strftime("%Y년 %W주차")} 주간 리뷰

기간: {monday.strftime("%Y-%m-%d")} ~ {sunday.strftime("%Y-%m-%d")}

---

## 이번 주 완료한 작업

"""

    # 프로젝트별 작업 추가
    for project, tasks in tasks_by_project.items():
        content += f"\n### {project}\n\n"
        content += "\n".join(tasks)
        content += "\n"

    # Ollama 회고 추가
    content += """
---

## AI 회고 분석

"""

    if review_content:
        content += review_content
    else:
        content += "회고 생성 실패. 수동으로 작성해주세요."

    content += """

---

## 다음 주 목표

### Asyncsite
- [ ]

### Forbiz
- [ ]

### Personal
- [ ]

---

## 메모
"""

    # 파일 저장
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    with open(review_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"주간 리뷰 생성 완료: {review_file}")


def main():
    print("=" * 50)
    print("주간 회고 자동 생성 스크립트")
    print("=" * 50)

    # 이번 주 범위
    monday, sunday = get_week_range()
    print(f"기간: {monday.strftime('%Y-%m-%d')} ~ {sunday.strftime('%Y-%m-%d')}")

    # 할일 파일 찾기
    print("\n할일 파일 검색 중...")
    todo_files = find_todo_files(monday, sunday)
    print(f"발견: {len(todo_files)}개 파일")

    # 완료된 작업 추출
    print("\n완료된 작업 추출 중...")
    all_completed_tasks = []
    for file in todo_files:
        tasks = extract_completed_tasks(file)
        all_completed_tasks.extend(tasks)

    print(f"완료된 작업: {len(all_completed_tasks)}개")

    if not all_completed_tasks:
        print("\n완료된 작업이 없습니다.")
        return

    # 작업 목록 출력
    print("\n완료된 작업 목록:")
    for task in all_completed_tasks:
        print(f"  [{task['project']}] {task['task']}")

    # Ollama로 회고 생성
    print("\n" + "=" * 50)
    review_content = generate_review_with_ollama(all_completed_tasks)

    if review_content:
        print("\n생성된 회고:")
        print(review_content)

    # 주간 리뷰 파일 생성
    print("\n" + "=" * 50)
    create_weekly_review(all_completed_tasks, review_content)

    print("\n완료!")


if __name__ == "__main__":
    main()