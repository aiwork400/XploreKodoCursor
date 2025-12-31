# Development Guidelines - ExploraKodo Platform

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Tech Stack](#architecture--tech-stack)
3. [The Developer Manifesto (SOP)](#the-developer-manifesto-sop)
4. [Project Structure](#project-structure)
5. [Coding Standards & Safety](#coding-standards--safety)
6. [Database Conventions](#database-conventions)
7. [API Conventions](#api-conventions)
8. [UI/UX & All-in-One Shop Guidelines](#uiux--all-in-one-shop-guidelines)
9. [Environment Setup](#environment-setup)
10. [Git Workflow & Sandbox Protocol](#git-workflow--sandbox-protocol)
11. [Common Pitfalls & Solutions](#common-pitfalls--solutions)

---

## 1. Project Overview
**ExploraKodo** is a trilingual (English, Japanese, Nepali) Agentic AI (AAI) training platform. 
- **Core Mission**: Replace static 2-PDF teaching materials with dynamic, LLM-backed Socratic Conversations.
- **Key Constraints**: 180s video-to-chat timer and 3,000-word response buffers for competency grading.

---

## 2. Architecture & Tech Stack
- **Backend**: FastAPI (`api/main.py`) | **Frontend**: Streamlit (`dashboard/app.py`)
- **Agent Framework**: Agency Swarm | **LLM**: Google Gemini 2.0 Flash
- **Database**: PostgreSQL (SQLAlchemy)

---

## 3. The Developer Manifesto (SOP)
*This section governs all AI Agent interactions (Cursor, Claude, Gemini CLI).*

1. **Impact Assessment First**: Before any major code change, the Agent must provide a "Change Impact Analysis."
2. **Atomic Instructions**: Break complex features into sub-instructions. Do not modify the UI and Backend logic in a single turn.
3. **The Sandbox Rule**: Complex logic or new workflows must be developed in a standalone file (e.g., `tests/sandbox_feature.py`) and verified before merging into `app.py`.
4. **Single Source of Truth**: All data (translations, Pydantic rules, mastery logic) must originate from centralized modules, never hard-coded in the UI.

---

## 4. Project Structure
*(Standard directory structure as previously defined...)*

---

## 5. Coding Standards & Safety

### String Safety (The "Triple Quote" Rule)
To avoid the `SyntaxError` issues encountered during project stabilization:
- **Avoid** raw triple-quoted f-strings for user inputs.
- **Use** the `!r` format specifier: `f"User said: {user_input!r}"`.
- **Prefer** building prompts as lists and joining them: `"\n".join(prompt_parts)`.

### Error Handling
- **No Naked Excepts**: Every `try` block must have a specific `except Exception as e:` with `st.error` or logging.
- **Indentation Integrity**: Ensure `except` and `finally` blocks are at the exact same indentation level as their `try` statement.

---

## 8. UI/UX & All-in-One Shop Guidelines

### Video Hub & Socratic Shift
- **Timer Protocol**: At the 180s mark of video playback, the UI must trigger the `Socratic_Questioning_Tool`.
- **Word Limits**: Text areas for candidate responses must display a "Word Count" and enforce a 3,000-word buffer.
- **Centering**: Since `use_container_width` is version-restricted, use `st.columns([1, 6, 1])` for all video and primary chat elements.

---

## 10. Git Workflow & Sandbox Protocol

### Sandbox Testing Workflow
1. **Create Sandbox**: Agent creates `agency/sandbox_[feature].py`.
2. **Execute & Verify**: User runs the sandbox file to verify logic.
3. **Impact Review**: Agent explains how this will be integrated into the main `app.py`.
4. **Final Integration**: Only upon explicit approval is the code moved to the main branch.

### Commit Standards
- Use types: `feat:`, `fix:`, `refactor:`, `docs:`.
- Example: `feat(socratic): implement 180s timer trigger in video hub`

---

## 11. Common Pitfalls & Solutions
- **Plotly**: Use `colorbar=dict(title=dict(text='...', side='right'))`. **Do not** use `titleside`.
- **Uvicorn**: Ensure launch from root: `uvicorn api.main:app --reload`.
- **Language Switch**: Ensure `st.session_state.language` is updated before re-rendering video components.

**Last Updated**: 2025-12-31 (Project Baseline Reset)