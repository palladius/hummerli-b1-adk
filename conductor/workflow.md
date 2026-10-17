# Project Workflow — Hummerli

## Guiding Principles

1. **The Plan is the Source of Truth:** All work must be tracked in `plan.md`.
2. **The Tech Stack is Deliberate:** Changes to the tech stack must be documented in `tech-stack.md` *before* implementation.
3. **Test- & Trajectory-Driven Development (TDD + TrDD):** Write unit tests AND ADK trajectory evaluations (`tests/evals/*.test.json` + trajectory assertions) before or alongside every agent/tool feature.
4. **High Code & Trajectory Coverage:** Aim for >80% unit code coverage and 100% expected tool trajectory coverage for all ADK agent flows.
5. **User Experience First:** Every decision prioritizes low-latency oral immersion and natural German B1 learning.
6. **Non-Interactive & CI-Aware:** Prefer non-interactive commands (`uv run pytest`).

---

## Task Workflow

All tasks follow a strict lifecycle:

### Standard Task Workflow

1. **Select Task:** Choose the next available task from `plan.md` in sequential order.
2. **Mark In Progress:** Before beginning work, edit `plan.md` and change the task from `[ ]` to `[~]`.
3. **Write Failing Tests & Trajectory Specs (Red Phase):**
   - For pure Python modules (e.g., SRS SM-2 math, curriculum parser): write unit tests in `tests/unit/`.
   - For ADK Agents & Tools (e.g., Frau Blücher, Rijckard Coach, SRS tool calls): define expected tool trajectories (`expected_tool_use`) in `tests/evals/*.test.json` and trajectory runner tests in `tests/evals/test_trajectories.py`.
   - **CRITICAL:** Run `uv run pytest` and confirm that the new tests fail as expected ("Red" phase).
4. **Implement to Pass Tests (Green Phase):**
   - Write the minimum application/agent code necessary to make both unit tests and trajectory evaluations pass.
   - Run `uv run pytest` to confirm all tests pass ("Green" phase).
5. **Refactor:**
   - Improve clarity, remove duplication, and enforce type hints (`ruff check`).
   - Rerun `uv run pytest` to verify everything remains green.
6. **Verify Coverage & Trajectory Scores:**
   - Run `uv run pytest --cov=hummerli --cov-report=term-missing`.
   - Verify trajectory evaluation assertions (`tool_trajectory_avg_score >= 0.85` or exact deterministic tool sequence match).
7. **Commit Code Changes:**
   - Stage changes and commit with a clear semantic commit message (`feat(srs): ...`, `eval(trajectory): ...`).
8. **Update Plan:**
   - Mark the task `[x]` in `plan.md` with the short commit SHA.

---

## 🛤️ ADK Trajectory Evaluation Protocol ("Evals Along the Way")

Every ADK agent capability MUST be accompanied by a trajectory evaluation test in `tests/evals/`:

1. **Tool Trajectory Verification (Deterministic & Offline-Capable):**
   - Tests that given a synthetic user turn (e.g., *"Starte eine neue Übung"*, *"Ich habe meinen Freund vom Bahnhof abgeholt"*, or *"Non ho capito cosa significa abholen"*), the agent invokes the exact expected sequence of tools (`get_due_words`, `record_word_attempt`, `delegate_to_rijckard`, `file_eval_issue`) with valid arguments.
2. **ADK Native `.test.json` / `.evalset.json` Compatibility:**
   - Trajectory fixtures follow the Google ADK evaluation schema (`query`, `expected_tool_use`, `expected_intermediate_agent_responses`, `reference`) so they can be executed both via fast deterministic mock/replay in `pytest` AND via `adk eval` / `AgentEvaluator.evaluate()` against live Gemini models.
3. **Judge & Bug-Router Verification:**
   - The LLM-as-Judge evaluator itself is tested against known "good" and "bad" trajectories (e.g., tutor speaking English instead of German, tutor forgetting to call `record_word_attempt`, tutor making a false grammar correction) to ensure it accurately classifies root causes (`harness` vs `skill` vs `model`) and routes bug reports to the right repo (`hummerli-b1-adk` vs `hummerli-b1-adk-pvt`).

---

## Development Commands

### Setup
```bash
uv sync --all-extras
```

### Daily Development & Evals
```bash
# Run all unit and trajectory eval tests (fast deterministic mode)
uv run pytest

# Run trajectory evaluations with coverage
uv run pytest --cov=hummerli --cov-report=term-missing

# Run live ADK AgentEvaluator against Gemini API (requires GOOGLE_API_KEY)
HUMMERLI_LIVE_EVAL=1 uv run pytest tests/evals/ -m live_eval

# Lint & format check
uv run ruff check .
```

---

## Quality Gates

Before marking any task or phase complete, verify:
- [ ] All unit tests pass (`uv run pytest tests/unit`)
- [ ] All trajectory evaluation tests pass (`uv run pytest tests/evals`)
- [ ] Code coverage meets requirements (>80%)
- [ ] Code follows `conductor/code_styleguides/python.md`
- [ ] No secrets or personal data staged (`git status` checked against `.gitignore`)
