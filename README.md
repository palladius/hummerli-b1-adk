# 🦞🐎 Hummerli (`hummerli-b1-adk`)

**Autonomous Google ADK German B1 Oral Tutor, Bidirectional Barge-In Engine, Spaced Repetition (SRS) & Trajectory Evaluation Datalake**

Built for **Riccardo's Swiss Naturalization B1 Oral Exam Prep (FIDE — Hören & Sprechen)** in the Canton of Zurich, with multi-profile support for Alessandro (Primary 3) and Sebastian (Primary 1).

---

## ✨ Key Architecture

1. **Dual-Persona ADK Agent Orchestration**:
   - **Frau Leonie Blücher 🐎 (`frau_bluecher`)**: Patient, clear Standard High German (*Hochdeutsch* B1) tutor (`de-DE-Neural2-F` / Gemini Live native audio). Organically weaves 1–3 due Goethe B1 lemmata into Zurich civic and daily-life conversations.
   - **Rijckard (`rijckard_coach`)**: Warm Italian coach (`it-IT-Neural2-C`) intervening *exclusively* when the learner signals confusion (*"Non ho capito"*, *"Wie bitte?"*, or explicit grammar questions), then immediately handing the floor back to Frau Blücher.
2. **Goethe B1 Wortliste SRS Engine (`hummerli.srs`)**:
   - SuperMemo SM-2 / Leitner scheduler over the Goethe-Zertifikat B1 vocabulary.
   - Mastered words expand through `1d → 7d → 15d → 30d → 90d` intervals; missed words (`q < 3`) reset to immediate reinforcement (*"la lingua batte dove il dente duole"*).
3. **Two-Level Trajectory Evaluation & Closed-Loop Bug Filing (`hummerli.eval`)**:
   - **Level 1 (Harness / Tool Trajectory)**: Deterministic & ADK `.test.json` / `.evalset.json` trajectory evaluations verifying exact tool call sequences (`get_profile_context` → `get_due_words` → `record_word_attempt` / `explain_in_italian`).
   - **Level 2 (Pedagogical & Harness LLM-as-Judge)**: Evaluates transcripts & trajectories, generates daily Markdown digests, and automatically routes bugs:
     - 🔧 **Harness/code bugs** (synthetic, no PII) → [`palladius/hummerli-b1-adk`](https://github.com/palladius/hummerli-b1-adk) (Public)
     - 🔐 **Personal transcript / audio / model bugs** → `palladius/hummerli-b1-adk-pvt` (Private companion repo)

---

## 🔐 Secrets & Privacy Hygiene

- Copy `.env.dist` to `.env` and populate your keys locally.
- **NEVER** commit `.env`, `sa.json`, or raw audio files (`.ogg`, `.wav`, `.mp3`).
- Raw audio lives in `gs://hummerli-audio-vault/` and personal session evaluations live in `hummerli-b1-adk-pvt`.

---

## 🚀 Quickstart

```bash
# Run unit tests + ADK trajectory evaluations
just test

# Run trajectory evaluations and export Markdown report
just eval-report

# Inspect Goethe B1 SRS queue for Riccardo
just srs riccardo

# Generate a Daily Judge Evaluation Digest
just digest riccardo
```
