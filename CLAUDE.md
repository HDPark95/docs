# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git Commit Guidelines

- **DO NOT** include Claude Code attribution in commit messages
- **DO NOT** add "Co-Authored-By: Claude" footer
- Write clean, professional commit messages without AI tool references
- Focus on what was changed and why, not who/what tool made the change

## Repository Overview

This is a personal knowledge management system combining PARA methodology with Zettelkasten note-taking. The repository contains software engineering study notes and concept explanations in Korean, organized for systematic learning and practical application.

## Architecture and Structure

### Dual Organization System

The repository uses two complementary organizational systems:

1. **PARA Method** (`PARA/`) - Action-oriented organization:
   - `1_Projects/`: Active projects with deadlines
   - `2_Areas/`: Ongoing responsibility areas (Spring, Database, Algorithm, etc.)
   - `3_Resources/`: Reference materials and learning resources
   - `4_Archives/`: Completed or inactive content

2. **Zettelkasten** (`Zettelkasten/`) - Knowledge-oriented organization:
   - `0_임시메모/`: Fleeting notes for quick idea capture
   - `1_문헌메모/`: Literature notes from books and sources
   - `2_영구메모/`: Permanent notes with atomic concepts

### Note ID and Linking System

- **Permanent Notes**: Use timestamp-based IDs (`202501211_캐시기본개념.md`)
- **Hierarchical IDs**: Branch concepts with letter suffixes (`202501211a_Look-Aside패턴.md`)
- **Links**: Use `[[ID]]` format for cross-references between notes
- **Tags**: Use `#태그` format for categorization

### Content Evolution Flow

```
임시메모 (fleeting) → 문헌메모 (literature) → 영구메모 (permanent) → PARA 프로젝트 적용
```

## Working with This Repository

### Content Guidelines

- All content written in Korean
- Do not use emojis in any documentation or markdown files
- Focus on practical application over theoretical concepts
- Include code examples and real-world implementation details
- Maintain atomic principle: one concept per permanent note
- Establish connections between related concepts through linking

### File Naming Conventions

- **Permanent notes**: `YYYYMMDDN_개념명.md` (where N is sequence number)
- **Literature notes**: Organized by source (e.g., `HTTP완벽분석/3장-Http메시지.md`)
- **PARA files**: Descriptive Korean names within appropriate categories

### Metadata Format

Each note should include YAML front matter:

```yaml
---
영구메모_ID: 202501211
생성일: 2025-01-21
태그: #캐시 #성능최적화
연결: [[202501211a_Look-Aside패턴]] [[202501211b_캐시키설계]]
---
```

### Knowledge Management Workflow

1. **Capture**: Quick ideas in `0_임시메모/`
2. **Process**: Weekly review to convert to literature or permanent notes
3. **Connect**: Link related concepts using `[[]]` syntax
4. **Apply**: Move actionable insights to PARA projects

### Fleeting Notes Creation

When the user provides keywords for fleeting notes:
- Create structured templates with the provided keywords only
- Do not add explanatory content or descriptions
- Focus on creating a framework that the user can fill in later
- Use consistent template structure with sections for ideas, technical considerations, next steps, and tags

**Important**: The value of this note-taking method comes from the user's own understanding and processing. If Claude fills in the content, it defeats the purpose of personal knowledge building and comprehension. Templates should remain empty for the user to fill based on their own learning and thinking process.

### Task Management with Project Todo Lists

When the user mentions tasks for specific projects, automatically add them to the corresponding project todo files:

- **Asyncsite tasks** (주 키워드: "어사", "Asyncsite", "asyncsite" / 프로젝트명: "쿼리데일리")
  → Add to latest file in `PARA/1_Projects/Asyncsite/` with `#어사` tag

- **Forbiz tasks** (주 키워드: "포비즈", "Forbiz", "포비스")
  → Add to latest file in `PARA/1_Projects/Forbiz/` with `#포비즈` tag

- **Personal tasks** (주 키워드: "개인", "Personal", "사이드프로젝트", "블로그")
  → Add to latest file in `PARA/1_Projects/Personal/` with `#개인` tag

- **잡다구리 tasks** (주 키워드: "잡다구리", "기타", "etc")
  → Add to latest file in `PARA/1_Projects/잡다구리/` with `#잡다구리` tag
  → Use for miscellaneous tasks that don't fit into specific projects

**Important**: Only trigger task addition when user explicitly mentions the project keyword (어사/포비즈/개인/잡다구리). Do not automatically infer project from context or sub-project names like "쿼리데일리" alone.

**Workflow**:
1. If no todo file exists for today (YYYY-MM-DD.md), create one from the template first
2. Add tasks to the appropriate section (백엔드/프론트엔드/운영/학습 etc.) based on task context
3. Always include the project tag and relevant category tag

**Format**: Add tasks to the appropriate section (백엔드/프론트엔드/운영/학습 etc.) based on task context. Always include the project tag.

**Examples**:
- User: "어사 쿼리데일리 멤버 도메인 설계해야해"
  → Action: Add `- [ ] 쿼리데일리 멤버 도메인 설계 #어사 #backend` to Asyncsite

- User: "쿼리데일리 멤버 도메인 설계해야해" (no project keyword)
  → Action: Do nothing (user didn't specify project)

- User: "포비즈 API 문서 업데이트"
  → Action: Add `- [ ] API 문서 업데이트 #포비즈 #development` to Forbiz

- User: "잡다구리 은행 서류 제출해야해"
  → Action: Add `- [ ] 은행 서류 제출 #잡다구리 #urgent` to 잡다구리

### Entry Points

- `README.md`: Overview and current status
- `INDEX.md`: Complete structure and navigation map
- `GUIDE.md`: Detailed usage instructions and workflows

The system emphasizes connected knowledge over isolated notes, enabling discovery of patterns and insights across different technical domains.