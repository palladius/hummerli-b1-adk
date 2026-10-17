# Implementation Plan: Core ADK Tutor, Goethe B1 SRS Engine & Trajectory Evaluation Harness

## Phase 1: Project Scaffolding, Multi-Profile Config & Goethe B1 Curriculum
- [x] Task 1.1: Initialize Python package structure (`pyproject.toml`, `src/hummerli/__init__.py`, `README.md`) with `google-adk`, `pydantic`, `typer`, `rich`, `pyyaml`, `pytest`, `pytest-asyncio`, `pytest-cov`.
- [x] Task 1.2: Write failing unit tests (`tests/unit/test_curriculum_and_profiles.py`) for Goethe B1 Wortliste loading, filtering by POS/topic, and multi-profile configuration (`riccardo`, `ale`, `sebi`).
- [x] Task 1.3: Create curated Goethe B1 Wortliste dataset (`data/curricula/goethe_b1.json` + Tandem P3/P1 seeds) and implement `hummerli.curriculum` and `hummerli.profiles`.

## Phase 2: SuperMemo SM-2 / Leitner Spaced Repetition (SRS) Engine
- [x] Task 2.1: Write failing unit tests (`tests/unit/test_srs_engine.py`) covering SM-2 math ($q=0..5$), interval progression (1d → 7d → 15d → 30d → 90d), struggling word prioritization, and JSON state persistence.
- [x] Task 2.2: Implement `hummerli.srs` (`SRSCard`, `AttemptRecord`, `SRSEngine`) to pass all SRS unit tests.

## Phase 3: Google ADK Dual-Persona Agents & Tools (Frau Blücher & Rijckard)
- [x] Task 3.1: Write failing unit & tool-contract tests (`tests/unit/test_adk_tools.py`) for `get_profile_context`, `get_due_words`, `record_word_attempt`, and `explain_in_italian`.
- [x] Task 3.2: Implement ADK tools (`hummerli.tools`) and ADK agent definitions (`hummerli.agent` with `frau_bluecher`, `rijckard_coach`, and `root_agent`).

## Phase 4: Two-Level Trajectory Evaluation Harness & Dual-Repo Bug Router ("Evals Along the Way")
- [x] Task 4.1: Create ADK `.test.json` trajectory evaluation fixtures in `tests/evals/trajectories/` (`session_init_b1.test.json`, `word_mastery_abholen.test.json`, `coach_handoff_non_ho_capito.test.json`, `struggling_word_retry.test.json`).
- [x] Task 4.2: Write failing trajectory evaluation tests (`tests/evals/test_trajectories.py`) and judge/bug-routing tests (`tests/evals/test_judge_and_bug_router.py`).
- [x] Task 4.3: Implement `hummerli.eval.trajectory` (`TrajectoryEvaluator`, ADK `.test.json` loader, deterministic trajectory runner & scorer) and `hummerli.eval.judge` (`JudgeAnalyzer`, `BugRouter` for public `hummerli-b1-adk` vs private `hummerli-b1-adk-pvt`, and Daily Digest generator).

## Phase 5: CLI Interface & End-to-End Verification
- [x] Task 5.1: Write CLI tests (`tests/unit/test_cli.py`) and implement `hummerli.cli` (`srs`, `eval`, `digest`, `simulate`).
- [x] Task 5.2: Run full test & trajectory evaluation suite (`PYTHONPATH=src .venv/bin/pytest`) and commit track completion.
