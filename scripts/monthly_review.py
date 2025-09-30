#!/usr/bin/env python3
"""
월간 회고 자동 생성 스크립트
Ollama를 사용하여 완료된 작업을 분석하고 회고를 생성합니다.
"""

import os
import re
from datetime import datetime
from pathlib import Path
import calendar

try:
    import ollama
except ImportError:
    print("Error: ollama 패키지가 설치되어 있지 않습니다.")
    print("설치: pip install ollama")
    exit(1)


# 설정
DOCS_ROOT = Path(__file__).parent.parent
PROJECTS_DIR = DOCS_ROOT / "PARA/1_Projects"
REVIEW_DIR = DOCS_ROOT / "PARA/3_Resources/Think/review/monthly"
OLLAMA_MODEL = "llama3.2"  # 사용할 Ollama 모델


def get_month_range():
    """이번 달 첫날과 마지막날 반환"""
    today = datetime.now()
    first_day = today.replace(day=1)
    last_day_num = calendar.monthrange(today.year, today.month)[1]
    last_day = today.replace(day=last_day_num)
    return first_day, last_day


def get_month_string():
    """이번 달 문자열 (YYYY-MM 형식)"""
    return datetime.now().strftime("%Y-%m")


def find_todo_files(start_date, end_date):
    """월간 범위 내의 모든 할일 파일 찾기"""
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
    """Ollama를 사용하여 월간 회고 생성"""

    # 프로젝트별로 그룹화
    tasks_by_project = {}
    for task in completed_tasks:
        project = task['project']
        if project not in tasks_by_project:
            tasks_by_project[project] = []
        tasks_by_project[project].append(task['task'])

    # 프롬프트 생성
    prompt = "다음은 이번 달에 완료한 작업들입니다:\n\n"

    for project, tasks in tasks_by_project.items():
        prompt += f"## {project}\n"
        for task in tasks:
            prompt += f"- {task}\n"
        prompt += "\n"

    prompt += f"\n총 완료 작업: {len(completed_tasks)}개\n\n"

    prompt += """
위 작업들을 분석하여 다음 항목에 대해 월간 회고를 작성해주세요:

1. **주요 성과**: 이번 달의 가장 중요한 성과나 마일스톤
2. **완료한 프로젝트**: 완전히 완료되거나 큰 진전이 있었던 작업들
3. **배운 점**: 이번 달 작업을 통해 얻은 주요 인사이트나 학습 내용

그리고 KPT 회고:
4. **Keep (계속할 것)**: 이번 달 잘 진행된 프로세스나 습관
5. **Problem (문제점)**: 개선이 필요한 부분이나 어려움
6. **Try (시도할 것)**: 다음 달에 시도해볼 새로운 방법이나 개선 사항

각 항목을 2-3문장으로 간단명료하게 작성해주세요. 마크다운 형식으로 작성하되, 헤더는 사용하지 마세요.
"""

    try:
        print("Ollama로 월간 회고 생성 중...")
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


def create_monthly_review(completed_tasks, review_content):
    """월간 리뷰 파일 생성"""

    first_day, last_day = get_month_range()
    month_str = get_month_string()

    # 파일명
    review_file = REVIEW_DIR / f"{month_str}.md"

    # 프로젝트별 작업 그룹화 및 통계
    tasks_by_project = {}
    for task in completed_tasks:
        project = task['project']
        if project not in tasks_by_project:
            tasks_by_project[project] = []
        tasks_by_project[project].append(f"- [x] {task['task']}")

    # 마크다운 생성
    content = f"""---
created: {datetime.now().strftime("%Y-%m-%d %H:%M")}
month: {month_str}
tags: #월간리뷰 #review #auto-generated
---

# {first_day.strftime("%Y년 %m월")} 월간 리뷰

총 완료 작업: {len(completed_tasks)}개

---

## 이번 달 완료한 작업

"""

    # 프로젝트별 작업 추가
    for project, tasks in tasks_by_project.items():
        content += f"\n### {project} ({len(tasks)}개)\n\n"
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

## 다음 달 계획

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

    print(f"월간 리뷰 생성 완료: {review_file}")


def main():
    print("=" * 50)
    print("월간 회고 자동 생성 스크립트")
    print("=" * 50)

    # 이번 달 범위
    first_day, last_day = get_month_range()
    print(f"기간: {first_day.strftime('%Y-%m-%d')} ~ {last_day.strftime('%Y-%m-%d')}")

    # 할일 파일 찾기
    print("\n할일 파일 검색 중...")
    todo_files = find_todo_files(first_day, last_day)
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

    # 프로젝트별 통계
    print("\n프로젝트별 완료 작업:")
    project_counts = {}
    for task in all_completed_tasks:
        project = task['project']
        project_counts[project] = project_counts.get(project, 0) + 1

    for project, count in project_counts.items():
        print(f"  {project}: {count}개")

    # Ollama로 회고 생성
    print("\n" + "=" * 50)
    review_content = generate_review_with_ollama(all_completed_tasks)

    if review_content:
        print("\n생성된 회고:")
        print(review_content)

    # 월간 리뷰 파일 생성
    print("\n" + "=" * 50)
    create_monthly_review(all_completed_tasks, review_content)

    print("\n완료!")


if __name__ == "__main__":
    main()