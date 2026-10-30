# Specification: AI Entropic Visual Scenarios (Zero-Click + Italian Director Override) & Outcome-Based FIDE B1 Exam Rubric

- **Track ID**: `entropic_scenarios_and_fide_outcome_20261030`
- **Type**: `feature`
- **Target Profile (MVP)**: `riccardo` (Goethe B1 / FIDE Zürich Einbürgerung), extensible to `ale` and `sebi`.

---

## 1. Overview & Strategic Goal

Inspired by the best "outcome-based" mechanics of *Finnish It! / Finish it*, this track upgrades **Hummerli** with two major capabilities rendered dynamically via **Google A2UI v0.9 Generative UI**:

1. **Zero-Click Entropic Visual Scenarios + "Regia in Italiano" Override**:
   - Instead of forcing the user through tedious setup questionnaires (*"Morning or evening? Summer or winter? Bakery or post office?"*), Hummerli automatically injects controlled entropy (time of day, weather/season in Zürich, interlocutor mood, civic/daily setting) and **pre-generates 3 ready-to-play Scenario Cards** already anchored to the user's top 3 due SRS words (`get_due_words`).
   - **Client Viewport & Device Auto-Detection**:
     - **Mobile / Portrait (`aspect_ratio = "1:1"`)**: Vertical stacked layout with a square `1:1` scene illustration on top, the Voice Orb + scenario prompt in the middle, and interactive comprehension/trigger questions + A2UI widgets stacked below.
     - **Desktop / Landscape (`aspect_ratio = "16:9"`)**: Horizontal split layout with a widescreen `16:9` scene illustration alongside the Voice Orb, scenario questions, and A2UI feedback cards.
   - **"Regia in Italiano" (Live Director Textarea)**:
     - A natural-language Italian steering box (e.g., *"Sì ma voglio ristorante indiano invece di italiano e la tizia è molto maleducata con me"*).
     - Submitting the textarea triggers an ADK tool (`mutate_scenario_with_director_notes`) that hot-swaps the setting, updates Frau Blücher's roleplay persona/mood, regenerates the scene illustration (cached locally), and **strictly preserves the 3 target Goethe B1 SRS words** so pedagogical progression is never lost.

2. **Outcome-Based FIDE B1 Exam Rubric & Native Rewrite (Stile *Finnish It!*)**:
   - Every spoken/written turn in a scenario is evaluated against official **FIDE / Goethe B1 Oral Exam criteria** (*Erfüllung der Aufgabe, Flüssigkeit, Wortschatz, Strukturen/Grammatik*).
   - Renders an A2UI v0.9 **`FideExamOutcomeCard`** + **`GrammarDiffCard`** showing:
     - **Predicted FIDE Sub-Score** (`A1` / `A2` / `A2+` / `B1 Pass ✅` / `B2`),
     - **"What it takes to reach B1+"** actionable advice in Italian,
     - **Native B1 Rewrite** (*"Così lo direbbe un candidato B1 perfetto a Zurigo"*).

---

## 2. Functional Requirements

### FR-1: Entropic Scenario Generator (`hummerli.scenarios`)
- **Entropy Seeds**: Combines Zurich locations (*Bäckerei am Bellevue, Kreisbüro 4, SBB Schalter HB, Kinderarztpraxis, Quartierfest, Indisches Restaurant in Wiedikon*), time/season (*Montagmorgen im Regen, Freitagabend im Winter, Sommermittag am See*), and interlocutor vibe (*freundlich aber in Eile, streng und bürokratisch, leicht unhöflich/genervt, herzlich*).
- **Zero-Click Batch**: `generate_entropic_scenarios(profile_id, count=3, client_layout="mobile_portrait" | "desktop_landscape")` produces 3 distinct, complete `EntropicScenario` objects, each binding the learner's current `due_words` from `SRSEngine`.
- **Scene Image Generation & Disk Cache**:
  - Uses Gemini Image generation (`gemini-2.5-flash-image` / `gemini-3.1-flash-image-preview` via `GEMINI_API_KEY`) with deterministic SVG/Canvas illustrated fallback when offline or in fast unit tests.
  - Automatically formats aspect ratio (`1:1` for mobile portrait, `16:9` for desktop landscape) and caches images under `data/scenarios_cache/` (gitignored).

### FR-2: Client Viewport Auto-Detect (`mobile_portrait` vs `desktop_landscape`)
- On page load and window resize, the Web/PWA client detects `window.innerWidth < window.innerHeight` (or mobile User-Agent) and passes `client_layout` (`"mobile_portrait"` vs `"desktop_landscape"`) to `/api/scenarios`.
- **Mobile Portrait Layout**: `1:1` image card above, compact Voice Orb + target word chips, and scenario questions / A2UI widgets below.
- **Desktop Landscape Layout**: Side-by-side `16:9` visual stage on the left and interactive Voice Orb + A2UI cards on the right.

### FR-3: Italian Director Override (`mutate_scenario_with_director_notes`)
- New ADK tool registered on `HummerliToolset` and `HummerliAgent`:
  `mutate_scenario_with_director_notes(profile_id: str, current_scenario_id: str, director_feedback_it: str, client_layout: str = "mobile_portrait") -> dict`
- Parses the user's Italian instruction (e.g., *"voglio ristorante indiano invece di italiano e la tizia è molto maleducata con me"*), rewrites the German B1 situation, updates the interlocutor's persona/mood instructions for Frau Blücher, generates a fresh scene illustration matching the new prompt, and keeps the exact same `target_words` from the SRS engine.

### FR-4: Outcome-Based FIDE B1 Rubric & A2UI v0.9 Widgets
- Extends `src/hummerli/a2ui.py` with:
  - `VisualScenarioCard`: displays the `1:1` or `16:9` image, scenario title, interlocutor mood badge, 2–3 oral prompt questions (*Test Events*), target SRS words, and the inline **"🎬 Regia in Italiano" textarea**.
  - `FideExamOutcomeCard`: shows the 4 FIDE dimensions (*Fluency, Grammar, Vocabulary, Task Completion*), the estimated FIDE level badge (`A2` → `B1 ✅`), the **Native B1 Rewrite**, and what is needed to reach the next tier.

### FR-5: Trajectory Evaluations ("Evals Along the Way")
- New ADK `.test.json` trajectory suites in `tests/evals/trajectories/`:
  1. `entropic_scenario_init.test.json`: verifies `generate_entropic_scenarios` + `get_due_words` trajectory at scenario start.
  2. `director_override_indian_restaurant.test.json`: verifies that when Riccardo submits Italian director feedback (*"Si ma voglio ristorante indiano, invece di italiano e la tizia e' molto maleducata con me"*), the agent invokes `mutate_scenario_with_director_notes` while preserving the SRS target words.

---

## 3. Non-Functional Requirements
- **Zero Extra Clicks to Start**: Opening the app immediately selects the #1 Entropic Scenario (with 2 alternative cards selectable in 1 tap).
- **Offline & Deterministic Testability**: All unit and trajectory eval tests (`pytest`) run in <1s without requiring live network calls.
- **Privacy Hygiene**: Generated scenario cache (`data/scenarios_cache/`) stays local/gitignored.

---

## 4. Acceptance Criteria
- [ ] `generate_entropic_scenarios` returns 3 varied scenarios with `1:1` (mobile) or `16:9` (desktop) visual assets and binds the learner's due SRS words.
- [ ] Submitting *"Sì ma voglio ristorante indiano, invece di italiano e la tizia è molto maleducata con me"* in the Italian Director textarea calls `mutate_scenario_with_director_notes`, updates the active scenario + mood + image, and keeps the SRS target words intact.
- [ ] Every turn in the scenario produces an A2UI v0.9 `updateComponents` message containing both the `VisualScenarioCard` and the outcome-based `FideExamOutcomeCard` (with Native B1 Rewrite and FIDE level score).
- [ ] All existing + new unit and trajectory evaluation suites pass (`PYTHONPATH=src .venv/bin/pytest`).
