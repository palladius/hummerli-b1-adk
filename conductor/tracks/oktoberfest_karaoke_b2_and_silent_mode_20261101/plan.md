# Implementation Plan: Oktoberfest "Karaoke B2" (Pre-Computed CEFR Color-Coding) & Cross-App Duolingo Silent/No-Mic "Piano B"

## Phase 1: Pre-Computed Oktoberfest Catalog (`data/karaoke/oktoberfest_b2.json`) & Scientific CEFR Validator (`src/hummerli/karaoke.py`)
- [ ] Task 1.1: Write failing unit tests (`tests/unit/test_karaoke.py`) verifying:
  - Scientific CEFR alignment against Goethe reference wordlists (`green_a1_a2` → `#22c55e`, `blue_b1` → `#3b82f6`, `red_b2` → `#ef4444`).
  - Presence and schema completeness of the 5 Oktoberfest/Kult songs (`fliegerlied`, `joanna`, `wahnsinn`, `atemlos`, `neunundneunzig_luftballons`).
  - Mode 1 (`stop_and_fill`) gap masking & spoken/written answer verification.
  - Mode 2 (`flow_and_translate`) 5-option Italian near-synonym challenge scoring.
  - `ModalityPreferences` (`can_listen`, `can_speak`) adaptation across the `2x2` Silent/No-Mic matrix.
- [ ] Task 1.2: Create `data/karaoke/oktoberfest_b2.json` and implement `KaraokeEngine`, `KaraokeSong`, `KaraokeLine`, `KaraokeToken`, and `ModalityPreferences` in `src/hummerli/karaoke.py`.
- [ ] Task 1.3: Phase Verification & Checkpoint (Refer to `workflow.md`).

## Phase 2: ADK Tools (`start_karaoke_session`, `submit_karaoke_answer`, `set_modality_preferences`), A2UI v0.9 `KaraokeB2StageCard` & Trajectory Evals
- [ ] Task 2.1: Write failing unit and trajectory tests in `tests/unit/test_a2ui.py` and `tests/evals/test_trajectories.py` for the new Karaoke & Modality ADK tools and `KaraokeB2StageCard` A2UI v0.9 surface updates.
- [ ] Task 2.2: Register `start_karaoke_session`, `submit_karaoke_answer`, and `set_modality_preferences` in `src/hummerli/tools.py` and `src/hummerli/agent.py`, add `KaraokeB2StageCard` to `src/hummerli/a2ui.py`, and create `tests/evals/trajectories/karaoke_b2_and_silent_mode.test.json`.
- [ ] Task 2.3: Phase Verification & Checkpoint (Refer to `workflow.md`).

## Phase 3: Interactive Karaoke Web/Mobile Stage & Global Duolingo "Piano B" (`🔇 / 🙊`) UI
- [ ] Task 3.1: Write failing endpoint tests in `tests/unit/test_webapp.py` for `/api/karaoke`, `/api/karaoke/answer`, and `/api/modality`.
- [ ] Task 3.2: Upgrade `src/hummerli/webapp.py` to include:
  - Global header pills **`🔇 Non posso ascoltare`** and **`🙊 Non posso parlare`** that adapt Orb, Scenarios, Scene Dialogues, and Karaoke in real time.
  - Interactive **🍺 Karaoke B2 Stage** with synchronized lyrics colored in 🟢 A1–A2 (`#22c55e`), 🔵 B1 (`#3b82f6`), 🔴 B2 (`#ef4444`), visual bouncing-ball beat bar + WebAudio Oktoberfest synth melody, Mode 1 (`Stop & Pronounce/Type`) and Mode 2 (`Flow & 5-Choice Translation`).
- [ ] Task 3.3: Run full test & trajectory evaluation suite (`PYTHONPATH=src .venv/bin/pytest`), restart `hummerli.service`, and commit & push track completion.
