# Specification: Cross-Stack German Noun Gender X-Ray (Rosa / Azzurrino / Grigio, On-Demand Reveal)

- **Track ID**: `noun_gender_xray_across_stack_20261030`
- **Type**: `feature`
- **Integrates With**:
  - Track 1 (`srs_and_trajectory_eval_mvp_20261017` — Curriculum, SRS cards, CLI, Chat Transcripts)
  - Track 2 (`entropic_scenarios_and_fide_outcome_20261030` — Entropic Visual Scenarios)
  - Track 3 (`interactive_scene_hotspots_and_sample_dialogues_20261030` — `1. Vocabulary` SVG Arrows & `2. Sample Conversation`)

---

## 1. Overview & Pedagogical Rationale

Mastering German noun gender (`der` Masculine, `die` Feminine, `das` Neuter) is critical for passing the **FIDE B1 / Goethe B1** oral exam, because every preposition (`mit dem Hund`, `auf die Wiese`, `in der Gemeinde`) and adjective ending depends on the noun's gender.

However, if gender colors are permanently visible by default, the learner's brain passively relies on the color crutch instead of actively retrieving the gender from memory. Conversely, having no gender visual aid makes live transcripts and dialogues missed learning opportunities.

This track introduces a **Cross-Stack German Noun Gender X-Ray System**:
1. **Canonical Hummerli Gender Palette**:
   - **Femminile (`die` / `F`)** → **🌸 Rosa** (`#f472b6` text / `rgba(244, 114, 182, 0.16)` pill background / `#ec4899` border)
   - **Maschile (`der` / `M`)** → **🩵 Azzurrino** (`#38bdf8` text / `rgba(56, 189, 248, 0.16)` pill background / `#0ea5e9` border)
   - **Neutro (`das` / `N`)** → **🩶 Grigio** (`#94a3b8` text / `rgba(148, 163, 184, 0.18)` pill background / `#64748b` border)
2. **Non-Immediate, On-Demand Reveal ("Visualizzato all'uopo")**:
   - By default, German nouns render in standard readable typography (with a barely perceptible dotted baseline hint so the user knows they are inspectable, without spoiling the gender).
   - **Single-Word Reveal (Double-Click / Double-Tap on a Noun)**: Reveals *only* that specific noun's gender color (**Rosa / Azzurrino / Grigio**) + micro-article prefix (`die`, `der`, `das`).
   - **Global X-Ray Toggle (`Ctrl+G` on Desktop / Triple-Tap or `⚧️` Header Pill on Mobile)**: Toggles Gender X-Ray across **all** German nouns currently on screen (Chat bubbles, Track 3 SVG Scene Hotspots, Track 3 Sample Conversations, A2UI Flashcards, Grammar Diffs).

---

## 2. Functional Requirements

### FR-1: 3-Tier Cross-Stack German Noun Gender Resolver (`src/hummerli/gender.py`)
A unified backend module `GenderResolver` that resolves any German noun token (or inline LLM tag) into a structured `NounGenderAnnotation`:
- `surface`: original word in text (e.g. `"Wiese"`, `"Hund"`, `"Geschäft"`, `"Einbürgerung"`, `"Parkbank"`)
- `lemma`: base noun lemma
- `gender`: `"F" | "M" | "N"`
- `article`: `"die" | "der" | "das"`
- `color_hex`: `"#f472b6"` (`F`), `"#38bdf8"` (`M`), `"#94a3b8"` (`N`)
- `css_class`: `"gender-f"` | `"gender-m"` | `"gender-n"`

**Resolution Tiers (in priority order)**:
1. **Tier 1 — Inline LLM Markup & Explicit Metadata**:
   - Parses optional LLM inline notation `[Wiese|F]`, `[Hund|M]`, `[Geschäft|N]` or `[Parkbank|die]` emitted by Frau Blücher / Scenario Generator, as well as explicit `article` fields in `CurriculumEntry` and `SceneVocabHotspot`.
2. **Tier 2 — Curriculum + Core German B1 Inflection & Compound Tail Lookup**:
   - Looks up exact and inflected forms (plurals, genitive `-s/-es`, dative plural `-n`) against `goethe_b1.json`, `tandem_p3.json`, `tandem_p1.json`, and the built-in B1 core noun dictionary.
   - **German Compound Noun Rule (Komposita)**: If a capitalized word is a compound (e.g., `Parkbank`, `Sprachzertifikat`, `Bahnhofsvorsteher`, `Hundewiese`), resolves the gender from the **longest matching tail noun** (`-bank` → `die` [F], `-zertifikat` → `das` [N], `-wiese` → `die` [F]).
3. **Tier 3 — Deterministic German Morphological Suffix Rules**:
   - **Feminine (`die` / `F` → 🌸 Rosa)**: `-ung`, `-heit`, `-keit`, `-schaft`, `-tion`, `-tät`, `-ik`, `-ie`, `-enz`, `-anz`, `-ur`, `-in`.
   - **Neuter (`das` / `N` → 🩶 Grigio)**: `-chen`, `-lein`, `-ment`, `-tum`, `-um`, `-ma`, `Ge-...-e` collectives (e.g. `Gebäude`, `Gebirge`).
   - **Masculine (`der` / `M` → 🩵 Azzurrino)**: `-ling`, `-ismus`, `-ig`, `-ich`, `-or`, `-ant`, `-ent`, `-ist`.

### FR-2: Cross-Stack Payload Enrichment (Chat, A2UI v0.9, Track 3 Scenes, CLI)
- **Web & A2UI API (`/api/chat`, `/api/voice-turn`, `/api/scenarios/*`)**:
  - Every German text field returned by the backend includes either pre-annotated `annotated_html` (`<span class="de-noun" data-gender="F" data-article="die" data-lemma="Wiese">Wiese</span>`) or a structured `noun_annotations` list so the frontend can render interactive noun spans anywhere.
- **Track 3 (`InteractiveSceneExplorerCard`) Alignment**:
  - **In `1. Vocabulary` (SVG Arrows on Scene Image)**: By default, hotspot pills show the noun (`Parkbank`, `Baum`, `Hund`, `Wiese`, `Geschäft`) in neutral dark glassmorphism so the user can test themselves; double-tapping a hotspot pill or pressing `Ctrl+G` / Triple-Tap switches the pill and its SVG arrow to **🌸 Rosa (`die`)**, **🩵 Azzurrino (`der`)**, or **🩶 Grigio (`das`)** and reveals the article!
  - **In `2. Sample Conversation`**: Key nouns are **bold** by default; double-tapping a noun or toggling `Ctrl+G` / Triple-Tap illuminates all nouns in **🌸 Rosa / 🩵 Azzurrino / 🩶 Grigio** with their micro-article badge (`die`, `der`, `das`).
- **CLI Support (`hummerli srs`, `hummerli simulate`)**:
  - Adds a `--gender-colors / --no-gender-colors` flag in Typer CLI using Rich colors (`bright_magenta` for F, `bright_cyan` for M, `grey70` for N).

### FR-3: Frontend On-Demand Interaction (`Ctrl+G` Desktop + Double/Triple-Tap Mobile)
- **Desktop Shortcut (`Ctrl+G` or `Cmd+G`)**:
  - Pressing `Ctrl+G` toggles `document.body.classList.toggle('gender-xray-active')` and shows a non-intrusive toast (`"⚧️ Gender X-Ray: ON (🌸 die · 🩵 der · 🩶 das)"` / `"⚧️ Gender X-Ray: OFF"`).
- **Single-Word Double-Tap / Double-Click**:
  - Double-clicking (desktop) or double-tapping within `300ms` (mobile touch) on any `.de-noun` element toggles `.gender-revealed` on that single word (`e.g. [die] Wiese` in 🌸 Rosa), without revealing the rest of the screen.
- **Mobile Global Trigger (Triple-Tap on Card/Transcript or Long-Press on `⚧️` Pill)**:
  - Triple-tapping on any conversation card/scene or tapping the subtle `⚧️ Ctrl+G` indicator pill in the top bar toggles global `.gender-xray-active` on mobile.

### FR-4: ADK Tooling & Trajectory Evaluation ("Evals Along the Way")
- New ADK tool on `HummerliToolset`:
  - `analyze_german_nouns_gender(text_de: str) -> dict` returning all detected German nouns in `text_de` with `{surface, lemma, gender, article, color_hex, resolution_tier}`.
- New trajectory evaluation fixture `tests/evals/trajectories/noun_gender_xray.test.json` testing when the user asks Frau Blücher or Rijckard about the gender of nouns in a sentence (e.g., *"Che genere hanno Hund, Wiese e Geschäft?"* or *"Welches Genus haben diese Nomen?"*).

---

## 3. Acceptance Criteria
- [ ] `GenderResolver` accurately classifies Feminine (`die` → `F`, 🌸 `#f472b6`), Masculine (`der` → `M`, 🩵 `#38bdf8`), and Neuter (`das` → `N`, 🩶 `#94a3b8`) across curriculum words, compound nouns (`Parkbank` → `F`, `Sprachzertifikat` → `N`), morphological suffixes (`Einbürgerung` → `F`, `Mädchen` → `N`, `Frühling` → `M`), and inline LLM tags.
- [ ] By default in the UI, German nouns do **not** immediately spoil their gender color.
- [ ] **Double-tap / double-click** on a single noun reveals its **Rosa / Azzurrino / Grigio** color and micro-article (`die` / `der` / `das`).
- [ ] **`Ctrl+G`** on desktop (or **Triple-tap** / `⚧️` toggle on mobile) toggles global Gender X-Ray across all German text on screen, including Chat bubbles, A2UI widgets, and Track 3's Scene Vocabulary Arrows & Sample Conversations.
- [ ] All unit tests (`tests/unit/test_gender.py`) and ADK trajectory evals (`tests/evals/trajectories/noun_gender_xray.test.json`) pass (`PYTHONPATH=src .venv/bin/pytest`).
