# Technology Stack — Hummerli

## Overview

Hummerli is built as a pure **Google Agent Development Kit (ADK)** Python application featuring bidirectional real-time audio streaming, an SM-2 Spaced Repetition System (SRS) engine over the Goethe-Zertifikat B1 vocabulary, a GCS-backed datalake, and a **two-tier LLM-as-Judge Trajectory Evaluation & Auto-Bug-Filing Pipeline**.

---

## Core Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.12+ | First-class support for Google ADK, async WebSockets, DuckDB, and ML/eval tooling. |
| **Package & Env Manager** | `uv` + `pyproject.toml` | Fast, reproducible dependency resolution and execution (`uv run`). |
| **Agent Framework** | **Google ADK (`google-adk`)** | Native multi-agent orchestration (`LlmAgent`), session state, tool calling, and native `AgentEvaluator` trajectory testing. |
| **Live Voice & Barge-In** | **Gemini Multimodal Live API** (`google-genai`) | Full-duplex WebSocket streaming with built-in Voice Activity Detection (VAD) for zero-latency barge-in interruption. |
| **Text-to-Speech (TTS)** | **Google Cloud TTS Neural2** & Gemini Native Audio | `de-DE-Neural2-F` for **Frau Leonie Blücher 🐎** (German tutor) and `it-IT-Neural2-C` for **Rijckard** (Italian coach). |
| **SRS & Local Analytics** | **JSON + DuckDB + Parquet** | Fast local state (`srs_state.json`) paired with analytical queries over Parquet session logs. |
| **Cloud Storage & Vault** | **Google Cloud Storage (GCS)** | `gs://hummerli-audio-vault/` stores 100% of raw user/tutor audio and telemetry mirrors. |
| **Interfaces (MVP)** | **Web Client** (WebSockets + Vanilla JS), **Telegram Bot** (`python-telegram-bot`), **CLI** (`typer` / `rich`) | Desktop full-duplex barge-in, mobile async voice-memo practice, and terminal-based rapid testing/replay. |
| **Analytics Dashboard** | **Astro + Tailwind CSS** | Static/SSR dashboard rendering vocabulary mastery heatmaps (🟢🟡🔴) and daily trajectory eval scores. |
| **Testing & Quality** | `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff` | Unit, integration, and deterministic trajectory verification. |

---

## 🛤️ Evaluation & Trajectory Testing Architecture (Eval-First)

Evaluation is a first-class citizen tested continuously alongside every feature ("Evals along the way"):

### 1. Two-Level Evaluation Taxonomy

| Level | Scope | What is Tested / Evaluated | Tooling |
|---|---|---|---|
| **Level 1: Deterministic & ADK Trajectory Evals** | Harness & Tool Calling (`tool_trajectory_avg_score`) | Does the agent call `get_due_words` at session start? Does it call `record_word_attempt` when Riccardo uses a target word? Does it switch to `rijckard_coach` when Riccardo says *"Non ho capito"*? | `google.adk.evaluation.AgentEvaluator` + `.test.json` / `.evalset.json` fixtures + `pytest` |
| **Level 2: Pedagogical & Linguistic LLM-as-Judge** | Tutor Quality & B1 Alignment (`response_match_score` + custom rubrics) | Did Frau Blücher stay within Goethe B1 vocabulary? Were grammar corrections accurate (no false positives)? Was feedback specific rather than vague? | Multi-Judge async worker (`gemini-2.5-pro` shadow judge) + Daily Digest generator |

### 2. Closed-Loop MLOps Feedback & Dual-Repo Bug Routing

```
Live / Replay Session → Trajectory & Audio captured
         ↓
Multi-Judge Evaluator (Harness Trajectory + Pedagogical Rubric)
         ↓
Root-Cause Classifier (harness | skill | model)
         ↓
Automated GitHub Issue Filing (`gh` CLI / PyGitHub):
  ├─ 🔧 Harness/Code Bug (synthetic repro, no PII)  ──► palladius/hummerli-b1-adk (PUBLIC)
  └─ 🔐 Session/Transcript/Audio Evidence Bug       ──► palladius/hummerli-b1-adk-pvt (PRIVATE)
```

- Once a private issue in `hummerli-b1-adk-pvt` is fixed, its trajectory is anonymized into a synthetic `.test.json` case in the public repo's `tests/evals/` folder so it never regresses.

---

## Curriculum Data Source Strategy (Goethe B1 Wortliste)

1. **Primary**: Automated parser/scraper for public Goethe-Zertifikat B1 Wortliste datasets (structured JSON/CSV with lemma, article, plural, example sentence, B1 category).
2. **Fallback 1**: Riccardo's Google Drive copy of the Goethe B1 word list.
3. **Fallback 2**: Curated seed dataset + LLM-verified B1 lemma expansion.

---

## Repository & Secrets Hygiene

- **Public Repo (`palladius/hummerli-b1-adk`)**: Code, ADK agents, SRS engine, synthetic trajectory evals (`tests/evals/*.test.json`), `.env.dist`. **Zero secrets, zero personal audio/transcripts.**
- **Private Companion Repo (`palladius/hummerli-b1-adk-pvt`)**: Personal session transcripts, daily judge digests, private bug reports with `gs://hummerli-audio-vault/` links, real-user `.evalset.json` replays.
- **Registry**: Both repositories are tracked in `/home/riccardo/git/gic/bin/repos-ricc`.
