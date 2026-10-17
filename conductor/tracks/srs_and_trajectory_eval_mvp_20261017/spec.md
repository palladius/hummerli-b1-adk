# Specification: Core ADK Tutor, Goethe B1 SRS Engine & Trajectory Evaluation Harness

## 1. Overview

This track implements the foundational core of **Hummerli**:
1. **Multi-Profile & Goethe B1 Wortliste Curriculum Engine**: Structured B1 vocabulary dataset (verbs, nouns, adjectives relevant to Zurich naturalization / FIDE exam and daily life) plus profile configurations for `riccardo` (B1), `ale` (P3 A1-A2), and `sebi` (P1 Early Immersion).
2. **SuperMemo SM-2 / Leitner SRS Engine**: Tracks word mastery (`repetition_count`, `ease_factor`, `interval_days`, `next_review_due`, `last_score`, history of comments/scores), scheduling mastered words at expanding intervals (1, 7, 15, 30, 90 days) and failed words (`q < 3`) for immediate reinforcement.
3. **Google ADK Dual-Persona Agent System**:
   - **Frau Leonie Blücher 🐎** (`frau_bluecher`): Primary German B1 tutor agent (`LlmAgent`) equipped with SRS and profile tools (`get_profile_context`, `get_due_words`, `record_word_attempt`).
   - **Rijckard Coach** (`rijckard_coach`): Italian coach sub-agent/tool (`explain_in_italian`) invoked exclusively when the user signals confusion (*"Non ho capito"*, *"Wie bitte?"*, or explicit Italian/English grammar questions).
4. **Two-Level Trajectory Evaluation Harness & Closed-Loop Bug Router ("Evals Along the Way")**:
   - **Level 1 (Harness / Tool Trajectory Evals)**: ADK `.test.json` / `.evalset.json` trajectory fixtures and deterministic evaluator verifying exact tool call sequences (`tool_trajectory_avg_score`), argument correctness, and agent state transitions.
   - **Level 2 (Pedagogical & Harness Judge + Dual-Repo Bug Router)**: Automated judge analyzing session trajectories for both **Harness errors** (missing tool call, wrong tool args, infinite loop) and **Pedagogical errors** (wrong language, false grammar correction, out-of-scope C1/C2 vocabulary, vague feedback), generating daily Markdown digests and routing bug reports to `palladius/hummerli-b1-adk` (public harness bugs) or `palladius/hummerli-b1-adk-pvt` (private transcript/model bugs).
5. **CLI Interface (`hummerli`)**: Commands to inspect SRS status, run interactive/simulated sessions, execute trajectory evals, and generate daily evaluation digests.

---

## 2. Functional Requirements

### FR1: Curriculum & Multi-Profile Management
- Load profile configurations (`riccardo`, `ale`, `sebi`) from YAML/JSON with target language, support language, strictness, speed, and topic list.
- Load and query the Goethe B1 Wortliste curriculum (`data/curricula/goethe_b1.json`) containing structured entries (`lemma`, `pos`, `article`, `plural`, `example_de`, `translation_it`, `topic`, `cefr_level`).

### FR2: Spaced Repetition (SRS) Engine
- Implement SM-2 algorithm tailored to Riccardo's spec:
  - Scores $q \in \{0, 1, 2, 3, 4, 5\}$.
  - Quality $q \ge 3$ (pass): increments repetition count, updates ease factor $EF' = \max(1.3, EF + (0.1 - (5 - q) \cdot (0.08 + (5 - q) \cdot 0.02)))$, and progresses interval through milestone buckets (1d → 7d → 15d → 30d → 90d+).
  - Quality $q < 3$ (fail): resets repetition count to 0 and schedules interval to 0/1 day so *"la lingua batte dove il dente duole"*.
- Persist and reload per-user state from `data/users/{profile_id}/srs_state.json`.
- Select top $k$ (default 1–3) due/struggling words for a new session.

### FR3: ADK Agents & Tools
- Expose ADK-compatible tool functions with full type annotations and docstrings:
  - `get_profile_context(profile_id: str) -> dict`
  - `get_due_words(profile_id: str, limit: int = 3) -> list[dict]`
  - `record_word_attempt(profile_id: str, lemma: str, quality: int, user_sentence: str, tutor_comment: str, used_actively: bool = True) -> dict`
  - `explain_in_italian(concept_or_phrase: str, user_question: str) -> dict`
- Construct ADK `Agent` / `LlmAgent` hierarchy (`hummerli_root_agent` / `frau_bluecher` + `rijckard_coach`).

### FR4: Trajectory Evaluation & Closed-Loop Bug Filing
- Define standard ADK trajectory test files in `tests/evals/trajectories/`:
  - `session_init_b1.test.json`: Verifies agent fetches profile and due B1 words before starting conversation.
  - `word_mastery_abholen.test.json`: Verifies agent records attempt when user correctly uses *"abholen"* in a sentence.
  - `coach_handoff_non_ho_capito.test.json`: Verifies agent calls `explain_in_italian` when user says *"Non ho capito"*, then resumes German practice.
- Implement `TrajectoryEvaluator` computing `tool_trajectory_score` (exact match, prefix match, and set match) and `JudgeAnalyzer` detecting harness vs. pedagogical errors.
- Implement `BugRouter` that formats evidence-backed GitHub Issues and routes:
  - `category == "harness"` (no PII) → `palladius/hummerli-b1-adk`
  - `category in ("skill", "model", "pedagogical")` or `has_personal_data == True` → `palladius/hummerli-b1-adk-pvt`

---

## 3. Acceptance Criteria

- [ ] `uv run pytest` executes both unit tests (`tests/unit/`) and trajectory evaluation suites (`tests/evals/`) with 100% pass rate and >85% code coverage.
- [ ] ADK trajectory fixtures (`tests/evals/trajectories/*.test.json`) validate all 4 core conversational & tool-use trajectories.
- [ ] `JudgeAnalyzer` accurately catches injected trajectory failures (missing tool call, wrong language, false grammar correction) and routes the resulting bug payload to the correct public or private repository.
- [ ] CLI (`uv run hummerli`) supports `srs`, `eval`, and `digest` commands cleanly.
