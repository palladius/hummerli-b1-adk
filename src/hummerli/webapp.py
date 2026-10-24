"""Interactive Web & Mobile Voice Orb Application + Live Trajectory Studio for Hummerli."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from hummerli.agent import TurnTrajectory, create_hummerli_agent
from hummerli.eval.judge import BugRouter, JudgeAnalyzer, TurnVerdict, generate_daily_digest
from hummerli.eval.trajectory import run_all_trajectory_evals

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAJECTORIES_DIR = REPO_ROOT / "tests" / "evals" / "trajectories"


def call_gemini_live_llm(
    user_input: str,
    profile_ctx: dict[str, Any],
    due_words: list[dict[str, Any]],
    traj: TurnTrajectory,
    audio_b64: Optional[str] = None,
    audio_mime: str = "audio/webm",
) -> Optional[dict[str, str]]:
    """Calls Gemini Flash via REST API (if GEMINI_API_KEY is set) for natural B1 conversation + optional audio STT."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    target_list = ", ".join(
        f"{w['display_headword']} ({w['translation_it']})" for w in due_words
    )
    tool_summary = ", ".join(
        f"{tc.tool_name}({tc.tool_args})" for tc in traj.tool_calls
    )
    sys_prompt = (
        f"Du bist Frau Leonie Blücher 🐎, die herzliche Schweizer Hochdeutsch-Lehrerin (Niveau {profile_ctx.get('target_level', 'B1')}) "
        f"für {profile_ctx.get('display_name', 'Riccardo')} in Zürich.\n"
        f"Aktuelle Zielwörter aus dem Spaced-Repetition-System (SRS): {target_list}.\n"
        f"Bereits ausgeführte ADK-Tools in diesem Zug: {tool_summary}.\n"
        "WICHTIGE REGELN:\n"
        "1. Antworte kurz (2-3 Sätze), natürlich und mündlich sprechbar (wie in einem echten Telefonat).\n"
        "2. Sprich klares Standard-Hochdeutsch (NIEMALS Englisch!).\n"
        "3. Wenn der Nutzer auf Italienisch fragt oder 'Non ho capito' sagt, antworte zuerst kurz als '[Rijckard 🇮🇹]: ...' auf Italienisch und führe dann als '[Frau Blücher 🐎]: ...' auf Deutsch weiter.\n"
        "4. Wenn Audio mitgeschickt wurde, transkribiere zuerst genau, was der Nutzer gesagt hat.\n"
        'Antworte AUSSCHLIESSLICH als JSON-Objekt mit den Feldern: {"transcript": "...", "reply": "...", "language": "de" oder "it+de"}.'
    )

    parts: list[dict[str, Any]] = []
    if audio_b64:
        parts.append(
            {
                "inline_data": {
                    "mime_type": audio_mime,
                    "data": audio_b64,
                }
            }
        )
        parts.append(
            {
                "text": "Höre dir diese Sprachaufnahme des Lernenden an, transkribiere sie in 'transcript' und antworte als Frau Blücher (oder Rijckard + Frau Blücher) in 'reply'."
            }
        )
    else:
        parts.append({"text": f"Aussage des Lernenden: {user_input}"})

    payload = {
        "system_instruction": {"parts": [{"text": sys_prompt}]},
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.6,
            "responseMimeType": "application/json",
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            text = raw["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "reply" in parsed:
                return {
                    "transcript": str(parsed.get("transcript") or user_input),
                    "reply": str(parsed["reply"]),
                    "language": str(parsed.get("language") or traj.language),
                }
    except Exception:
        return None
    return None


class HummerliWebBackend:
    """Stateful backend powering the Hummerli Voice Orb App, SRS Heatmap, Live Chat, and Eval Studio."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        use_live_llm: bool = False,
    ) -> None:
        self.data_dir = data_dir
        self.use_live_llm = use_live_llm
        self.agent = create_hummerli_agent(data_dir=data_dir)
        self.judge = JudgeAnalyzer()
        self.bug_router = BugRouter()
        self.session_verdicts: dict[str, list[TurnVerdict]] = {
            "riccardo": [],
            "ale": [],
            "sebi": [],
        }

    def get_state(self, profile_id: str = "riccardo") -> dict[str, Any]:
        """Returns complete profile context, due words, full curriculum heatmap grid, and digest."""
        assert self.agent.toolset is not None
        toolset = self.agent.toolset
        ctx = toolset.get_profile_context(profile_id=profile_id)
        due_words = toolset.get_due_words(profile_id=profile_id, limit=3)

        profile = toolset.profile_manager.get_profile(profile_id)
        entries = toolset.curriculum_repo.load_curriculum(profile.curriculum)
        cards = toolset.srs_engine.load_state(profile_id)

        grid = []
        for entry in entries:
            card = cards.get(entry.lemma)
            grid.append(
                {
                    "lemma": entry.lemma,
                    "display_headword": entry.display_headword,
                    "pos": entry.pos,
                    "topic": entry.topic,
                    "translation_it": entry.translation_it,
                    "example_de": entry.example_de,
                    "status": card.status if card else "new",
                    "repetition_count": card.repetition_count if card else 0,
                    "interval_days": card.interval_days if card else 0,
                    "ease_factor": card.ease_factor if card else 2.5,
                    "last_score": card.last_score if card else None,
                    "history": [h.model_dump() for h in card.history] if card else [],
                }
            )

        verdicts = self.session_verdicts.get(profile_id, [])
        digest_md = generate_daily_digest(
            profile_id=profile_id,
            date_str=date.today().isoformat(),
            verdicts=verdicts,
            bug_router=self.bug_router,
        )

        return {
            "profile": ctx,
            "due_words": due_words,
            "curriculum_grid": grid,
            "digest_markdown": digest_md,
            "turns_count": len(verdicts),
            "live_llm_enabled": bool(self.use_live_llm and os.environ.get("GEMINI_API_KEY")),
        }

    def handle_chat(
        self,
        profile_id: str,
        query: str,
        is_session_start: bool = False,
        barge_in: bool = False,
        audio_b64: Optional[str] = None,
        audio_mime: str = "audio/webm",
    ) -> dict[str, Any]:
        """Runs a conversational turn (text or multimodal audio) through the ADK agent + Judge."""
        assert self.agent.toolset is not None
        profile_ctx = self.agent.toolset.get_profile_context(profile_id=profile_id)
        due_before = self.agent.toolset.get_due_words(profile_id=profile_id, limit=3)
        target_lemmata = [w["lemma"] for w in due_before]

        effective_query = query.strip()
        llm_override: Optional[dict[str, str]] = None
        if audio_b64 and self.use_live_llm:
            dummy_traj = TurnTrajectory(user_input=effective_query or "[Audio]", profile_id=profile_id)
            llm_override = call_gemini_live_llm(
                user_input=effective_query or "[Audio]",
                profile_ctx=profile_ctx,
                due_words=due_before,
                traj=dummy_traj,
                audio_b64=audio_b64,
                audio_mime=audio_mime,
            )
            if llm_override and llm_override.get("transcript"):
                effective_query = llm_override["transcript"]

        if not effective_query:
            effective_query = "Hallo Frau Blücher!"

        traj = self.agent.run_turn(
            user_input=effective_query,
            profile_id=profile_id,
            is_session_start=is_session_start,
            barge_in=barge_in,
        )

        if self.use_live_llm:
            if llm_override is None:
                llm_override = call_gemini_live_llm(
                    user_input=effective_query,
                    profile_ctx=profile_ctx,
                    due_words=due_before,
                    traj=traj,
                )
            if llm_override and llm_override.get("reply"):
                traj.final_response = llm_override["reply"]

        verdict = self.judge.evaluate_turn(
            traj,
            target_lemmata=target_lemmata,
            audio_gcs_uri=f"gs://hummerli-audio-vault/profiles/{profile_id}/sessions/{date.today().isoformat()}/turn_{len(self.session_verdicts.get(profile_id, [])) + 1:03d}.ogg",
        )
        self.session_verdicts.setdefault(profile_id, []).append(verdict)
        issues = self.bug_router.build_issues_from_verdict(verdict, is_personal_session=True)

        return {
            "trajectory": traj.model_dump(),
            "verdict": verdict.model_dump(),
            "issues": [iss.model_dump() for iss in issues],
            "state": self.get_state(profile_id=profile_id),
        }

    def simulate_flawed_turn(self, profile_id: str = "riccardo") -> dict[str, Any]:
        """Injects a flawed LLM turn (missing SRS tool call + English leak) to demonstrate Judge & BugRouter."""
        flawed_traj = TurnTrajectory(
            user_input="Ich habe gestern den Antrag bei der Gemeinde eingereicht.",
            profile_id=profile_id,
            active_persona="Frau Leonie Blücher",
            language="de",
            tool_calls=[],
            final_response="Great job Riccardo! Bravo!",
        )
        verdict = self.judge.evaluate_turn(
            flawed_traj,
            target_lemmata=["Antrag", "Gemeinde"],
            audio_gcs_uri=f"gs://hummerli-audio-vault/profiles/{profile_id}/sessions/{date.today().isoformat()}/flawed_turn.ogg",
        )
        self.session_verdicts.setdefault(profile_id, []).append(verdict)
        issues = self.bug_router.build_issues_from_verdict(verdict, is_personal_session=True)
        state = self.get_state(profile_id=profile_id)
        return {
            "trajectory": flawed_traj.model_dump(),
            "verdict": verdict.model_dump(),
            "issues": [iss.model_dump() for iss in issues],
            "digest_markdown": state["digest_markdown"],
            "state": state,
        }

    def run_evals(self) -> dict[str, Any]:
        """Executes all 4 ADK `.test.json` trajectory suites and returns the live scorecard."""
        return run_all_trajectory_evals(trajectories_dir=DEFAULT_TRAJECTORIES_DIR)


PWA_MANIFEST = {
    "name": "Hummerli B1 Voice Tutor",
    "short_name": "Hummerli 🐎",
    "description": "Frau Leonie Blücher & Rijckard — German B1 Oral Tutor & SRS",
    "start_url": "/?mode=orb",
    "display": "standalone",
    "background_color": "#0b1120",
    "theme_color": "#0284c7",
}

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <link rel="manifest" href="/manifest.json" />
  <title>🐎 Hummerli B1 — Pallino Vocale & Trajectory Studio</title>
  <style>
    :root {
      --bg: #0b1120;
      --panel: #1e293b;
      --panel-alt: #263349;
      --text: #f8fafc;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --swiss-red: #ef4444;
      --green: #22c55e;
      --yellow: #eab308;
      --border: #334155;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 20px;
      background: #070b14;
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
      gap: 10px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 700;
      font-size: 1.1rem;
    }
    .badge {
      padding: 3px 10px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
      background: var(--panel-alt);
      color: var(--accent);
      border: 1px solid var(--border);
    }
    .controls {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    select, button, input {
      background: var(--panel);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 0.88rem;
      cursor: pointer;
    }
    button:hover { border-color: var(--accent); }
    button.primary {
      background: #0284c7;
      border-color: #38bdf8;
      font-weight: 600;
    }
    button.mode-btn.active {
      background: var(--accent);
      color: #0b1120;
      font-weight: 700;
    }

    /* ================= ORB VIEW (PHONE & DESKTOP VOICE APP) ================= */
    #orbView {
      display: none;
      flex: 1;
      flex-direction: column;
      align-items: center;
      justify-content: space-between;
      padding: 20px 16px 28px;
      max-width: 540px;
      width: 100%;
      margin: 0 auto;
      text-align: center;
    }
    .orb-due-box {
      width: 100%;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 12px;
    }
    .orb-center-stage {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 18px;
      margin: 20px 0;
    }
    .mic-orb {
      width: 190px;
      height: 190px;
      border-radius: 50%;
      border: none;
      background: radial-gradient(circle at 35% 30%, #38bdf8, #0284c7 60%, #0369a1 100%);
      box-shadow: 0 0 45px rgba(56, 189, 248, 0.45), inset 0 0 25px rgba(255, 255, 255, 0.25);
      color: white;
      font-size: 4.2rem;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.25s, background 0.25s;
      user-select: none;
      -webkit-tap-highlight-color: transparent;
    }
    .mic-orb:hover { transform: scale(1.04); }
    .mic-orb:active { transform: scale(0.96); }
    .mic-orb.listening {
      background: radial-gradient(circle at 35% 30%, #f87171, #ef4444 60%, #991b1b 100%);
      box-shadow: 0 0 70px rgba(239, 68, 68, 0.8), 0 0 120px rgba(239, 68, 68, 0.4);
      animation: pulseOrb 1.2s infinite ease-in-out;
    }
    .mic-orb.speaking {
      background: radial-gradient(circle at 35% 30%, #4ade80, #16a34a 60%, #15803d 100%);
      box-shadow: 0 0 65px rgba(34, 197, 94, 0.75);
      animation: pulseOrb 1.6s infinite ease-in-out;
    }
    .mic-orb.thinking {
      background: radial-gradient(circle at 35% 30%, #facc15, #ca8a04 60%, #854d0e 100%);
      box-shadow: 0 0 55px rgba(234, 179, 8, 0.65);
    }
    @keyframes pulseOrb {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.09); }
    }
    .orb-status {
      font-size: 1.05rem;
      font-weight: 600;
      color: var(--accent);
    }
    .orb-substatus {
      font-size: 0.82rem;
      color: var(--muted);
      margin-top: -10px;
    }
    .orb-transcript-card {
      width: 100%;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      text-align: left;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    /* ================= STUDIO 3-COLUMN VIEW ================= */
    .layout {
      display: grid;
      grid-template-columns: 1.15fr 1fr 1.05fr;
      gap: 16px;
      padding: 16px 24px;
      max-width: 1800px;
      margin: 0 auto;
      width: 100%;
    }
    @media (max-width: 1280px) {
      .layout { grid-template-columns: 1fr; }
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .card h2 {
      margin: 0;
      font-size: 1.02rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 8px;
    }
    .scenario-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .scenario-bar button {
      font-size: 0.76rem;
      padding: 5px 10px;
      background: var(--panel-alt);
    }
    .chat-box {
      height: 390px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 10px;
      background: #070b14;
      border-radius: 8px;
      border: 1px solid var(--border);
    }
    .msg {
      padding: 10px 13px;
      border-radius: 10px;
      max-width: 90%;
      font-size: 0.92rem;
      white-space: pre-wrap;
    }
    .msg.user { align-self: flex-end; background: #0369a1; }
    .msg.tutor { align-self: flex-start; background: var(--panel-alt); border-left: 4px solid var(--accent); }
    .msg.coach { align-self: flex-start; background: #1e3a2f; border-left: 4px solid var(--green); }
    .msg-meta { font-size: 0.72rem; color: var(--muted); margin-bottom: 4px; }
    .chat-input-row { display: flex; gap: 8px; }
    .chat-input-row input { flex: 1; cursor: text; }
    .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
    .stat-pill {
      background: #070b14;
      padding: 8px 10px;
      border-radius: 8px;
      text-align: center;
      border: 1px solid var(--border);
    }
    .stat-pill .num { font-size: 1.2rem; font-weight: 700; }
    .stat-pill .lbl { font-size: 0.72rem; color: var(--muted); }
    .heatmap-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(125px, 1fr));
      gap: 8px;
      max-height: 410px;
      overflow-y: auto;
      padding: 4px;
    }
    .word-tile {
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: #070b14;
      cursor: pointer;
    }
    .word-tile.mastered { background: rgba(34, 197, 94, 0.18); border-color: var(--green); }
    .word-tile.learning { background: rgba(234, 179, 8, 0.18); border-color: var(--yellow); }
    .word-tile.struggling { background: rgba(239, 68, 68, 0.24); border-color: var(--swiss-red); }
    .word-tile .hw { font-weight: 600; font-size: 0.86rem; }
    .word-tile .it { font-size: 0.74rem; color: var(--muted); }
    .word-tile .iv { font-size: 0.7rem; margin-top: 4px; color: var(--accent); }
    pre.code-box {
      background: #070b14;
      padding: 10px;
      border-radius: 8px;
      border: 1px solid var(--border);
      font-size: 0.76rem;
      overflow-x: auto;
      max-height: 210px;
      margin: 0;
      color: #e2e8f0;
    }
    .due-list { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
    .due-chip {
      background: rgba(56, 189, 248, 0.14);
      border: 1px solid var(--accent);
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.8rem;
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span>🐎🇨🇭 Hummerli</span>
      <span class="badge" id="profileBadge">Riccardo · B1</span>
      <span class="badge" id="llmModeBadge">ADK + Gemini Live</span>
    </div>
    <div class="controls">
      <button class="mode-btn active" id="btnModeOrb" onclick="setViewMode('orb')">🎙️ Pallino Vocale (App)</button>
      <button class="mode-btn" id="btnModeStudio" onclick="setViewMode('studio')">🔬 Studio 3-Colonne</button>
      <select id="profileSelect" onchange="switchProfile()">
        <option value="riccardo">🇨🇭 Riccardo (B1 Zürich)</option>
        <option value="ale">👦 Alessandro (P3)</option>
        <option value="sebi">🧒 Sebastian (P1)</option>
      </select>
      <label style="font-size:0.8rem;display:flex;align-items:center;gap:4px;">
        <input type="checkbox" id="ttsToggle" checked /> 🔊 Voce
      </label>
    </div>
  </header>

  <!-- ==================== VIEW 1: PALLINO DA MICROFONO (ORB APP) ==================== -->
  <section id="orbView">
    <div class="orb-due-box">
      <div style="font-size:0.78rem;color:var(--muted);margin-bottom:6px;">🎯 Parole B1 di oggi da usare nella conversazione:</div>
      <div class="due-list" id="orbDueWords"></div>
    </div>

    <div class="orb-center-stage">
      <button class="mic-orb" id="micOrbBtn" onclick="toggleOrbTap()">🎙️</button>
      <div class="orb-status" id="orbStatusText">Tocca il Pallino per parlare con Frau Blücher</div>
      <div class="orb-substatus" id="orbSubStatusText">Parla in Tedesco B1 o chiedi aiuto in Italiano ("Non ho capito...")</div>
    </div>

    <div class="orb-transcript-card">
      <div>
        <div style="font-size:0.74rem;color:var(--muted);">🗣️ Tu hai detto:</div>
        <div id="orbUserText" style="font-size:0.95rem;font-weight:500;">—</div>
      </div>
      <div style="border-top:1px solid var(--border);padding-top:8px;">
        <div style="font-size:0.74rem;color:var(--accent);" id="orbTutorLabel">🤖 Frau Leonie Blücher 🐎:</div>
        <div id="orbTutorText" style="font-size:0.98rem;">Grüezi Riccardo! Tocca il pallino o scrivi qui sotto per iniziare.</div>
      </div>
      <div class="chat-input-row" style="margin-top:6px;">
        <input type="text" id="orbTextInput" placeholder="Oppure scrivi/detta qui in tedesco o italiano..." onkeydown="if(event.key==='Enter') sendFromOrbInput()" />
        <button class="primary" onclick="sendFromOrbInput()">Invia</button>
      </div>
    </div>
  </section>

  <!-- ==================== VIEW 2: STUDIO 3 COLONNE ==================== -->
  <main class="layout" id="studioView">
    <section class="card">
      <h2>
        <span>🎙️ Conversazione Live (Frau Blücher & Rijckard)</span>
        <span class="badge" id="activeVoiceBadge">de-DE-Neural2-F</span>
      </h2>

      <div style="font-size:0.78rem;color:var(--muted);">Scenari Rapidi (1-Click Trajectory Test):</div>
      <div class="scenario-bar">
        <button onclick="sendQuick('Hallo Frau Blücher, starten wir eine neue Übung für heute!', true)">1️⃣ Inizia Sessione B1</button>
        <button onclick="sendQuick('Ich muss heute Nachmittag meine Kinder von der Schule abholen.', false)">2️⃣ Usa 'abholen' (q=5)</button>
        <button onclick="sendQuick('Scusa, non ho capito cosa significa Antrag in questo contesto.', false)">3️⃣ 'Non ho capito Antrag' (Rijckard 🇮🇹)</button>
        <button onclick="sendQuick('Non ricordo cosa vuol dire Behörde, me lo spieghi in italiano?', false)">4️⃣ 'Non ricordo Behörde' (Reset 🔴)</button>
        <button onclick="triggerFlawedTurn()" style="border-color:#ef4444;color:#fca5a5;">5️⃣ Simula Bug LLM (Judge)</button>
      </div>

      <div>
        <span style="font-size:0.78rem;color:var(--muted);">Parole target della sessione (`get_due_words`):</span>
        <div class="due-list" id="dueWordsBar" style="margin-top:4px;justify-content:flex-start;"></div>
      </div>

      <div class="chat-box" id="chatBox"></div>

      <div class="chat-input-row">
        <button onclick="toggleOrbTap()" id="micBtn">🎤 Parla</button>
        <input type="text" id="chatInput" placeholder="Scrivi o parla in Tedesco o Italiano..." onkeydown="if(event.key==='Enter') sendChat()" />
        <button class="primary" onclick="sendChat()">Invia</button>
      </div>
    </section>

    <section class="card">
      <h2>
        <span>🗺️ Goethe B1 Wortliste SRS Heatmap (SM-2)</span>
        <span class="badge" id="curriculumNameBadge">goethe_b1</span>
      </h2>

      <div class="stats-row">
        <div class="stat-pill"><div class="num" style="color:var(--green)" id="cntMastered">0</div><div class="lbl">🟢 Mastered</div></div>
        <div class="stat-pill"><div class="num" style="color:var(--yellow)" id="cntLearning">0</div><div class="lbl">🟡 Learning</div></div>
        <div class="stat-pill"><div class="num" style="color:var(--swiss-red)" id="cntStruggling">0</div><div class="lbl">🔴 Struggling</div></div>
        <div class="stat-pill"><div class="num" id="cntUnseen">0</div><div class="lbl">⚪ Unseen</div></div>
      </div>

      <div class="heatmap-grid" id="heatmapGrid"></div>

      <div id="wordDetailBox" style="font-size:0.82rem;background:#070b14;padding:10px;border-radius:8px;border:1px solid var(--border);">
        💡 <em>Clicca su qualsiasi tessera del vocabolario per vedere la frase d'esempio B1, l'intervallo SM-2 e lo storico dei tuoi tentativi.</em>
      </div>
    </section>

    <section class="card">
      <h2>
        <span>🔬 ADK Trajectory & Level-2 LLM-as-Judge</span>
        <button class="primary" style="padding:4px 10px;font-size:0.76rem;" onclick="runAllEvals()">🧪 Esegui 4 Suite EVAL</button>
      </h2>
      <div><span class="badge" id="verdictBadge">In attesa</span></div>

      <div style="font-size:0.8rem;color:var(--muted);">Ultimo Turno — Tool ADK Chiamati (`TurnTrajectory.tool_calls`):</div>
      <pre class="code-box" id="trajectoryBox">Nessun turno ancora eseguito.</pre>

      <div style="font-size:0.8rem;color:var(--muted);">Level-2 Judge Verdict & Dual-Repo Bug Router (`public` vs `pvt`):</div>
      <pre class="code-box" id="judgeBox"></pre>

      <div style="font-size:0.8rem;color:var(--muted);">📋 Daily Digest Markdown & Risultati Suite EVAL:</div>
      <pre class="code-box" id="digestBox" style="max-height:220px;"></pre>
    </section>
  </main>

  <script>
    let currentProfile = 'riccardo';
    let orbState = 'idle';
    let activeRecognition = null;
    let mediaRecorder = null;
    let audioChunks = [];

    function setViewMode(mode) {
      const orbView = document.getElementById('orbView');
      const studioView = document.getElementById('studioView');
      const btnOrb = document.getElementById('btnModeOrb');
      const btnStudio = document.getElementById('btnModeStudio');
      if (mode === 'orb') {
        orbView.style.display = 'flex';
        studioView.style.display = 'none';
        btnOrb.classList.add('active');
        btnStudio.classList.remove('active');
      } else {
        orbView.style.display = 'none';
        studioView.style.display = 'grid';
        btnOrb.classList.remove('active');
        btnStudio.classList.add('active');
      }
    }

    function setOrbVisualState(state, statusText, subText) {
      orbState = state;
      const orb = document.getElementById('micOrbBtn');
      orb.className = `mic-orb ${state === 'idle' ? '' : state}`;
      if (state === 'idle') {
        orb.textContent = '🎙️';
        document.getElementById('orbStatusText').textContent = statusText || 'Tocca il Pallino per parlare con Frau Blücher';
        document.getElementById('orbSubStatusText').textContent = subText || 'Parla in Tedesco B1 o chiedi aiuto in Italiano ("Non ho capito...")';
      } else if (state === 'listening') {
        orb.textContent = '⏹️';
        document.getElementById('orbStatusText').textContent = statusText || '🔴 Ti ascolto... (Tocca per inviare)';
        document.getElementById('orbSubStatusText').textContent = subText || 'Parla liberamente in Hochdeutsch o Italiano';
      } else if (state === 'thinking') {
        orb.textContent = '⏳';
        document.getElementById('orbStatusText').textContent = statusText || '🧠 Frau Blücher & ADK elaborano...';
        document.getElementById('orbSubStatusText').textContent = subText || 'Aggiornamento SRS SM-2 e valutazione traiettoria...';
      } else if (state === 'speaking') {
        orb.textContent = '🔊';
        document.getElementById('orbStatusText').textContent = statusText || '🗣️ Frau Blücher sta parlando (Tocca per Barge-In!)';
        document.getElementById('orbSubStatusText').textContent = subText || 'Tocca il pallino in qualsiasi momento per interromperla e parlare tu';
      }
    }

    async function loadState() {
      const res = await fetch(`/api/state?profile=${currentProfile}`);
      const data = await res.json();
      renderState(data);
    }

    function renderState(data) {
      const p = data.profile;
      const hm = p.srs_heatmap;
      document.getElementById('profileBadge').textContent = `${p.display_name} · ${p.target_level}`;
      document.getElementById('llmModeBadge').textContent = data.live_llm_enabled ? '🟢 Gemini Live + ADK' : '⚡ ADK Deterministic';
      document.getElementById('curriculumNameBadge').textContent = p.curriculum;
      document.getElementById('cntMastered').textContent = hm.mastered_green;
      document.getElementById('cntLearning').textContent = hm.learning_yellow;
      document.getElementById('cntStruggling').textContent = hm.struggling_red;
      document.getElementById('cntUnseen').textContent = hm.unseen;

      ['dueWordsBar', 'orbDueWords'].forEach(id => {
        const bar = document.getElementById(id);
        bar.innerHTML = '';
        data.due_words.forEach(w => {
          const chip = document.createElement('span');
          chip.className = 'due-chip';
          chip.textContent = `${w.display_headword} (${w.translation_it})`;
          bar.appendChild(chip);
        });
      });

      const grid = document.getElementById('heatmapGrid');
      grid.innerHTML = '';
      data.curriculum_grid.forEach(item => {
        const tile = document.createElement('div');
        tile.className = `word-tile ${item.status}`;
        tile.innerHTML = `
          <div class="hw">${item.display_headword}</div>
          <div class="it">${item.translation_it}</div>
          <div class="iv">Int: ${item.interval_days}d · Rep: ${item.repetition_count}</div>
        `;
        tile.onclick = () => showWordDetail(item);
        grid.appendChild(tile);
      });

      document.getElementById('digestBox').textContent = data.digest_markdown;
    }

    function showWordDetail(item) {
      const box = document.getElementById('wordDetailBox');
      const hist = item.history.length
        ? item.history.map(h => `• [q=${h.quality}] "${h.user_sentence}" → ${h.tutor_comment}`).join('<br/>')
        : '<em>Nessun tentativo registrato finora.</em>';
      box.innerHTML = `
        <strong>${item.display_headword}</strong> (${item.pos}, <em>${item.topic}</em>) — 🇮🇹 ${item.translation_it}<br/>
        🇩🇪 <em>"${item.example_de}"</em><br/>
        📊 Stato: <strong>${item.status.toUpperCase()}</strong> | Intervallo: <strong>${item.interval_days} giorni</strong> | Ease Factor: ${item.ease_factor}<br/>
        <div style="margin-top:6px;color:var(--muted);">${hist}</div>
      `;
    }

    function appendChatMessage(role, persona, text) {
      const box = document.getElementById('chatBox');
      const div = document.createElement('div');
      div.className = `msg ${role}`;
      div.innerHTML = `<div class="msg-meta">${persona}</div><div>${text}</div>`;
      box.appendChild(div);
      box.scrollTop = box.scrollHeight;
    }

    function speakText(text, lang) {
      if (!document.getElementById('ttsToggle').checked || !('speechSynthesis' in window)) {
        setOrbVisualState('idle');
        return;
      }
      window.speechSynthesis.cancel();
      const cleanText = text.replace(/\\[.*?\\]:/g, '').replace(/\\*\\*/g, '');
      const u = new SpeechSynthesisUtterance(cleanText);
      u.lang = lang.includes('it') ? 'it-IT' : 'de-DE';
      u.onstart = () => setOrbVisualState('speaking');
      u.onend = () => setOrbVisualState('idle');
      u.onerror = () => setOrbVisualState('idle');
      window.speechSynthesis.speak(u);
    }

    function bargeIn() {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      setOrbVisualState('idle', '🛑 Barge-In! Frau Blücher fermata.', 'Tocca o parla subito');
    }

    async function toggleOrbTap() {
      if (orbState === 'speaking') {
        bargeIn();
      }
      if (orbState === 'listening') {
        if (activeRecognition) {
          activeRecognition.stop();
          activeRecognition = null;
        }
        if (mediaRecorder && mediaRecorder.state === 'recording') {
          mediaRecorder.stop();
        }
        return;
      }

      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRec) {
        const rec = new SpeechRec();
        activeRecognition = rec;
        rec.lang = 'de-DE';
        rec.interimResults = true;
        setOrbVisualState('listening');
        let finalTranscript = '';

        rec.onresult = (e) => {
          let interim = '';
          for (let i = e.resultIndex; i < e.results.length; ++i) {
            if (e.results[i].isFinal) {
              finalTranscript += e.results[i][0].transcript;
            } else {
              interim += e.results[i][0].transcript;
            }
          }
          document.getElementById('orbUserText').textContent = finalTranscript || interim || '...';
        };
        rec.onerror = () => {
          activeRecognition = null;
          setOrbVisualState('idle');
        };
        rec.onend = async () => {
          activeRecognition = null;
          const spoken = (finalTranscript || document.getElementById('orbUserText').textContent || '').trim();
          if (spoken && spoken !== '—' && spoken !== '...') {
            document.getElementById('chatInput').value = spoken;
            await sendChat(false);
          } else {
            setOrbVisualState('idle');
          }
        };
        rec.start();
        return;
      }

      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          audioChunks = [];
          mediaRecorder = new MediaRecorder(stream);
          mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
          mediaRecorder.onstop = async () => {
            stream.getTracks().forEach(t => t.stop());
            const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
            const reader = new FileReader();
            reader.onloadend = async () => {
              const b64 = reader.result.split(',')[1];
              await sendAudioTurn(b64, blob.type || 'audio/webm');
            };
            reader.readAsDataURL(blob);
          };
          setOrbVisualState('listening');
          mediaRecorder.start();
        } catch (err) {
          document.getElementById('orbTextInput').focus();
          setOrbVisualState('idle', 'Usa il microfono della tastiera qui sotto 👇', 'Su connessione HTTP da telefono, usa la dettatura vocale della tastiera');
        }
      } else {
        document.getElementById('orbTextInput').focus();
        setOrbVisualState('idle', 'Usa il microfono della tastiera qui sotto 👇', 'Su connessione HTTP da telefono, usa la dettatura vocale della tastiera');
      }
    }

    async function sendAudioTurn(audioB64, audioMime) {
      setOrbVisualState('thinking');
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile_id: currentProfile,
          query: '',
          is_session_start: false,
          audio_b64: audioB64,
          audio_mime: audioMime
        })
      });
      const data = await res.json();
      handleTurnResponse(data);
    }

    async function sendFromOrbInput() {
      const inp = document.getElementById('orbTextInput');
      const q = inp.value.trim();
      if (!q) return;
      inp.value = '';
      document.getElementById('chatInput').value = q;
      await sendChat(false);
    }

    async function sendQuick(query, isStart) {
      document.getElementById('chatInput').value = query;
      await sendChat(isStart);
    }

    async function sendChat(isStart = false) {
      const input = document.getElementById('chatInput');
      const query = input.value.trim();
      if (!query) return;
      input.value = '';
      document.getElementById('orbUserText').textContent = query;
      appendChatMessage('user', `🗣️ ${currentProfile}`, query);
      setOrbVisualState('thinking');

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id: currentProfile, query, is_session_start: isStart })
      });
      const data = await res.json();
      handleTurnResponse(data);
    }

    function handleTurnResponse(data) {
      const traj = data.trajectory;
      document.getElementById('orbUserText').textContent = traj.user_input;
      document.getElementById('orbTutorLabel').textContent = `🤖 ${traj.active_persona} (${traj.voice}):`;
      document.getElementById('orbTutorText').textContent = traj.final_response;

      const roleClass = traj.language.includes('it') ? 'coach' : 'tutor';
      appendChatMessage(roleClass, `🤖 ${traj.active_persona} (${traj.voice})`, traj.final_response);
      document.getElementById('activeVoiceBadge').textContent = traj.voice;

      speakText(traj.final_response, traj.language);
      updateInspector(data);
      renderState(data.state);
    }

    async function triggerFlawedTurn() {
      appendChatMessage('user', `🗣️ ${currentProfile} (Test Judge)`, 'Ich habe gestern den Antrag bei der Gemeinde eingereicht.');
      const res = await fetch('/api/simulate_flawed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id: currentProfile })
      });
      const data = await res.json();
      appendChatMessage('tutor', '🤖 Frau Blücher (Simulazione Turno Difettoso)', data.trajectory.final_response);
      updateInspector(data);
      renderState(data.state);
    }

    function updateInspector(data) {
      document.getElementById('trajectoryBox').textContent = JSON.stringify(data.trajectory.tool_calls, null, 2);
      const vBadge = document.getElementById('verdictBadge');
      if (data.verdict.passed) {
        vBadge.textContent = `✅ PASS (Score ${data.verdict.score})`;
        vBadge.style.color = '#22c55e';
      } else {
        vBadge.textContent = `❌ FAIL (${data.verdict.anomalies.length} anomalie)`;
        vBadge.style.color = '#ef4444';
      }
      document.getElementById('judgeBox').textContent = JSON.stringify({
        passed: data.verdict.passed,
        score: data.verdict.score,
        anomalies: data.verdict.anomalies,
        routed_github_issues: data.issues
      }, null, 2);
    }

    async function runAllEvals() {
      const box = document.getElementById('digestBox');
      box.textContent = '⏳ Esecuzione delle 4 suite ADK Trajectory Evaluation in corso...';
      const res = await fetch('/api/eval', { method: 'POST' });
      const summary = await res.json();
      box.textContent = JSON.stringify(summary, null, 2);
      const vBadge = document.getElementById('verdictBadge');
      vBadge.textContent = `🧪 EVALS: ${summary.status} (Score ${summary.overall_tool_trajectory_score})`;
      vBadge.style.color = '#38bdf8';
    }

    function switchProfile() {
      currentProfile = document.getElementById('profileSelect').value;
      document.getElementById('chatBox').innerHTML = '';
      loadState();
    }

    window.addEventListener('DOMContentLoaded', async () => {
      const params = new URLSearchParams(window.location.search);
      const initialMode = params.get('mode') === 'studio' ? 'studio' : 'orb';
      setViewMode(initialMode);
      await loadState();
      await sendQuick('Hallo Frau Blücher, starten wir eine neue Übung für heute!', true);
    });
  </script>
</body>
</html>
"""


def make_handler(backend: HummerliWebBackend) -> type[BaseHTTPRequestHandler]:
    """Creates an HTTP handler class bound to the given HummerliWebBackend instance."""

    class HummerliHTTPHandler(BaseHTTPRequestHandler):
        def _send_json(self, payload: Any, status: int = 200) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _send_html(self, html: str, status: int = 200) -> None:
            raw = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html", "/orb"}:
                self._send_html(DASHBOARD_HTML)
                return
            if parsed.path == "/manifest.json":
                self._send_json(PWA_MANIFEST)
                return
            if parsed.path == "/api/state":
                qs = parse_qs(parsed.query)
                profile_id = qs.get("profile", ["riccardo"])[0]
                self._send_json(backend.get_state(profile_id=profile_id))
                return
            self._send_json({"error": "Not found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0"))
            body_raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            payload = json.loads(body_raw) if body_raw else {}

            if parsed.path == "/api/chat":
                res = backend.handle_chat(
                    profile_id=payload.get("profile_id", "riccardo"),
                    query=payload.get("query", ""),
                    is_session_start=bool(payload.get("is_session_start", False)),
                    barge_in=bool(payload.get("barge_in", False)),
                    audio_b64=payload.get("audio_b64"),
                    audio_mime=payload.get("audio_mime", "audio/webm"),
                )
                self._send_json(res)
                return
            if parsed.path == "/api/simulate_flawed":
                res = backend.simulate_flawed_turn(
                    profile_id=payload.get("profile_id", "riccardo")
                )
                self._send_json(res)
                return
            if parsed.path == "/api/eval":
                self._send_json(backend.run_evals())
                return
            self._send_json({"error": "Not found"}, status=404)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    return HummerliHTTPHandler


def run_web_server(
    host: str = "0.0.0.0",
    port: int = 8788,
    data_dir: Optional[Path] = None,
    use_live_llm: bool = True,
) -> None:
    """Starts the Hummerli Web & Voice Orb HTTP server (bound to 0.0.0.0 for LAN/Tailscale Phone access)."""
    backend = HummerliWebBackend(data_dir=data_dir, use_live_llm=use_live_llm)
    handler_cls = make_handler(backend)
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((host, port), handler_cls)
    print(f"🐎 Hummerli Voice Orb & Studio listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
