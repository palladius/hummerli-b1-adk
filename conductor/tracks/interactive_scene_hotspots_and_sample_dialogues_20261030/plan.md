# Implementation Plan: Interactive Scene Vocabulary Hotspots (SVG Arrows) & Color-Coded Sample Conversations

## Phase 1: Scene Hotspots (SVG Arrow Coordinates) & Sample Conversation Data Models
- [ ] Task 1.1: Write failing unit tests (`tests/unit/test_scene_hotspots_and_dialogue.py`) for `SceneVocabHotspot` (normalized `(label_x, label_y) -> (target_x, target_y)` arrow coordinates, grammatical gender color mapping) and `SampleConversation` (`DialogueLine` with bold/color-coded B1 vocabulary tokens and Italian translation).
  - [ ] Include the canonical Zürich Park scene (*"Grüezi! Schönes Wetter heute, oder?" ... "Ich komme jeden Morgen mit meinem Hund auf diese Wiese, damit er sein Geschäft machen kann."*) with hotspots (`die Parkbank`, `der Baum`, `der Rentner`, `die Wiese`, `der Hund`, `das Geschäft`).
- [ ] Task 1.2: Implement `SceneVocabHotspot`, `DialogueLine`, and `SampleConversation` in `src/hummerli/scenarios.py`, ensuring both curated and custom/mutated scenarios populate hotspots and sample dialogues.
- [ ] Task 1.3: Phase Verification & Checkpoint (Refer to `workflow.md`).

## Phase 2: ADK Tool `get_scene_vocabulary_and_dialogue` & A2UI v0.9 `InteractiveSceneExplorerCard`
- [ ] Task 2.1: Write failing unit tests in `tests/unit/test_a2ui.py` for the `get_scene_vocabulary_and_dialogue` ADK tool and the A2UI v0.9 `InteractiveSceneExplorerCard` widget (exposing `1. Vocabulary` arrow overlay state and `2. Sample Conversation` bold/color-coded dialogue state).
- [ ] Task 2.2: Register `get_scene_vocabulary_and_dialogue` on `HummerliToolset` (`src/hummerli/tools.py`) and `HummerliAgent` (`src/hummerli/agent.py`), and add `InteractiveSceneExplorerCard` to `HUMMERLI_A2UI_CATALOG_SCHEMA` (`src/hummerli/a2ui.py`).
- [ ] Task 2.3: Phase Verification & Checkpoint (Refer to `workflow.md`).

## Phase 3: ADK Trajectory Evaluation ("Evals Along the Way") & Interactive SVG Arrow + Dialogue UI
- [ ] Task 3.1: Create ADK `.test.json` trajectory evaluation fixture `tests/evals/trajectories/scene_vocab_and_sample_convo.test.json` and update `tests/evals/test_trajectories.py`.
- [ ] Task 3.2: Upgrade `src/hummerli/webapp.py` to render the **`🏷️ 1. Vocabulary`** button (clickable word chips + `<svg>` callout labels and directional arrows over the scene image + `de-DE` TTS on click) and the **`💬 2. Sample Conversation`** button (dialogue with bold gender-colored B1 words, Italian translations, `🔊 Ascolta Dialogo` 2-voice playback, and `🎙️ Provaci tu con Frau Blücher!` roleplay trigger).
- [ ] Task 3.3: Run full test & trajectory evaluation suite (`PYTHONPATH=src .venv/bin/pytest`), restart `hummerli.service`, and commit & push track completion.
