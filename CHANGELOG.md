# Changelog

All notable changes to **Hummerli** (`hummerli-b1-adk`) are documented in this file.

## [0.1.0] - 2026-10-17

### Added
- Initialized Conductor Spec-Driven Development (`conductor/`) and Dual-Repo architecture (`palladius/hummerli-b1-adk` + private `palladius/hummerli-b1-adk-pvt`).
- Multi-profile curriculum engine (`riccardo` Goethe B1 Wortliste, `ale` Tandem P3, `sebi` Tandem P1).
- SuperMemo SM-2 / Leitner Spaced Repetition (SRS) engine with expanding intervals (1d, 7d, 15d, 30d, 90d) and struggling-word reinforcement.
- Google ADK dual-persona agent orchestration: **Frau Leonie Blücher 🐎** (German B1 Tutor) and **Rijckard** (Italian Coach on *"Non ho capito"*).
- Two-Level Trajectory Evaluation Harness (`tests/evals/` & `hummerli.eval`):
  - Level 1: ADK `.test.json` / `.evalset.json` deterministic tool trajectory evaluator (`tool_trajectory_avg_score`).
  - Level 2: LLM-as-Judge trajectory & pedagogical analyzer with automatic dual-repo GitHub Issue routing and daily Markdown digest generator.
- `hummerli` CLI (`srs`, `eval`, `digest`, `simulate`).
