---
생성일: 2025-10-11
태그: #아키텍처 #문서화 #다이어그램 #C4모델 #Structurizr
상태: 임시메모
---

# C4 다이어그램과 Structurizr DSL 자동화

## 개요

Spring Boot 프로젝트의 아키텍처를 C4 모델 기반 Structurizr DSL로 자동 생성하는 시스템

### 핵심 가치

**살아있는 문서 (Living Documentation)**
- 코드 변경 시 다이어그램 자동 업데이트
- Git 히스토리로 아키텍처 진화 추적
- 항상 최신 상태 유지

**자동화 워크플로우**
- Git hook 기반 (post-commit, post-merge)
- LLM 활용 (Ollama qwen2.5-coder:7b)
- LangGraph 품질 보장 파이프라인

## 기술 스택

### C4 Model
- Level 1: System Context (시스템과 외부 의존성)
- Level 2: Container (배포 단위)
- Level 3: Component (코드 수준 그룹)
- Level 4: Code (클래스 다이어그램)

### 도구
- **Structurizr Lite**: 로컬 시각화 서버 (포트 8080)
- **Structurizr CLI**: PNG/SVG 이미지 생성
- **Ollama**: 로컬 LLM 런타임 (무료)
- **LangGraph**: 품질 보장 워크플로우

## 환경 설정

### 1. 필수 도구 설치

```bash
# Java 17+
java -version

# Ollama
brew install ollama
ollama pull qwen2.5-coder:7b

# Python 패키지
pip install langgraph langchain-community ollama
```

### 2. 디렉토리 구조

```
project/
├── docs/
│   └── architecture/
│       └── workspace.dsl        # 생성된 DSL
├── scripts/
│   └── generate_arch_langgraph.py
├── .git/
│   └── hooks/
│       └── post-commit          # Git hook
└── src/                         # Java 소스
```

### 3. Structurizr 도구 다운로드

```bash
mkdir -p ~/tools/structurizr
cd ~/tools/structurizr

# Structurizr Lite
wget https://github.com/structurizr/lite/releases/latest/download/structurizr-lite.war

# Structurizr CLI
wget https://github.com/structurizr/cli/releases/latest/download/structurizr-cli.zip
unzip structurizr-cli.zip
```

## LangGraph 워크플로우

### 아키텍처

```
코드 분석 → 아키텍처 설계 → DSL 생성 → 검증
                                    ↓ (invalid & iterations < 3)
                                   수정 → 검증 (retry)
                                    ↓ (valid | iterations >= 3)
                                 최종 DSL
```

### 6개 노드

1. **analyze_code**: Java 파일 분석 (Controller/Service/Repository)
2. **design_architecture**: C4 모델 아키텍처 설계
3. **generate_dsl**: Structurizr DSL 생성
4. **validate_dsl**: 5단계 검증 체크리스트
5. **fix_dsl**: 오류 수정
6. **finalize**: 최종 DSL 출력

### 검증 체크리스트

1. **Syntax Validation** (필수)
   - workspace/model/views 블록 존재
   - 브레이스 위치 규칙
   - 전방 참조 없음
   - 문자열 인용 규칙

2. **Uniqueness Validation** (필수)
   - Software system 이름 unique
   - Person 이름 unique
   - Container 이름 unique (시스템 내)
   - Component 이름 unique (컨테이너 내)
   - View key unique

3. **Structural Validation**
   - 요소 정의 후 관계 정의
   - Container는 softwareSystem 내부에만
   - Component는 container 내부에만
   - 모든 container에 기술 스택 명시

4. **Best Practice Validation**
   - 외부 시스템 내부 구현 숨김
   - 단일 메시지 버스 모델링 지양
   - 정의되지 않은 추상화 레벨 없음
   - 의미 있는 설명 포함

5. **Quality Checks**
   - 명확하고 목적 지향적 설명
   - 일관된 명명 규칙
   - 적절한 상세도
   - C4 모델 추상화 올바른 사용

### 실제 경험에서 발견된 오류 패턴

**1. Component 중첩 오류**
```dsl
# 잘못된 예
container = container "App" {
    component = component "Controllers" {
        orderController = component "OrderController"  # 오류!
    }
}

# 올바른 예
container = container "App" {
    orderController = component "OrderController" "..." "Spring MVC"
    userController = component "UserController" "..." "Spring MVC"
}
```

**2. Component에서 External System으로 직접 관계**
```dsl
# 잘못된 예
emailService -> emailSystem "Sends" "SMTP"  # component -> external (오류!)

# 올바른 예
webApp -> emailSystem "Sends" "SMTP"  # container -> external (정상)
```

**3. Component에서 Container로 관계**
```dsl
# 잘못된 예
orderService -> database "Queries"  # component -> container (오류!)

# 올바른 예
orderService -> orderRepository "Uses"  # component -> component
webApp -> database "Queries" "JDBC"  # container -> container
```

**4. Container가 softwareSystem 밖에 선언**
```dsl
# 잘못된 예
workspace "X" {
    model {
        system = softwareSystem "Main"
        webApp = container "Web" "..." "Spring"  # model 직접 하위 (오류!)
    }
}

# 올바른 예
workspace "X" {
    model {
        system = softwareSystem "Main" {
            webApp = container "Web" "..." "Spring"  # softwareSystem 내부 (정상)
        }
    }
}
```

### 검증 규칙 강화 사항

**Structural Validation 추가**:
- Components CANNOT be nested
- Components must be inside container
- All components at same nesting level

**Relationship Validation 추가**:
- Component → Component (same container): 허용
- Container → External System: 허용
- Component → External System: 금지
- Component → Container: 금지

## 구현 코드

### scripts/generate_arch_langgraph.py

```python
#!/usr/bin/env python3
from langgraph.graph import Graph, END
from langchain_community.llms import Ollama
from pathlib import Path
from typing import TypedDict
import json

class State(TypedDict):
    code_files: list
    analysis: str
    design: str
    dsl: str
    validation_result: dict
    iterations: int
    final_dsl: str

llm = Ollama(model="qwen2.5-coder:7b", temperature=0)

# ========================================
# 시스템 프롬프트
# ========================================

GENERATE_DSL_PROMPT = """
You are an expert Structurizr DSL architect. Generate a high-quality workspace.dsl file.

CRITICAL REQUIREMENTS:
1. Syntax Rules (MUST follow):
   - Lines processed sequentially, NO forward references
   - Opening braces MUST be on same line as statement
   - Closing braces on their own line
   - Use double quotes for multi-word strings
   - Keywords are case-insensitive

2. Naming Conventions (MUST be unique):
   - Software system names: UNIQUE across workspace
   - Person names: UNIQUE across workspace
   - Container names: UNIQUE within same software system
   - Component names: UNIQUE within same container
   - Use meaningful, descriptive names

3. Relationship Rules:
   - Syntax: element -> element "description" "technology"
   - Descriptions MUST be unique between same source/destination
   - Clearly state the purpose/action

4. Required Structure:
workspace "name" "description" {{
    model {{
        person = person "name" "description"
        system = softwareSystem "name" "description" {{
            container = container "name" "description" "technology"
        }}
        person -> system "description"
    }}
    views {{
        systemContext system "key" {{
            include *
            autoLayout
        }}
        container system "key" {{
            include *
            autoLayout
        }}
    }}
}}

5. AVOID Anti-Patterns:
   - Showing internal details of external systems
   - Modeling single message bus
   - Creating undefined abstraction levels
   - Mixing container and component abstractions
   - Too much text causing visual clutter

6. FOLLOW Best Practices:
   - Containers = deployable units
   - Components = code-level groupings
   - Use tags for styling
   - Include technology stack information
   - Add meaningful descriptions
   - Use autoLayout

ARCHITECTURE DESIGN:
{design}

Generate ONLY the complete DSL code, NO explanations, NO markdown blocks.
Start directly with: workspace "..." {{
"""

VALIDATE_DSL_PROMPT = """
You are a Structurizr DSL validator. Analyze the DSL for errors and quality issues.

VALIDATION CHECKLIST:

1. Syntax Validation (CRITICAL):
   - workspace block exists and properly formatted
   - model block exists
   - views block exists
   - All opening braces on same line as statement
   - All closing braces on their own line
   - No forward references
   - Proper string quoting

2. Uniqueness Validation (CRITICAL):
   - All software system names unique
   - All person names unique
   - Container names unique within system
   - Component names unique within container
   - View keys unique
   - Relationship descriptions unique per source-destination

3. Structural Validation:
   - Elements defined before relationships
   - Containers only inside softwareSystem
   - Components only inside container
   - Technology specified for all containers

4. Best Practice Validation:
   - No internal details of external systems
   - No single message bus modeling
   - Meaningful descriptions provided
   - Technology stack clearly specified

5. Quality Checks:
   - Clear and purposeful descriptions
   - Consistent naming
   - Appropriate detail level
   - Proper C4 abstractions

DSL TO VALIDATE:
{dsl}

Respond in JSON format:
{{{{
    "is_valid": true/false,
    "errors": [
        {{{{"type": "syntax|uniqueness|structure|practice|quality", "message": "..."}}}},
    ],
    "warnings": [
        {{{{"message": "...", "suggestion": "..."}}}},
    ],
    "quality_score": 0-100
}}}}
"""

FIX_DSL_PROMPT = """
You are a Structurizr DSL repair specialist. Fix the errors in the DSL.

ORIGINAL DSL:
{dsl}

VALIDATION ERRORS:
{errors}

REPAIR INSTRUCTIONS:
1. Address ALL errors listed above
2. Maintain the original architecture intent
3. Follow all Structurizr DSL syntax rules strictly
4. Preserve all working parts
5. Ensure uniqueness of all names
6. Fix structural issues (braces, order, nesting)

DO NOT:
- Remove essential elements
- Change the fundamental architecture
- Add features not in original design
- Create new errors while fixing old ones

Generate the COMPLETE CORRECTED DSL, NO explanations.
Start directly with: workspace "..." {{
"""

# ========================================
# 노드 함수
# ========================================

def analyze_code(state: State) -> State:
    code_samples = "\n\n".join(state["code_files"])

    analysis_prompt = f"""
Analyze this Java Spring Boot code and identify:
- All REST Controllers (endpoints)
- All Services (business logic)
- All Repositories (data access)
- External dependencies (databases, APIs, message queues)
- Inter-service communication patterns

Code:
{code_samples}

Provide structured analysis in this format:
Controllers: [list]
Services: [list]
Repositories: [list]
External Systems: [list]
Communication: [description]
"""

    analysis = llm.invoke(analysis_prompt)
    return {**state, "analysis": analysis}

def design_architecture(state: State) -> State:
    analysis = state["analysis"]

    design_prompt = f"""
Based on this code analysis, design a C4 model architecture:

{analysis}

Create a clear architecture design with:
1. Software System name and purpose
2. Containers (deployable units) with technologies
3. Key components within containers
4. Relationships and data flow
5. External systems and integrations

Use C4 model abstractions correctly:
- Container = deployable/runnable unit
- Component = code-level grouping
"""

    design = llm.invoke(design_prompt)
    return {**state, "design": design}

def generate_dsl(state: State) -> State:
    design = state["design"]
    prompt = GENERATE_DSL_PROMPT.format(design=design)
    response = llm.invoke(prompt)

    dsl = response.strip()
    if "```" in dsl:
        dsl = dsl.split("```")[1]
        if dsl.startswith("dsl"):
            dsl = dsl[3:].strip()

    return {**state, "dsl": dsl}

def validate_dsl(state: State) -> State:
    dsl = state["dsl"]
    prompt = VALIDATE_DSL_PROMPT.format(dsl=dsl)
    response = llm.invoke(prompt)

    try:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        else:
            json_str = response.strip()
        validation_result = json.loads(json_str)
    except:
        validation_result = {
            "is_valid": False,
            "errors": [{"type": "parsing", "message": "Validation parsing failed"}],
            "warnings": [],
            "quality_score": 0
        }

    return {**state, "validation_result": validation_result}

def fix_dsl(state: State) -> State:
    dsl = state["dsl"]
    errors = state["validation_result"]["errors"]
    iterations = state["iterations"] + 1

    errors_text = "\n".join([f"- {err['type']}: {err['message']}" for err in errors])
    prompt = FIX_DSL_PROMPT.format(dsl=dsl, errors=errors_text)
    response = llm.invoke(prompt)

    fixed_dsl = response.strip()
    if "```" in fixed_dsl:
        fixed_dsl = fixed_dsl.split("```")[1]
        if fixed_dsl.startswith("dsl"):
            fixed_dsl = fixed_dsl[3:].strip()

    return {**state, "dsl": fixed_dsl, "iterations": iterations}

def finalize(state: State) -> State:
    final_dsl = state["dsl"]
    quality = state["validation_result"].get("quality_score", 0)

    print(f"최종 DSL 품질 점수: {quality}/100")
    print(f"총 재시도 횟수: {state['iterations']}")

    return {**state, "final_dsl": final_dsl}

# ========================================
# 조건부 라우팅
# ========================================

def should_fix(state: State) -> str:
    if state["validation_result"]["is_valid"]:
        return "finalize"
    elif state["iterations"] < 3:
        return "fix"
    else:
        print("최대 재시도 횟수 도달. 현재 상태로 종료합니다.")
        return "finalize"

# ========================================
# 그래프 구성
# ========================================

workflow = Graph()

workflow.add_node("analyze", analyze_code)
workflow.add_node("design", design_architecture)
workflow.add_node("generate", generate_dsl)
workflow.add_node("validate", validate_dsl)
workflow.add_node("fix", fix_dsl)
workflow.add_node("finalize", finalize)

workflow.add_edge("analyze", "design")
workflow.add_edge("design", "generate")
workflow.add_edge("generate", "validate")
workflow.add_conditional_edges(
    "validate",
    should_fix,
    {
        "fix": "fix",
        "finalize": "finalize"
    }
)
workflow.add_edge("fix", "validate")
workflow.add_edge("finalize", END)

workflow.set_entry_point("analyze")

# ========================================
# 메인 실행
# ========================================

def main():
    print("고품질 DSL 생성 시작...")

    # Java 파일 읽기
    java_files = []
    for file in Path('src').rglob('*.java'):
        if any(x in file.name for x in ['Controller', 'Service', 'Repository']):
            with open(file) as f:
                content = f.read()[:800]
                java_files.append(f"=== {file.name} ===\n{content}")

    if not java_files:
        print("Java 파일을 찾을 수 없습니다.")
        return

    # 워크플로우 실행
    app = workflow.compile()

    result = app.invoke({
        "code_files": java_files[:10],
        "iterations": 0
    })

    # DSL 저장
    dsl = result["final_dsl"]
    output_dir = Path("docs/architecture")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "workspace.dsl"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(dsl)

    print(f"DSL 생성 완료: {output_file}")
    print(f"품질 점수: {result['validation_result'].get('quality_score', 'N/A')}/100")
    print(f"재시도 횟수: {result['iterations']}")

    # 경고 출력
    warnings = result['validation_result'].get('warnings', [])
    if warnings:
        print("\n경고사항:")
        for w in warnings:
            print(f"   - {w['message']}")
            if 'suggestion' in w:
                print(f"     제안: {w['suggestion']}")

if __name__ == '__main__':
    main()
```

### .git/hooks/post-commit

```bash
#!/bin/bash

if git diff HEAD~1 --name-only | grep -q "\.java$"; then
    echo "Java 파일 변경 감지 - DSL 업데이트 시작..."

    # 고품질 DSL 생성
    python3 scripts/generate_arch_langgraph.py

    # Structurizr Lite 실행
    if ! lsof -ti:8080 > /dev/null; then
        echo "Structurizr Lite 시작..."
        java -jar ~/tools/structurizr/structurizr-lite.war docs/architecture &
        sleep 3
        open http://localhost:8080
    else
        echo "Structurizr Lite 이미 실행 중 - 새로고침하세요"
    fi

    echo "아키텍처 다이어그램 업데이트 완료"
fi
```

### 실행 권한 부여

```bash
chmod +x .git/hooks/post-commit
chmod +x scripts/generate_arch_langgraph.py
```

## 사용 방법

### 초기 DSL 생성

```bash
python3 scripts/generate_arch_langgraph.py
```

### Structurizr Lite 시작

```bash
java -jar ~/tools/structurizr/structurizr-lite.war docs/architecture
open http://localhost:8080
```

### 이미지 내보내기

```bash
cd ~/tools/structurizr/structurizr-cli
./structurizr.sh export -workspace /path/to/docs/architecture/workspace.dsl -format png
```

## 품질 보장

### LangGraph vs LangChain 비교

| 항목 | LangChain | LangGraph |
|-----|-----------|-----------|
| 복잡도 | 낮음 | 높음 |
| 품질 보장 | 2점 | 5점 |
| 재시도 로직 | 어려움 | 쉬움 |
| 조건부 분기 | 복잡 | 간단 |
| 디버깅 | 보통 | 쉬움 |
| 학습 곡선 | 쉬움 | 어려움 |
| 실행 시간 | 빠름 | 느림 (재시도 포함) |

**선택**: 완성도 우선 LangGraph

### 기대 효과

| 지표 | 단순 프롬프트 | 시스템 프롬프트 |
|-----|------------|----------------|
| 문법 오류율 | 약 30% | 약 5% |
| 완성도 | 2점 | 5점 |
| 재생성 필요 | 자주 | 드물게 |
| 품질 일관성 | 낮음 | 높음 |
| 유지보수성 | 어려움 | 쉬움 |
| 실행 시간 | 30초 | 2-3분 |

## 핵심 개선점

1. **웹 리서치 기반**: 공식 문서 + 커뮤니티 베스트 프랙티스 통합
2. **검증 루프**: 자동 오류 감지 및 수정 (최대 3회)
3. **품질 점수**: 정량적 평가 및 개선 추적
4. **구조화된 출력**: JSON 기반 명확한 오류/경고 분류

## 연결될 수 있는 개념

- Living Documentation
- Documentation as Code
- Architecture Decision Records (ADR)
- CI/CD Pipeline Integration
- Git Hooks
- LLM Agent Workflows
- Multi-Agent Systems
