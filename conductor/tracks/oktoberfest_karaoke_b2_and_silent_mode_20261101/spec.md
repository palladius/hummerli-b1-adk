# Specification: Oktoberfest "Karaoke B2" (Pre-Computed CEFR Color-Coding) & Cross-App Duolingo Silent/No-Mic "Piano B"

- **Track ID**: `oktoberfest_karaoke_b2_and_silent_mode_20261101`
- **Type**: `feature`
- **Integrates With**:
  - Track 1 (`srs_and_trajectory_eval_mvp_20261017` — Goethe Curriculum & SM-2 SRS)
  - Track 2 (`entropic_scenarios_and_fide_outcome_20261030` — Scenarios & FIDE Outcome)
  - Track 3 (`interactive_scene_hotspots_and_sample_dialogues_20261030` — Scene Vocabulary & Sample Conversations)
  - Track 4 (`noun_gender_xray_across_stack_20261030` — Noun Gender X-Ray `Ctrl+G` / Multi-Tap)

---

## 1. Overview & Pedagogical Goal

Learning German through iconic **Oktoberfest / Schlager / NDW** anthems (*"So ein schöner Tag (Fliegerlied)"*, *"Joanna"*, *"Wahnsinn (Hölle, Hölle, Hölle)"*, *"Atemlos durch die Nacht"*, *"99 Luftballons"*) locks vocabulary and grammatical structures into long-term musical memory.

This track introduces two deeply connected capabilities:
1. **🍺 "Karaoke B2" (Scientific Offline CEFR Color-Coding + 2 Interactive Gameplay Modes)**:
   - **Pre-Computed, Scientifically Verified CEFR Token Map**: Every song line is pre-processed offline against official **Goethe-Institut A1, A2, B1, and B2 wordlists** (no runtime LLM latency or hallucination) and validated by deterministic `pytest` unit suites:
     - 🟢 **Verde (`#22c55e`)**: **A1–A2** foundational words (*schön, Tag, heute, fliegen, Herz, schauen*)
     - 🔵 **Blu (`#3b82f6`)**: **B1** target words (*Wahnsinn, Gefühl, Horizont, träumen, Sehnsucht*)
     - 🔴 **Rosso (`#ef4444`)**: **B2+ / Idiomatic / Schlager expressions** (*Hölle, geborgen, schwindelfrei, unsterblich, verdammt*)
   - **Gameplay Mode 1 — "Stop & Fill the Gap" (Cloze Wait Mode)**:
     - The karaoke line progresses word-by-word up to a target **🔵 B1** or **🔴 B2** word, blanks it out (`"Warum schickst du mich in die [_______]?"`), and **pauses playback** until the user either:
       - **🎙️ Pronounces the word aloud** (when Microphone is ON), OR
       - **⌨️ Types it / taps the right word stem** (when in **"🙊 Non posso parlare ora"** mode).
   - **Gameplay Mode 2 — "Live Flow & 4–5 Synonym Translation" (Rhythm Quiz Mode)**:
     - The song continues flowing without stopping while a target **🔵 B1 / 🔴 B2** word pulses; the user must select its exact Italian translation among **4–5 semantically close distractors** (e.g. for *Sehnsucht*: `nostalgia struggente ✅`, `gelosia improvvisa`, `stanchezza fisica`, `curiosità morbosa`, `rabbia repressa`) before the bar finishes.

2. **🔇🙊 Cross-App Duolingo-Style "Piano B" (Adaptive Silent & No-Mic Mode Across ALL Tracks)**:
   - Whether Riccardo is in a quiet office, on an SBB train in Zürich, or at home on `pupurabbux` while his wife sleeps, he can toggle at any moment:
     - **🔇 `"Non posso ascoltare ora (15 min)"` (Silent / No-Audio Mode)**: Mutes all TTS and WebAudio accompaniment, activates a **Visual Bouncing-Ball Beat & Phonetic Stress Ticker** for Karaoke and Sample Conversations, and shifts listening prompts to visual reading challenges.
     - **🙊 `"Non posso parlare ora (15 min)"` (Quiet / No-Mic Mode)**: Disables microphone capture and seamlessly switches Karaoke Mode 1, Scenario Roleplays (Track 2/3), and Frau Blücher turns to tactile/written challenges (keyboard + smart word chips + 4–5 distractor quizzes) while still crediting SM-2 SRS progress.

---

## 2. Functional Requirements

### FR-1: Pre-Computed Karaoke Catalog & Scientific Goethe CEFR Verifier (`src/hummerli/karaoke.py`, `data/karaoke/oktoberfest_b2.json`)
- **Curated 5-Song Oktoberfest & Kult Catalog**:
  1. `fliegerlied` — *"So ein schöner Tag (Fliegerlied)"* (Tim Toupet / Donikkl)
  2. `joanna` — *"Joanna (Du geile Sau / Geboren um Liebe zu geben)"* (Roland Kaiser / Peter Wackel)
  3. `wahnsinn` — *"Wahnsinn (Hölle, Hölle, Hölle)"* (Wolfgang Petry)
  4. `atemlos` — *"Atemlos durch die Nacht"* (Helene Fischer)
  5. `neunundneunzig_luftballons` — *"99 Luftballons"* (Nena)
- **Pre-Computed Token Schema (`KaraokeToken`)**:
  - `surface`: original lyric token
  - `lemma`: normalized German lemma
  - `cefr`: `"A1" | "A2" | "B1" | "B2"`
  - `cefr_color_band`: `"green_a1_a2"` (`#22c55e`) | `"blue_b1"` (`#3b82f6`) | `"red_b2"` (`#ef4444`)
  - `pos`: `"noun" | "verb" | "adj" | "other"` (integrates with Track 4's `Ctrl+G` Rosa/Azzurrino/Grigio Gender X-Ray when inspecting nouns!)
  - `translation_it`: exact contextual Italian translation
  - `distractors_it`: list of 4 plausible Italian near-synonym distractors for Mode 2 (`len(options) == 5` total including the correct answer)
- **Scientific Verification (`verify_karaoke_cefr_integrity`)**:
  - A deterministic validator tested in `tests/unit/test_karaoke.py` that cross-checks every token's `lemma` and `cefr` against the Goethe reference wordlist and ensures every target B1/B2 challenge token has 4 distinct Italian distractors and valid timing (`start_ms`, `end_ms`).

### FR-2: Two Interactive Karaoke Modes (`stop_and_fill` & `flow_and_translate`)
- **Mode 1 (`stop_and_fill`)**:
  - Advances through the lyric line (`start_ms` → `end_ms`), masks the designated target token (`[_____]`), and halts the timeline.
  - Accepts either spoken audio/transcript (`Mic ON`) or typed/chip answer (`🙊 No-Mic ON`).
  - Evaluates accuracy (`evaluate_karaoke_attempt`), updates SM-2 SRS state if the word is in the user's deck, shows immediate green/red visual feedback, and resumes the song.
- **Mode 2 (`flow_and_translate`)**:
  - Plays continuously (with WebAudio synth melody + optional vocal TTS when Audio ON, or visual rhythm progress bar + bouncing beat indicator when `🔇 Silent Mode` is ON).
  - As each line's target `blue_b1` or `red_b2` word highlights, presents 5 Italian choices (1 correct + 4 close distractors) in an A2UI `KaraokeB2ChallengeCard`.

### FR-3: Cross-App Adaptive Modality State (`ModalityPreferences`: `can_listen`, `can_speak`)
- Persistent session/client state (`can_listen: bool = True`, `can_speak: bool = True`, with optional `snooze_until` 15-minute timer like Duolingo):
  - Exposed in the Web/Mobile top bar via two 1-tap pills: **`🔊 Ascolto ON` / `🔇 Silenzioso (Piano B)`** and **`🎙️ Voce ON` / `🙊 Solo Scritto (Piano B)`**.
  - **Impact Across All Tracks**:
    - **Track 1 & 2 (Voice Orb & Scenarios)**: When `can_speak=False`, the big Orb morphs into a tactile **"✍️ Rispondi per iscritto / Costruisci frase"** composer; when `can_listen=False`, TTS is muted and subtitles + visual grammar badges take center stage.
    - **Track 3 (Scene Vocabulary & Sample Conversation)**: When `can_listen=False`, clicking a hotspot shows phonetic pronunciation (`[ˈpaʁkˌbaŋk]`) + Italian tooltip without firing audio; `Provaci tu!` uses text/chips when `can_speak=False`.
    - **Track 5 (Karaoke B2)**: Seamlessly adapts both Mode 1 and Mode 2 to the `2x2` `(can_listen, can_speak)` matrix so the user always has a fun, high-yield "Piano B".

### FR-4: ADK Tooling, A2UI v0.9 `KaraokeB2StageCard` & Trajectory Evaluations
- New ADK tools on `HummerliToolset`:
  - `start_karaoke_session(profile_id: str, song_id: str, mode: str = "stop_and_fill", can_listen: bool = True, can_speak: bool = True) -> dict`
  - `submit_karaoke_answer(profile_id: str, song_id: str, line_index: int, user_answer: str, mode: str = "stop_and_fill") -> dict`
  - `set_modality_preferences(profile_id: str, can_listen: bool, can_speak: bool) -> dict`
- New A2UI v0.9 widget `KaraokeB2StageCard` rendering the synchronized lyrics with 🟢 A1–A2 / 🔵 B1 / 🔴 B2 color-coding, the Mode 1 cloze input / mic trigger, the Mode 2 5-option Italian translation quiz, and the `🔇 / 🙊` Duolingo fallback toggles.
- New trajectory evaluation fixture `tests/evals/trajectories/karaoke_b2_and_silent_mode.test.json`.

---

## 3. Acceptance Criteria
- [ ] `data/karaoke/oktoberfest_b2.json` contains the 5 pre-computed Oktoberfest/Kult songs (*Fliegerlied*, *Joanna*, *Wahnsinn*, *Atemlos*, *99 Luftballons*) with scientifically verified CEFR tags (`green_a1_a2`, `blue_b1`, `red_b2`) and 5-option Italian translation challenges.
- [ ] **Mode 1 (`stop_and_fill`)** pauses at the blanked B1/B2 word and accepts either voice pronunciation or written input (in `🙊 No-Mic Mode`).
- [ ] **Mode 2 (`flow_and_translate`)** flows continuously (with audio or `🔇 Silent` visual rhythm bar) and scores the user's selection among 5 close Italian translations.
- [ ] Toggling **`🔇 Non posso ascoltare ora`** or **`🙊 Non posso parlare ora`** adapts Karaoke, Voice Orb, Entropic Scenarios, and Scene Dialogues without losing SRS tracking.
- [ ] All unit tests (`tests/unit/test_karaoke.py`) and trajectory evaluations (`tests/evals/trajectories/karaoke_b2_and_silent_mode.test.json`) pass (`PYTHONPATH=src .venv/bin/pytest`).
