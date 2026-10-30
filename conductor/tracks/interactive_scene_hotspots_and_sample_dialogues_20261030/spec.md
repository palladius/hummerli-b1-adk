# Specification: Interactive Scene Vocabulary Hotspots (SVG Arrows) & Color-Coded Sample Conversations

- **Track ID**: `interactive_scene_hotspots_and_sample_dialogues_20261030`
- **Type**: `feature`
- **Depends On**: Track 2 (`entropic_scenarios_and_fide_outcome_20261030`)

---

## 1. Overview & Strategic Goal

In *Finnish It!*, one of the most effective B1 exam preparation features is **Visual Situation Learning**: the learner sees an everyday scene (e.g., a park in Zürich with a bench, tree, elderly man walking his dog, lawn) with two primary interactive buttons right below the scene:
1. **`🏷️ 1. Vocabulary` (Interactive Image Callouts with Arrows)**:
   - Clicking `1. Vocabulary` animates **SVG callout badges + directional arrows ("freccine")** directly onto the scene image pointing to the objects in the picture (e.g., `🌸 die Parkbank` → bench, `🩵 der Baum` → tree, `🩵 der Rentner` → old man, `🌸 die Wiese` → lawn, `🩵 der Hund` → dog, `🩶 das Geschäft` → dog's business).
   - Gender colors follow the cross-stack Hummerli Gender Palette (**Rosa `#f472b6` for `die` [F]**, **Azzurrino `#38bdf8` for `der` [M]**, **Grigio `#94a3b8` for `das` [N]**) and respect the on-demand gender reveal state (`Ctrl+G` on desktop / multi-tap on mobile from Track 4).
   - Clicking any hotspot label on the image speaks the word aloud (`de-DE` TTS), displays its Italian translation & plural/conjugation form, and lets the user pin/record it in their SM-2 SRS queue.
2. **`💬 2. Sample Conversation` (Bold/Color-Coded Dialogue + Audio & Live Roleplay)**:
   - Clicking `2. Sample Conversation` opens a natural 4–6 turn B1 dialogue set in that exact scene (e.g., *"Grüezi! Schönes Wetter heute, oder?" — "Ja, herrlich! Kommen Sie oft hierher?" — "Ich komme jeden Morgen mit meinem **Hund** auf diese **Wiese**, damit er sein **Geschäft** machen kann."*).
   - **Visual Text First (Step 1)**: Displays the German B1 lines alongside their Italian translations, with **all key vocabulary words in bold** and gender-colorable via the cross-stack **Rosa (`die` F) / Azzurrino (`der` M) / Grigio (`das` N)** system (`Ctrl+G` / multi-tap).
   - **Interactive Audio & Roleplay (Step 2 — User's Choice)**: Includes two optional action buttons inside the card:
     - `🔊 Ascolta Dialogo (2 Voci)`: plays the dialogue line-by-line alternating two voices (`de-DE` speakers).
     - `🎙️ Provaci tu con Frau Blücher!`: launches the live conversational turn where Frau Blücher plays Speaker A and invites Riccardo to reply as Speaker B using the highlighted words.

---

## 2. Functional Requirements

### FR-1: Scene Hotspot & Arrow Data Model (`SceneVocabHotspot`)
- Every visual scenario includes 5–7 `SceneVocabHotspot` items:
  - `lemma`: e.g. `"Parkbank"`
  - `display_headword`: e.g. `"die Parkbank, -bänke"`
  - `gender`: `"der" | "die" | "das" | "verb"` (drives badge/arrow color when Gender Mode is revealed: 🩵 Azzurrino `#38bdf8` for `der` [M], 🌸 Rosa `#f472b6` for `die` [F], 🩶 Grigio `#94a3b8` for `das` [N], ⚡ Amber `#f59e0b` for `verb`)
  - `translation_it`: e.g. `"panchina del parco"`
  - `label_x`, `label_y`: normalized percentage coordinates `(0..100)` where the floating pill badge sits
  - `target_x`, `target_y`: normalized percentage coordinates `(0..100)` on the image where the SVG arrow tip (`marker-end="url(#arrowhead)"`) points!

### FR-2: Interactive `1. Vocabulary` SVG Arrow Overlay
- Toggling the **`🏷️ 1. Vocabulary`** button on a scene renders an `<svg viewBox="0 0 100 100">` overlay on top of the `1:1` (mobile) or `16:9` (desktop) image:
  - Draws curved/straight SVG arrows from `(label_x, label_y)` to `(target_x, target_y)` with color-matched arrowheads.
  - Renders clickable pill badges at `(label_x, label_y)` with the German headword (`die Parkbank`).
  - Clicking a pill badge or word chip below the image:
    1. Highlights the arrow on the image,
    2. Pronounces the German word via `speechSynthesis` (`de-DE`),
    3. Shows a mini tooltip with Italian translation + example sentence + `➕ Aggiungi/Ripassa in SRS` button.

### FR-3: `2. Sample Conversation` with Bold Color-Coded Key Terms & Roleplay Handoff
- Every visual scenario includes a `SampleConversation` object with 4–6 `DialogueLine` entries:
  - `speaker`: e.g. `"Herr Meier (Rentner)"` / `"Sie (im Park)"`
  - `text_de`: German B1 sentence with markup or token spans for target scene vocabulary
  - `text_it`: natural Italian translation
  - `highlighted_words`: list of `{word, lemma, gender}` rendered in **bold + gender color**
- Inside the `SampleConversation` view, the user can freely choose to:
  1. **Read & Inspect** the dialogue with bold color-coded vocabulary and toggleable Italian translations,
  2. **Listen (`🔊 Ascolta`)** to the dialogue spoken aloud turn-by-turn,
  3. **Start Live Roleplay (`🎙️ Parla nella Scena`)** with Frau Blücher, where the ADK agent greets the user with the first line of the scene and tracks which scene vocabulary words the user actively uses.

### FR-4: ADK Tooling & Trajectory Evaluations ("Evals Along the Way")
- New ADK tool on `HummerliToolset`:
  - `get_scene_vocabulary_and_dialogue(profile_id: str, scenario_id: str) -> dict` returning both the `hotspots` (with arrow coordinates) and `sample_conversation` (with highlighted B1 words).
- New A2UI v0.9 widget `InteractiveSceneExplorerCard` supporting the two mode buttons (`1. Vocabulary` and `2. Sample Conversation`).
- New trajectory evaluation fixture `tests/evals/trajectories/scene_vocab_and_sample_convo.test.json`.

---

## 3. Acceptance Criteria
- [ ] Every scenario exposes the 2 primary buttons: **`1. Vocabulary`** and **`2. Sample Conversation`**.
- [ ] Clicking **`1. Vocabulary`** displays the words in a chip bar AND draws SVG arrows ("freccine") pointing to the corresponding elements inside the scene image, color-coded by grammatical gender.
- [ ] Clicking **`2. Sample Conversation`** displays a realistic B1 dialogue (like the park dog-walking example) with target words in **bold + color**, Italian translation, 2-voice TTS playback, and 1-click handoff to live conversation with Frau Blücher.
- [ ] All unit and ADK trajectory tests pass (`PYTHONPATH=src .venv/bin/pytest`).
