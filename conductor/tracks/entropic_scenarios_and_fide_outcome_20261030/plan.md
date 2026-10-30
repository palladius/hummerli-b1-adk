# Implementation Plan: AI Entropic Visual Scenarios (Zero-Click + Italian Director Override) & Outcome-Based FIDE B1 Exam Rubric

## Phase 1: Entropic Scenario Engine & Client Layout Auto-Detection (`1:1` Mobile vs `16:9` Desktop)
- [ ] Task 1.1: Write failing unit tests (`tests/unit/test_scenarios.py`) for `EntropicScenario`, `ScenarioGenerator`, 3-card zero-click batch generation, SRS `due_words` binding, and `mobile_portrait` (`1:1`) vs `desktop_landscape` (`16:9`) aspect ratio selection.
  - [ ] Test that `generate_entropic_scenarios(profile_id="riccardo", count=3, client_layout="mobile_portrait")` returns 3 distinct Zurich scenarios with `aspect_ratio == "1:1"`, `test_events` questions, and `target_words` matching SRS `due_words`.
  - [ ] Test that `client_layout="desktop_landscape"` produces `aspect_ratio == "16:9"` and widescreen visual assets.
- [ ] Task 1.2: Implement `src/hummerli/scenarios.py` (`EntropicScenario`, `ScenarioGenerator`, Gemini Image API integration with deterministic SVG/Data-URI fallback and local disk cache in `data/scenarios_cache/`).
- [ ] Task 1.3: Phase Verification & Checkpoint (Refer to `workflow.md`).

## Phase 2: "Regia in Italiano" Live Director Override & ADK Tool Integration
- [ ] Task 2.1: Write failing unit & ADK tool tests in `tests/unit/test_scenarios.py` for `mutate_scenario_with_director_notes` (e.g., *"Sì ma voglio ristorante indiano, invece di italiano e la tizia è molto maleducata con me"*).
  - [ ] Verify that the mutated scenario changes location/cuisine (*Indisches Restaurant*), updates `interlocutor_mood` (*unhöflich / genervt*), generates a new visual asset, and **strictly preserves** the 3 SRS `target_words`.
- [ ] Task 2.2: Register `generate_entropic_scenarios` and `mutate_scenario_with_director_notes` on `HummerliToolset` (`src/hummerli/tools.py`) and `HummerliAgent` (`src/hummerli/agent.py`), including automatic detection of Italian director steering commands.
- [ ] Task 2.3: Phase Verification & Checkpoint (Refer to `workflow.md`).

## Phase 3: Outcome-Based FIDE B1 Exam Rubric & A2UI v0.9 Widget Extensions
- [ ] Task 3.1: Write failing unit tests in `tests/unit/test_a2ui.py` for the new A2UI v0.9 catalog widgets: `VisualScenarioCard` (with `1:1`/`16:9` image, `test_events`, and inline Italian Director textarea) and `FideExamOutcomeCard` (4 FIDE dimensions, CEFR/FIDE level badge, and Native B1 Rewrite).
- [ ] Task 3.2: Implement `VisualScenarioCard` and `FideExamOutcomeCard` in `src/hummerli/a2ui.py` and wire outcome scoring into `build_a2ui_surface_for_turn`.
- [ ] Task 3.3: Phase Verification & Checkpoint (Refer to `workflow.md`).

## Phase 4: ADK Trajectory Evaluations ("Evals Along the Way") & Web/Mobile Orb UI
- [ ] Task 4.1: Create ADK `.test.json` trajectory evaluation fixtures in `tests/evals/trajectories/`:
  - [ ] `entropic_scenario_init.test.json`
  - [ ] `director_override_indian_restaurant.test.json`
- [ ] Task 4.2: Update `tests/evals/test_trajectories.py` and `tests/unit/test_webapp.py` to assert 100% trajectory score across all 6 `.test.json` suites and verify `/api/scenarios` + `/api/director_override` HTTP endpoints.
- [ ] Task 4.3: Upgrade `src/hummerli/webapp.py` to auto-detect Mobile Portrait (`1:1` stacked layout) vs Desktop Landscape (`16:9` split layout), render the 3 Zero-Click Entropic Scenario chips, the inline **"🎬 Regia in Italiano"** textarea, and the live `VisualScenarioCard` + `FideExamOutcomeCard` A2UI v0.9 components.
- [ ] Task 4.4: Run full test & trajectory evaluation suite (`PYTHONPATH=src .venv/bin/pytest`), restart `hummerli.service`, and commit & push track completion.
