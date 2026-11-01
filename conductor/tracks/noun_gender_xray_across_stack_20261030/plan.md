# Implementation Plan: Cross-Stack German Noun Gender X-Ray (Rosa / Azzurrino / Grigio, On-Demand Reveal)

## Phase 1: 3-Tier German Noun Gender Resolver (`src/hummerli/gender.py`)
- [x] Task 1.1: Write failing unit tests (`tests/unit/test_gender.py`) covering:
  - Canonical palette mapping: `F` (`die`) → 🌸 Rosa `#f472b6`, `M` (`der`) → 🩵 Azzurrino `#38bdf8`, `N` (`das`) → 🩶 Grigio `#94a3b8`.
  - Tier 1: Inline LLM tag parsing (`[Hund|M]`, `[Wiese|F]`, `[Geschäft|N]`).
  - Tier 2: Curriculum lookup (`Antrag` → `M`, `Gemeinde` → `F`, `Gesetz` → `N`) + German compound-noun tail resolution (`Parkbank` → `F`, `Hundewiese` → `F`, `Sprachzertifikat` → `N`, `Rathausplatz` → `M`).
  - Tier 3: Deterministic German suffix heuristics (`-ung`, `-heit`, `-keit`, `-schaft`, `-tion`, `-tät` → `F`; `-chen`, `-lein`, `-ment`, `-tum`, `-um` → `N`; `-ling`, `-ismus`, `-or`, `-ig` → `M`).
  - HTML/Token span annotation (`annotate_german_text(text_de)`) producing `.de-noun` spans with `data-gender`, `data-article`, and `data-lemma`.
- [x] Task 1.2: Implement `NounGenderAnnotation`, `GenderResolver`, and `annotate_german_text` in `src/hummerli/gender.py`.
- [x] Task 1.3: Phase Verification & Checkpoint (Refer to `workflow.md`).

## Phase 2: ADK Tool `analyze_german_nouns_gender`, A2UI v0.9 & CLI Integration
- [x] Task 2.1: Write failing unit tests in `tests/unit/test_a2ui.py` and `tests/evals/test_trajectories.py` for the `analyze_german_nouns_gender` ADK tool and cross-stack A2UI payload enrichment.
- [x] Task 2.2: Register `analyze_german_nouns_gender` on `HummerliToolset` (`src/hummerli/tools.py`) and `HummerliAgent` (`src/hummerli/agent.py`), create `tests/evals/trajectories/noun_gender_xray.test.json`, and add Rich Rosa/Azzurrino/Grigio support in `src/hummerli/cli.py`.
- [x] Task 2.3: Phase Verification & Checkpoint (Refer to `workflow.md`).

## Phase 3: Frontend On-Demand UX (`Ctrl+G` Desktop + Double/Triple-Tap Mobile) Across All Surfaces
- [x] Task 3.1: Write failing unit/integration tests in `tests/unit/test_webapp.py` verifying that `/api/chat` and `/api/state` return `annotated_html` / `noun_annotations` and that the Web UI serves the Rosa (`#f472b6`), Azzurrino (`#38bdf8`), and Grigio (`#94a3b8`) CSS variables and `Ctrl+G` / multi-tap handlers.
- [x] Task 3.2: Upgrade `src/hummerli/webapp.py` (both Orb Mode `/?mode=orb` and Studio Mode `/?mode=studio`, plus Track 3's Scene Vocabulary SVG arrows & Sample Conversation cards) with:
  - Default non-spoiling noun styling,
  - Single-noun double-click / double-tap reveal (`.gender-revealed`),
  - Global `Ctrl+G` (desktop) and Triple-tap / `⚧️` header pill (mobile) Gender X-Ray toggle (`.gender-xray-active`).
- [x] Task 3.3: Run full test & trajectory evaluation suite (`PYTHONPATH=src .venv/bin/pytest`), restart `hummerli.service`, and commit & push track completion.
