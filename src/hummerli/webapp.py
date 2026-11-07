"""Interactive Web & Mobile Voice Orb Application + Visual Scenarios + Scene SVG Arrows
+ Noun Gender X-Ray (Ctrl+G / Double-Tap) + Oktoberfest Karaoke B2 & Duolingo 'Piano B' (Tracks 1–5).
"""

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

from hummerli.a2ui import HUMMERLI_A2UI_CATALOG_SCHEMA, build_a2ui_surface_for_turn
from hummerli.agent import TurnTrajectory, create_hummerli_agent
from hummerli.eval.judge import BugRouter, JudgeAnalyzer, TurnVerdict, generate_daily_digest
from hummerli.eval.trajectory import run_all_trajectory_evals
from hummerli.gender import GENDER_PALETTE, annotate_german_text

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAJECTORIES_DIR = REPO_ROOT / "tests" / "evals" / "trajectories"


def call_gemini_live_llm(
    user_input: str,
    profile_ctx: dict[str, Any],
    due_words: list[dict[str, Any]],
    traj: TurnTrajectory,
    audio_b64: Optional[str] = None,
    audio_mime: str = "audio/webm",
) -> Optional[dict[str, Any]]:
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
        f"5. A2UI v0.9 GENERATIVE UI CATALOG: Du kannst optional 1-2 passende UI-Widgets aus diesem Katalog in 'a2ui_components' zurückgeben: {json.dumps(HUMMERLI_A2UI_CATALOG_SCHEMA['widgets'], ensure_ascii=False)}\n"
        'Antworte AUSSCHLIESSLICH als JSON-Objekt mit den Feldern: {"transcript": "...", "reply": "...", "language": "de" oder "it+de", "a2ui_components": [{"type": "...", "props": {...}}]}.'
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
                    "a2ui_components": parsed.get("a2ui_components")
                    if isinstance(parsed.get("a2ui_components"), list)
                    else [],
                }
    except Exception:
        return None
    return None


class HummerliWebBackend:
    """Stateful backend powering Hummerli across Tracks 1–5."""

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

    def get_state(
        self,
        profile_id: str = "riccardo",
        client_layout: str = "mobile_portrait",
    ) -> dict[str, Any]:
        """Returns complete profile context, due words, scenarios, karaoke catalog, modality, and SRS heatmap."""
        assert self.agent.toolset is not None
        toolset = self.agent.toolset
        ctx = toolset.get_profile_context(profile_id=profile_id)
        due_words = toolset.get_due_words(profile_id=profile_id, limit=3)
        scenarios = toolset.generate_entropic_scenarios(
            profile_id=profile_id,
            count=3,
            client_layout=client_layout,
        )
        karaoke_songs = [s.model_dump() for s in toolset.karaoke_engine.list_songs()]
        modality = toolset.karaoke_engine.get_modality_preferences(profile_id=profile_id).model_dump()

        profile = toolset.profile_manager.get_profile(profile_id)
        entries = toolset.curriculum_repo.load_curriculum(profile.curriculum)
        cards = toolset.srs_engine.load_state(profile_id)

        grid = []
        for entry in entries:
            card = cards.get(entry.lemma)
            gender_ann = toolset.gender_resolver.resolve_word(entry.lemma, entry.article)
            grid.append(
                {
                    "lemma": entry.lemma,
                    "display_headword": entry.display_headword,
                    "pos": entry.pos,
                    "article": entry.article,
                    "gender_code": gender_ann.gender if gender_ann else None,
                    "gender_color_hex": gender_ann.color_hex if gender_ann else None,
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
            "scenarios": scenarios,
            "karaoke_songs": karaoke_songs,
            "modality": modality,
            "gender_palette": GENDER_PALETTE,
            "curriculum_grid": grid,
            "digest_markdown": digest_md,
            "turns_count": len(verdicts),
            "live_llm_enabled": bool(self.use_live_llm and os.environ.get("GEMINI_API_KEY")),
        }

    def mutate_scenario(
        self,
        profile_id: str,
        scenario_id: str,
        director_feedback_it: str,
        client_layout: str = "mobile_portrait",
    ) -> dict[str, Any]:
        """Track 2: Mutates the active scenario with Italian Director Notes."""
        assert self.agent.toolset is not None
        return self.agent.toolset.mutate_scenario_with_director_notes(
            profile_id=profile_id,
            current_scenario_id=scenario_id,
            director_feedback_it=director_feedback_it,
            client_layout=client_layout,
        )

    def get_scenario_detail(
        self,
        profile_id: str = "riccardo",
        scenario_id: str = "zuerich_park_hund",
        client_layout: str = "mobile_portrait",
    ) -> dict[str, Any]:
        """Track 3: Returns scenario with SVG arrow vocabulary hotspots and sample conversation."""
        assert self.agent.toolset is not None
        sc = self.agent.toolset.scenario_engine.get_scenario_by_id(
            scenario_id=scenario_id,
            profile_id=profile_id,
            client_layout="desktop_landscape" if client_layout == "desktop_landscape" else "mobile_portrait",
        )
        return sc.model_dump()

    def set_modality(
        self,
        profile_id: str = "riccardo",
        can_listen: bool = True,
        can_speak: bool = True,
    ) -> dict[str, Any]:
        """Track 5: Updates Duolingo-style 'Piano B' Silent / No-Mic modality."""
        assert self.agent.toolset is not None
        return self.agent.toolset.set_modality_preferences(
            profile_id=profile_id,
            can_listen=can_listen,
            can_speak=can_speak,
        )

    def start_karaoke(
        self,
        profile_id: str = "riccardo",
        song_id: str = "fliegerlied",
        mode: str = "stop_and_fill",
        can_listen: Optional[bool] = None,
        can_speak: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Track 5: Starts an Oktoberfest Karaoke B2 session."""
        assert self.agent.toolset is not None
        return self.agent.toolset.karaoke_engine.start_session(
            profile_id=profile_id,
            song_id=song_id,
            mode="flow_and_translate" if mode == "flow_and_translate" else "stop_and_fill",
            can_listen=can_listen,
            can_speak=can_speak,
        )

    def submit_karaoke_answer(
        self,
        profile_id: str,
        song_id: str,
        line_index: int,
        user_answer: str,
        mode: str = "stop_and_fill",
    ) -> dict[str, Any]:
        """Track 5: Scores a learner's answer in Karaoke B2."""
        assert self.agent.toolset is not None
        return self.agent.toolset.submit_karaoke_answer(
            profile_id=profile_id,
            song_id=song_id,
            line_index=line_index,
            user_answer=user_answer,
            mode=mode,
        )

    def handle_chat(
        self,
        profile_id: str,
        query: str,
        is_session_start: bool = False,
        barge_in: bool = False,
        audio_b64: Optional[str] = None,
        audio_mime: str = "audio/webm",
        client_layout: str = "mobile_portrait",
    ) -> dict[str, Any]:
        """Runs a conversational turn (text or multimodal audio) through the ADK agent + Judge."""
        assert self.agent.toolset is not None
        profile_ctx = self.agent.toolset.get_profile_context(profile_id=profile_id)
        due_before = self.agent.toolset.get_due_words(profile_id=profile_id, limit=3)
        target_lemmata = [w["lemma"] for w in due_before]

        effective_query = query.strip()
        llm_override: Optional[dict[str, Any]] = None
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
                traj.annotated_response_html = annotate_german_text(traj.final_response)["annotated_html"]

        verdict = self.judge.evaluate_turn(
            traj,
            target_lemmata=target_lemmata,
            audio_gcs_uri=f"gs://hummerli-audio-vault/profiles/{profile_id}/sessions/{date.today().isoformat()}/turn_{len(self.session_verdicts.get(profile_id, [])) + 1:03d}.ogg",
        )
        self.session_verdicts.setdefault(profile_id, []).append(verdict)
        issues = self.bug_router.build_issues_from_verdict(verdict, is_personal_session=True)
        updated_state = self.get_state(profile_id=profile_id, client_layout=client_layout)
        llm_comps = llm_override.get("a2ui_components") if isinstance(llm_override, dict) else None
        a2ui_msgs = build_a2ui_surface_for_turn(
            traj=traj,
            due_words=updated_state["due_words"],
            srs_heatmap=updated_state["profile"]["srs_heatmap"],
            llm_a2ui_components=llm_comps,
        )

        return {
            "trajectory": traj.model_dump(),
            "verdict": verdict.model_dump(),
            "issues": [iss.model_dump() for iss in issues],
            "a2ui_messages": [m.model_dump() for m in a2ui_msgs],
            "state": updated_state,
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
        """Executes all 8 ADK `.test.json` trajectory suites and returns the live scorecard."""
        return run_all_trajectory_evals(trajectories_dir=DEFAULT_TRAJECTORIES_DIR)


PWA_MANIFEST = {
    "name": "Hummerli B1 Voice Tutor & Karaoke B2",
    "short_name": "Hummerli 🐎",
    "description": "Frau Leonie Blücher & Rijckard — German B1 Oral Tutor, Visual Scenes, Gender X-Ray & Karaoke B2",
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
  <title>🐎 Hummerli B1 — Pallino Vocale, Scene FIDE, Gender X-Ray & Karaoke B2</title>
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
      /* Track 4 Canonical Gender Palette: Rosa (die/F), Azzurrino (der/M), Grigio (das/N) */
      --gender-f-rosa: #f472b6;
      --gender-m-azzurrino: #38bdf8;
      --gender-n-grigio: #94a3b8;
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
      padding: 10px 16px;
      background: #070b14;
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
      gap: 8px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      font-size: 1.05rem;
    }
    .badge {
      padding: 3px 9px;
      border-radius: 999px;
      font-size: 0.74rem;
      font-weight: 600;
      background: var(--panel-alt);
      color: var(--accent);
      border: 1px solid var(--border);
    }
    .controls {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }
    select, button, input, textarea {
      background: var(--panel);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 7px 11px;
      border-radius: 8px;
      font-size: 0.84rem;
      cursor: pointer;
      font-family: inherit;
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
    button.pianob-btn.active {
      background: #f59e0b;
      color: #0b1120;
      border-color: #fde047;
      font-weight: 700;
    }

    /* ================= TRACK 4: CROSS-STACK NOUN GENDER X-RAY (ON-DEMAND) ================= */
    .de-noun {
      border-bottom: 1px dotted rgba(148, 163, 184, 0.45);
      cursor: pointer;
      padding: 0 2px;
      border-radius: 4px;
      transition: all 0.18s ease;
    }
    .de-noun.gender-revealed.gender-f,
    body.gender-xray-active .de-noun.gender-f {
      color: var(--gender-f-rosa) !important;
      background: rgba(244, 114, 182, 0.16);
      border-bottom: 2px solid var(--gender-f-rosa);
      font-weight: 700;
    }
    .de-noun.gender-revealed.gender-m,
    body.gender-xray-active .de-noun.gender-m {
      color: var(--gender-m-azzurrino) !important;
      background: rgba(56, 189, 248, 0.16);
      border-bottom: 2px solid var(--gender-m-azzurrino);
      font-weight: 700;
    }
    .de-noun.gender-revealed.gender-n,
    body.gender-xray-active .de-noun.gender-n {
      color: var(--gender-n-grigio) !important;
      background: rgba(148, 163, 184, 0.22);
      border-bottom: 2px solid var(--gender-n-grigio);
      font-weight: 700;
    }
    .de-noun.gender-revealed::before,
    body.gender-xray-active .de-noun::before {
      content: "[" attr(data-article) "] ";
      font-size: 0.72em;
      opacity: 0.9;
      font-weight: 600;
    }

    /* ================= VIEW 1: ORB + VISUAL SCENARIOS (TRACKS 2 & 3) ================= */
    #orbView {
      display: none;
      flex: 1;
      flex-direction: column;
      gap: 14px;
      padding: 14px 16px 28px;
      max-width: 1180px;
      width: 100%;
      margin: 0 auto;
    }
    .orb-responsive-grid {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 16px;
      align-items: start;
    }
    @media (max-width: 860px) {
      .orb-responsive-grid {
        grid-template-columns: 1fr;
      }
    }
    .scene-stage-card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .scene-image-wrapper {
      position: relative;
      width: 100%;
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid var(--border);
      background: #070b14;
    }
    .scene-image-wrapper img {
      width: 100%;
      display: block;
    }
    .scene-svg-overlay {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
    }
    .hotspot-pill {
      position: absolute;
      transform: translate(-50%, -50%);
      background: rgba(15, 23, 42, 0.88);
      color: #f8fafc;
      border: 1.5px solid #64748b;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 0.76rem;
      font-weight: 600;
      cursor: pointer;
      pointer-events: auto;
      white-space: nowrap;
      box-shadow: 0 2px 8px rgba(0,0,0,0.55);
      transition: all 0.2s;
    }
    .hotspot-pill:hover, .hotspot-pill.active {
      transform: translate(-50%, -50%) scale(1.08);
    }
    body.gender-xray-active .hotspot-pill.gender-f,
    .hotspot-pill.gender-revealed.gender-f {
      border-color: var(--gender-f-rosa);
      color: var(--gender-f-rosa);
    }
    body.gender-xray-active .hotspot-pill.gender-m,
    .hotspot-pill.gender-revealed.gender-m {
      border-color: var(--gender-m-azzurrino);
      color: var(--gender-m-azzurrino);
    }
    body.gender-xray-active .hotspot-pill.gender-n,
    .hotspot-pill.gender-revealed.gender-n {
      border-color: var(--gender-n-grigio);
      color: var(--gender-n-grigio);
    }

    /* ================= ORB COLUMN ================= */
    .orb-column {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
    }
    .orb-due-box {
      width: 100%;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 12px;
      text-align: center;
    }
    .mic-orb {
      width: 155px;
      height: 155px;
      border-radius: 50%;
      border: none;
      background: radial-gradient(circle at 35% 30%, #38bdf8, #0284c7 60%, #0369a1 100%);
      box-shadow: 0 0 40px rgba(56, 189, 248, 0.45), inset 0 0 22px rgba(255, 255, 255, 0.25);
      color: white;
      font-size: 3.6rem;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.25s, background 0.25s;
      user-select: none;
    }
    .mic-orb.listening {
      background: radial-gradient(circle at 35% 30%, #f87171, #ef4444 60%, #991b1b 100%);
      animation: pulseOrb 1.2s infinite ease-in-out;
    }
    .mic-orb.speaking {
      background: radial-gradient(circle at 35% 30%, #4ade80, #16a34a 60%, #15803d 100%);
      animation: pulseOrb 1.6s infinite ease-in-out;
    }
    @keyframes pulseOrb {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.08); }
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

    /* ================= VIEW 2: KARAOKE B2 OKTOBERFEST (TRACK 5) ================= */
    #karaokeView {
      display: none;
      flex: 1;
      flex-direction: column;
      gap: 14px;
      padding: 16px;
      max-width: 960px;
      width: 100%;
      margin: 0 auto;
    }
    .karaoke-tok {
      padding: 2px 6px;
      border-radius: 6px;
      font-size: 1.15rem;
      font-weight: 600;
      display: inline-block;
      margin: 2px;
    }
    .karaoke-tok.green_a1_a2 {
      color: #4ade80;
      background: rgba(34, 197, 94, 0.14);
      border-bottom: 2px solid #22c55e;
    }
    .karaoke-tok.blue_b1 {
      color: #60a5fa;
      background: rgba(59, 130, 246, 0.18);
      border-bottom: 2px solid #3b82f6;
    }
    .karaoke-tok.red_b2 {
      color: #f87171;
      background: rgba(239, 68, 68, 0.20);
      border-bottom: 2px solid #ef4444;
    }
    .karaoke-target-gap {
      outline: 2px dashed #fde047;
      padding: 2px 10px;
    }

    /* ================= VIEW 3: STUDIO 3-COLUMN VIEW ================= */
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
    .scenario-bar { display: flex; flex-wrap: wrap; gap: 6px; }
    .scenario-bar button { font-size: 0.76rem; padding: 5px 10px; background: var(--panel-alt); }
    .chat-box {
      height: 360px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 10px;
      background: #070b14;
      border-radius: 8px;
      border: 1px solid var(--border);
    }
    .msg { padding: 10px 13px; border-radius: 10px; max-width: 90%; font-size: 0.92rem; white-space: pre-wrap; }
    .msg.user { align-self: flex-end; background: #0369a1; }
    .msg.tutor { align-self: flex-start; background: var(--panel-alt); border-left: 4px solid var(--accent); }
    .msg.coach { align-self: flex-start; background: #1e3a2f; border-left: 4px solid var(--green); }
    .msg-meta { font-size: 0.72rem; color: var(--muted); margin-bottom: 4px; }
    .chat-input-row { display: flex; gap: 8px; }
    .chat-input-row input { flex: 1; cursor: text; }
    .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
    .stat-pill { background: #070b14; padding: 8px 10px; border-radius: 8px; text-align: center; border: 1px solid var(--border); }
    .stat-pill .num { font-size: 1.2rem; font-weight: 700; }
    .stat-pill .lbl { font-size: 0.72rem; color: var(--muted); }
    .heatmap-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(125px, 1fr));
      gap: 8px;
      max-height: 390px;
      overflow-y: auto;
      padding: 4px;
    }
    .word-tile { padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border); background: #070b14; cursor: pointer; }
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
      max-height: 200px;
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
      <button class="mode-btn active" id="btnModeOrb" onclick="setViewMode('orb')">🎙️ Pallino & Scene FIDE</button>
      <button class="mode-btn" id="btnModeKaraoke" onclick="setViewMode('karaoke')">🍺 Karaoke B2 (Wiesn)</button>
      <button class="mode-btn" id="btnModeStudio" onclick="setViewMode('studio')">🔬 Studio 3-Colonne</button>
      <!-- Track 4: On-Demand Gender X-Ray Toggle (Ctrl+G / Double-Tap / Triple-Tap) -->
      <button id="btnGenderXRay" onclick="toggleGlobalGenderXRay()" title="Scorciatoia Desktop: Ctrl+G | Mobile: Doppio tap su una parola o Triplo tap sulla scheda">
        ⚧️ Genere (Ctrl+G): <span style="color:#f472b6">🌸die</span> · <span style="color:#38bdf8">🩵der</span> · <span style="color:#94a3b8">🩶das</span>
      </button>
      <!-- Track 5: Duolingo-style 'Piano B' Silent / No-Mic Toggles -->
      <button id="btnNoListen" class="pianob-btn" onclick="toggleModality('listen')" title="Piano B Stile Duolingo: Zona silenziosa senza audio">
        🔊 Ascolto ON
      </button>
      <button id="btnNoSpeak" class="pianob-btn" onclick="toggleModality('speak')" title="Piano B Stile Duolingo: Non posso parlare al microfono">
        🎙️ Microfono ON
      </button>
      <select id="profileSelect" onchange="switchProfile()">
        <option value="riccardo">🇨🇭 Riccardo (B1 Zürich)</option>
        <option value="ale">👦 Alessandro (P3)</option>
        <option value="sebi">🧒 Sebastian (P1)</option>
      </select>
    </div>
  </header>

  <div id="modalityBanner" style="background:#0f172a;border-bottom:1px solid var(--border);padding:5px 16px;font-size:0.78rem;color:#cbd5e1;display:flex;justify-content:space-between;align-items:center;">
    <span id="modalityBannerText">🔊🎙️ Audio & Voce attivi · 💡 Suggerimento Genere: premi <strong>Ctrl+G</strong> (o fai <strong>doppio tap</strong> su un nome tedesco) per vedere 🌸 rosa (die), 🩵 azzurrino (der), 🩶 grigio (das)!</span>
    <span id="viewportDetectBadge" class="badge">Layout: Auto</span>
  </div>

  <!-- ==================== VIEW 1: PALLINO + ENTROPIC VISUAL SCENES (TRACKS 2, 3, 4) ==================== -->
  <section id="orbView">
    <div class="orb-responsive-grid">
      <!-- LEFT: VISUAL SITUATION STAGE (TRACK 2 + TRACK 3) -->
      <div class="scene-stage-card">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
          <div>
            <strong id="sceneTitleDe" style="font-size:1rem;">🌳 Zürcher Park am Morgen — Spaziergang mit dem Hund</strong>
            <div id="sceneMoodDe" style="font-size:0.76rem;color:var(--muted);">Herr Meier (Rentner) · herzlich, gesprächig</div>
          </div>
          <div id="scenarioSelectorChips" style="display:flex;gap:5px;flex-wrap:wrap;"></div>
        </div>

        <!-- SCENE ILLUSTRATION + TRACK 3 SVG ARROWS OVERLAY -->
        <div class="scene-image-wrapper" id="sceneImageWrapper">
          <img id="sceneImg" src="" alt="Visual B1 Scenario" />
          <svg class="scene-svg-overlay" id="sceneSvgOverlay" viewBox="0 0 100 100" preserveAspectRatio="none"></svg>
          <div id="sceneHotspotPills"></div>
        </div>

        <!-- TRACK 3: TWO PRIMARY SCENE BUTTONS ('1. Vocabulary' & '2. Sample Conversation') -->
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button class="primary" id="btnSceneVocab" onclick="setSceneTab('vocab')" style="flex:1;">
            🏷️ 1. Vocabulary (Freccine SVG nell'immagine)
          </button>
          <button id="btnSceneConvo" onclick="setSceneTab('convo')" style="flex:1;">
            💬 2. Sample Conversation (Dialogo B1 + Audio)
          </button>
        </div>

        <!-- TAB 1: VOCABULARY CHIPS & SELECTED HOTSPOT DETAIL -->
        <div id="sceneVocabPanel" style="background:#070b14;border:1px solid var(--border);border-radius:10px;padding:10px;">
          <div style="font-size:0.76rem;color:var(--muted);margin-bottom:6px;">
            👆 Clicca una parola per illuminare la freccia nell'immagine e ascoltare la pronuncia (<strong>Ctrl+G</strong> o <strong>doppio tap</strong> per i colori 🌸/🩵/🩶):
          </div>
          <div id="sceneVocabChips" style="display:flex;gap:6px;flex-wrap:wrap;"></div>
          <div id="sceneHotspotDetail" style="margin-top:8px;font-size:0.84rem;color:#e2e8f0;"></div>
        </div>

        <!-- TAB 2: SAMPLE CONVERSATION (TRACK 3) -->
        <div id="sceneConvoPanel" style="display:none;background:#070b14;border:1px solid var(--border);border-radius:10px;padding:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:6px;">
            <strong id="sampleConvoTitle" style="font-size:0.88rem;color:var(--accent);">💬 Sample Conversation B1</strong>
            <div style="display:flex;gap:6px;">
              <button onclick="playSampleConversationTTS()" style="font-size:0.76rem;padding:4px 9px;">🔊 Ascolta Dialogo (2 Voci)</button>
              <button class="primary" onclick="startLiveRoleplayFromSample()" style="font-size:0.76rem;padding:4px 9px;">🎙️ Provaci tu con Frau Blücher!</button>
            </div>
          </div>
          <div id="sampleConvoLines" style="display:flex;flex-direction:column;gap:8px;"></div>
        </div>

        <!-- TRACK 2: ITALIAN DIRECTOR OVERRIDE ('REGIA IN ITALIANO') -->
        <div style="background:#070b14;border:1px solid var(--border);border-radius:10px;padding:10px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-size:0.78rem;font-weight:600;color:#fde047;">🎬 Regia in Italiano (Cambia situazione mantenendo i 3 vocaboli SRS!):</span>
            <button onclick="fillIndianRestaurantPreset()" style="font-size:0.72rem;padding:3px 8px;">🍛 Preset: Ristorante Indiano + Cameriera Maleducata</button>
          </div>
          <div style="display:flex;gap:6px;">
            <textarea id="directorNotesInput" rows="2" style="flex:1;cursor:text;" placeholder="Es: Sì ma voglio ristorante indiano, invece di italiano e la tizia è molto maleducata con me..."></textarea>
            <button class="primary" onclick="submitDirectorNotes()">🎬 Rigenera Scena</button>
          </div>
        </div>
      </div>

      <!-- RIGHT: VOICE ORB + TRANSCRIPT + A2UI v0.9 DYNAMIC SURFACE -->
      <div class="orb-column">
        <div class="orb-due-box">
          <div style="font-size:0.78rem;color:var(--muted);margin-bottom:6px;">🎯 Parole B1 SRS di oggi (sempre preservate nella scena):</div>
          <div class="due-list" id="orbDueWords"></div>
        </div>

        <button class="mic-orb" id="micOrbBtn" aria-label="Parla con Frau Blücher o interrompi (Barge-In)" onclick="toggleOrbTap()">🎙️</button>
        <div class="orb-status" id="orbStatusText" style="font-weight:600;color:var(--accent);">Tocca il Pallino per parlare con Frau Blücher</div>
        <div class="orb-substatus" id="orbSubStatusText" style="font-size:0.8rem;color:var(--muted);text-align:center;">
          Parla in Tedesco B1 o chiedi aiuto in Italiano ("Non ho capito...")
        </div>

        <div class="orb-transcript-card">
          <div>
            <div style="font-size:0.74rem;color:var(--muted);">🗣️ Tu hai detto:</div>
            <div id="orbUserText" style="font-size:0.95rem;font-weight:500;">—</div>
          </div>
          <div style="border-top:1px solid var(--border);padding-top:8px;">
            <div style="font-size:0.74rem;color:var(--accent);" id="orbTutorLabel">🤖 Frau Leonie Blücher 🐎:</div>
            <div id="orbTutorText" style="font-size:0.96rem;">Grüezi Riccardo! Tocca il pallino o esplora la scena qui a fianco.</div>
          </div>
          <div class="chat-input-row" style="margin-top:6px;">
            <input type="text" id="orbTextInput" placeholder="Oppure scrivi/detta qui (Piano B senza microfono)..." onkeydown="if(event.key==='Enter') sendFromOrbInput()" />
            <button class="primary" onclick="sendFromOrbInput()">Invia</button>
          </div>
        </div>

        <!-- A2UI v0.9 GENERATIVE UI DYNAMIC SURFACE -->
        <div id="a2uiOrbSurface" style="width:100%;display:flex;flex-direction:column;gap:10px;text-align:left;"></div>
      </div>
    </div>
  </section>

  <!-- ==================== VIEW 2: KARAOKE B2 OKTOBERFEST (TRACK 5) ==================== -->
  <section id="karaokeView">
    <div class="card">
      <h2>
        <span>🍺 Karaoke B2 — Oktoberfest & Kult Edition (Scientific Goethe CEFR)</span>
        <div style="display:flex;gap:8px;align-items:center;">
          <span class="badge" style="color:#4ade80;border-color:#22c55e;">🟢 Verde = A1/A2</span>
          <span class="badge" style="color:#60a5fa;border-color:#3b82f6;">🔵 Blu = B1</span>
          <span class="badge" style="color:#f87171;border-color:#ef4444;">🔴 Rosso = B2+</span>
        </div>
      </h2>

      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <label style="font-size:0.84rem;">🎵 Scegli Canzone:</label>
        <select id="karaokeSongSelect" onchange="loadKaraokeSession()"></select>
        <label style="font-size:0.84rem;margin-left:8px;">🎮 Modalità:</label>
        <select id="karaokeModeSelect" onchange="loadKaraokeSession()">
          <option value="stop_and_fill">1️⃣ Mode 1: La canzone SI FERMA sulla parola B1/B2 (Pronunciala o Scrivila!)</option>
          <option value="flow_and_translate">2️⃣ Mode 2: La canzone VA e scegli la traduzione tra 5 parole simili!</option>
        </select>
        <button class="primary" onclick="playKaraokeMelodyBeat()">▶️ Avvia Beat / Melodia</button>
      </div>

      <!-- Visual Bouncing-Ball Beat Progress Bar (works in Silent Mode too!) -->
      <div style="background:#070b14;border:1px solid var(--border);border-radius:10px;padding:10px;">
        <div style="display:flex;justify-content:space-between;font-size:0.76rem;color:var(--muted);margin-bottom:4px;">
          <span id="karaokeSongVibe">Inno Oktoberfest</span>
          <span id="karaokeBeatStatus">🟢 Beat Visivo Pronto (Funziona anche in 🔇 Zona Silenziosa!)</span>
        </div>
        <div style="background:#1e293b;height:10px;border-radius:99px;overflow:hidden;">
          <div id="karaokeBeatBar" style="background:linear-gradient(90deg,#22c55e,#3b82f6,#ef4444);width:0%;height:100%;transition:width 0.3s;"></div>
        </div>
      </div>

      <div id="karaokeLinesContainer" style="display:flex;flex-direction:column;gap:12px;"></div>
    </div>
  </section>

  <!-- ==================== VIEW 3: STUDIO 3 COLONNE ==================== -->
  <main class="layout" id="studioView">
    <section class="card">
      <h2>
        <span>🎙️ Conversazione Live (Frau Blücher & Rijckard)</span>
        <span class="badge" id="activeVoiceBadge">de-DE-Neural2-F</span>
      </h2>

      <div style="font-size:0.78rem;color:var(--muted);">Scenari Rapidi (1-Click Trajectory Test Tracks 1–5):</div>
      <div class="scenario-bar">
        <button onclick="sendQuick('Hallo Frau Blücher, starten wir eine neue Übung für heute!', true)">1️⃣ Start B1</button>
        <button onclick="sendQuick('Ich muss heute Nachmittag meine Kinder von der Schule abholen.', false)">2️⃣ Usa 'abholen'</button>
        <button onclick="sendQuick('Si ma voglio ristorante indiano, invece di italiano e la tizia e\\' molto maleducata con me.', false)">3️⃣ Regia: Indiano Maleducata</button>
        <button onclick="sendQuick('Che genere hanno Parkbank, Hund e Geschäft?', false)">4️⃣ Gender X-Ray (🌸🩵🩶)</button>
        <button onclick="sendQuick('Karaoke Wahnsinn ma sono in zona silenziosa: non posso ascoltare e non posso parlare', false)">5️⃣ Karaoke Silent Piano B</button>
        <button onclick="triggerFlawedTurn()" style="border-color:#ef4444;color:#fca5a5;">6️⃣ Simula Bug LLM</button>
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
        <button class="primary" style="padding:4px 10px;font-size:0.76rem;" onclick="runAllEvals()">🧪 Esegui 8 Suite EVAL</button>
      </h2>
      <div><span class="badge" id="verdictBadge">In attesa</span></div>

      <div style="font-size:0.8rem;color:var(--muted);">Ultimo Turno — Tool ADK Chiamati (`TurnTrajectory.tool_calls`):</div>
      <pre class="code-box" id="trajectoryBox">Nessun turno ancora eseguito.</pre>

      <div style="font-size:0.8rem;color:var(--muted);">Level-2 Judge Verdict & Dual-Repo Bug Router (`public` vs `pvt`):</div>
      <pre class="code-box" id="judgeBox"></pre>

      <div style="font-size:0.8rem;color:var(--muted);">📋 Daily Digest Markdown & Risultati 8 Suite EVAL:</div>
      <pre class="code-box" id="digestBox" style="max-height:220px;"></pre>
    </section>
  </main>

  <script>
    let currentProfile = 'riccardo';
    let orbState = 'idle';
    let activeRecognition = null;
    let mediaRecorder = null;
    let audioChunks = [];
    let currentScenarios = [];
    let activeScenario = null;
    let showVocabArrows = true;
    let canListen = true;
    let canSpeak = true;
    let currentKaraokeSession = null;

    function detectClientLayout() {
      const isPortrait = window.innerWidth < window.innerHeight || window.innerWidth < 760;
      const layout = isPortrait ? 'mobile_portrait' : 'desktop_landscape';
      const badge = document.getElementById('viewportDetectBadge');
      if (badge) {
        badge.textContent = isPortrait ? '📱 Mobile 1:1' : '🖥️ Desktop 16:9';
      }
      return layout;
    }

    // ================= TRACK 4: CTRL+G & DOUBLE/TRIPLE-TAP GENDER X-RAY =================
    function toggleGlobalGenderXRay() {
      document.body.classList.toggle('gender-xray-active');
      const isActive = document.body.classList.contains('gender-xray-active');
      const btn = document.getElementById('btnGenderXRay');
      if (btn) {
        btn.style.borderColor = isActive ? '#f472b6' : 'var(--border)';
        btn.style.background = isActive ? 'rgba(244, 114, 182, 0.16)' : 'var(--panel)';
      }
    }

    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'g') {
        e.preventDefault();
        toggleGlobalGenderXRay();
      }
    });

    // Double-click / Double-tap on a single .de-noun or .hotspot-pill reveals its gender; Triple-tap toggles global X-Ray
    let lastTapTime = 0;
    let tapCount = 0;
    document.addEventListener('click', (e) => {
      const nounEl = e.target.closest('.de-noun, .hotspot-pill');
      const now = Date.now();
      if (now - lastTapTime < 360) {
        tapCount += 1;
      } else {
        tapCount = 1;
      }
      lastTapTime = now;

      if (tapCount === 2 && nounEl) {
        nounEl.classList.toggle('gender-revealed');
      } else if (tapCount >= 3) {
        toggleGlobalGenderXRay();
        tapCount = 0;
      }
    });

    // ================= TRACK 5: DUOLINGO-STYLE 'PIANO B' SILENT / NO-MIC MODALITY =================
    async function toggleModality(which) {
      if (which === 'listen') canListen = !canListen;
      if (which === 'speak') canSpeak = !canSpeak;
      if (!canListen && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      const res = await fetch('/api/modality', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id: currentProfile, can_listen: canListen, can_speak: canSpeak })
      });
      const mod = await res.json();
      renderModalityState(mod);
    }

    function renderModalityState(mod) {
      canListen = mod.can_listen;
      canSpeak = mod.can_speak;
      const btnListen = document.getElementById('btnNoListen');
      const btnSpeak = document.getElementById('btnNoSpeak');
      btnListen.textContent = canListen ? '🔊 Ascolto ON' : '🔇 Non posso ascoltare (Piano B)';
      btnListen.classList.toggle('active', !canListen);
      btnSpeak.textContent = canSpeak ? '🎙️ Microfono ON' : '🙊 Non posso parlare (Piano B)';
      btnSpeak.classList.toggle('active', !canSpeak);
      document.getElementById('modalityBannerText').textContent = mod.banner_it + ' · Usa Ctrl+G o doppio tap per i generi 🌸die / 🩵der / 🩶das';

      if (!canSpeak) {
        document.getElementById('orbStatusText').textContent = '🙊 Piano B Senza Microfono attivo: rispondi scrivendo qui sotto!';
      }
    }

    function setViewMode(mode) {
      document.getElementById('orbView').style.display = mode === 'orb' ? 'flex' : 'none';
      document.getElementById('karaokeView').style.display = mode === 'karaoke' ? 'flex' : 'none';
      document.getElementById('studioView').style.display = mode === 'studio' ? 'grid' : 'none';
      document.getElementById('btnModeOrb').classList.toggle('active', mode === 'orb');
      document.getElementById('btnModeKaraoke').classList.toggle('active', mode === 'karaoke');
      document.getElementById('btnModeStudio').classList.toggle('active', mode === 'studio');
      if (mode === 'karaoke' && !currentKaraokeSession) {
        loadKaraokeSession();
      }
    }

    // ================= TRACKS 2 & 3: ENTROPIC SCENES + SVG ARROWS + SAMPLE CONVERSATION =================
    function renderScenariosBar(scenarios) {
      currentScenarios = scenarios || [];
      const bar = document.getElementById('scenarioSelectorChips');
      bar.innerHTML = '';
      currentScenarios.forEach((sc, idx) => {
        const btn = document.createElement('button');
        btn.style.fontSize = '0.75rem';
        btn.style.padding = '4px 9px';
        btn.textContent = `${idx + 1}. ${sc.title_de.split('—')[0].trim()}`;
        btn.onclick = () => selectScenario(sc);
        bar.appendChild(btn);
      });
      if (currentScenarios.length > 0 && !activeScenario) {
        selectScenario(currentScenarios[0]);
      } else if (activeScenario) {
        const updated = currentScenarios.find(s => s.scenario_id === activeScenario.scenario_id);
        if (updated) selectScenario(updated);
      }
    }

    function selectScenario(sc) {
      activeScenario = sc;
      document.getElementById('sceneTitleDe').textContent = sc.title_de;
      document.getElementById('sceneMoodDe').textContent = `${sc.interlocutor_name} · ${sc.interlocutor_mood_de} (${sc.time_and_season_de})`;
      document.getElementById('sceneImg').src = sc.image_data_url;
      renderSceneHotspotsAndArrows(sc, null);
      renderSampleConversation(sc);
    }

    function setSceneTab(tab) {
      showVocabArrows = (tab === 'vocab');
      document.getElementById('sceneVocabPanel').style.display = showVocabArrows ? 'block' : 'none';
      document.getElementById('sceneConvoPanel').style.display = showVocabArrows ? 'none' : 'block';
      document.getElementById('btnSceneVocab').classList.toggle('primary', showVocabArrows);
      document.getElementById('btnSceneConvo').classList.toggle('primary', !showVocabArrows);
      document.getElementById('sceneSvgOverlay').style.display = showVocabArrows ? 'block' : 'none';
      document.getElementById('sceneHotspotPills').style.display = showVocabArrows ? 'block' : 'none';
    }

    function renderSceneHotspotsAndArrows(sc, activeLemma) {
      const svg = document.getElementById('sceneSvgOverlay');
      const pillsBox = document.getElementById('sceneHotspotPills');
      const chipsBox = document.getElementById('sceneVocabChips');
      if (!svg || !pillsBox || !chipsBox) return;

      svg.innerHTML = `
        <defs>
          <marker id="arrow-default" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#f8fafc" />
          </marker>
          <marker id="arrow-F" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#f472b6" />
          </marker>
          <marker id="arrow-M" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#38bdf8" />
          </marker>
          <marker id="arrow-N" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#94a3b8" />
          </marker>
        </defs>
      `;
      pillsBox.innerHTML = '';
      chipsBox.innerHTML = '';

      (sc.hotspots || []).forEach(h => {
        const isSelected = activeLemma === h.lemma;
        const strokeColor = isSelected ? h.color_hex : '#f8fafc';
        const markerId = isSelected && ['F','M','N'].includes(h.gender) ? `arrow-${h.gender}` : 'arrow-default';

        // Draw SVG line with arrowhead from (label_x, label_y) to (target_x, target_y)
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', h.label_x);
        line.setAttribute('y1', h.label_y);
        line.setAttribute('x2', h.target_x);
        line.setAttribute('y2', h.target_y);
        line.setAttribute('stroke', strokeColor);
        line.setAttribute('stroke-width', isSelected ? '1.3' : '0.8');
        line.setAttribute('marker-end', `url(#${markerId})`);
        svg.appendChild(line);

        // Target dot on the object
        const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        dot.setAttribute('cx', h.target_x);
        dot.setAttribute('cy', h.target_y);
        dot.setAttribute('r', isSelected ? '1.8' : '1.2');
        dot.setAttribute('fill', h.color_hex);
        svg.appendChild(dot);

        // Floating pill badge on the image
        const pill = document.createElement('div');
        pill.className = `hotspot-pill ${h.css_class} ${isSelected ? 'active gender-revealed' : ''}`;
        pill.style.left = `${h.label_x}%`;
        pill.style.top = `${h.label_y}%`;
        pill.setAttribute('data-gender', h.gender);
        pill.setAttribute('data-article', h.article);
        pill.textContent = h.lemma;
        pill.onclick = (ev) => {
          ev.stopPropagation();
          inspectHotspot(sc, h);
        };
        pillsBox.appendChild(pill);

        // Chip button below the image
        const chip = document.createElement('button');
        chip.className = `de-noun ${h.css_class} ${isSelected ? 'gender-revealed' : ''}`;
        chip.setAttribute('data-gender', h.gender);
        chip.setAttribute('data-article', h.article);
        chip.style.fontSize = '0.8rem';
        chip.textContent = `${h.lemma} (${h.translation_it})`;
        chip.onclick = () => inspectHotspot(sc, h);
        chipsBox.appendChild(chip);
      });
    }

    function inspectHotspot(sc, h) {
      renderSceneHotspotsAndArrows(sc, h.lemma);
      const box = document.getElementById('sceneHotspotDetail');
      box.innerHTML = `
        <div style="padding:8px;border-left:4px solid ${h.color_hex};background:#0f172a;border-radius:6px;">
          <strong style="color:${h.color_hex};font-size:0.95rem;">${h.display_headword}</strong>
          <span class="badge" style="margin-left:6px;">Genere: ${h.gender} (${h.color_name_it})</span>
          — 🇮🇹 <strong>${h.translation_it}</strong><br/>
          🇩🇪 <em>"${h.example_de}"</em>
        </div>
      `;
      speakText(h.display_headword + '. ' + h.example_de, 'de');
    }

    function renderSampleConversation(sc) {
      const convo = sc.sample_conversation || { title_de: '', lines: [] };
      document.getElementById('sampleConvoTitle').textContent = `💬 ${convo.title_de}`;
      const container = document.getElementById('sampleConvoLines');
      container.innerHTML = '';
      (convo.lines || []).forEach(line => {
        const row = document.createElement('div');
        row.style.cssText = 'padding:8px 10px;border-radius:8px;background:#0f172a;border-left:3px solid ' + (line.role === 'interlocutor' ? '#38bdf8' : '#22c55e');
        row.innerHTML = `
          <div style="font-size:0.74rem;color:var(--muted);display:flex;justify-content:space-between;">
            <span><strong>${line.speaker}</strong></span>
            <button onclick="speakText('${line.text_de.replace(/'/g, "\\'")}', 'de')" style="padding:1px 6px;font-size:0.7rem;">🔊</button>
          </div>
          <div style="font-size:0.92rem;margin-top:2px;">${line.annotated_html || line.text_de}</div>
          <div style="font-size:0.78rem;color:var(--muted);margin-top:2px;">🇮🇹 <em>${line.text_it}</em></div>
        `;
        container.appendChild(row);
      });
    }

    function playSampleConversationTTS() {
      if (!activeScenario || !activeScenario.sample_conversation) return;
      const lines = activeScenario.sample_conversation.lines || [];
      const joined = lines.map(l => l.text_de).join(' ... ');
      speakText(joined, 'de');
    }

    async function startLiveRoleplayFromSample() {
      if (!activeScenario) return;
      const firstLine = activeScenario.sample_conversation.lines[0];
      document.getElementById('orbTutorLabel').textContent = `🤖 ${activeScenario.interlocutor_name} (Roleplay Live):`;
      document.getElementById('orbTutorText').innerHTML = firstLine.annotated_html || firstLine.text_de;
      speakText(firstLine.text_de, 'de');
    }

    function fillIndianRestaurantPreset() {
      document.getElementById('directorNotesInput').value = "Si ma voglio ristorante indiano, invece di italiano e la tizia e' molto maleducata con me.";
    }

    async function submitDirectorNotes() {
      const notes = document.getElementById('directorNotesInput').value.trim();
      if (!notes) return;
      const scId = activeScenario ? activeScenario.scenario_id : 'zuerich_park_hund';
      const res = await fetch('/api/scenarios/mutate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile_id: currentProfile,
          scenario_id: scId,
          director_feedback_it: notes,
          client_layout: detectClientLayout()
        })
      });
      const mutated = await res.json();
      selectScenario(mutated);
    }

    // ================= TRACK 5: KARAOKE B2 OKTOBERFEST STAGE =================
    function populateKaraokeSelector(songs) {
      const sel = document.getElementById('karaokeSongSelect');
      if (!sel || sel.options.length > 0) return;
      (songs || []).forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.song_id;
        opt.textContent = `${s.title} — ${s.artist} (${s.bpm} BPM)`;
        sel.appendChild(opt);
      });
    }

    async function loadKaraokeSession() {
      const songId = document.getElementById('karaokeSongSelect').value || 'fliegerlied';
      const mode = document.getElementById('karaokeModeSelect').value || 'stop_and_fill';
      const res = await fetch('/api/karaoke/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile_id: currentProfile,
          song_id: songId,
          mode: mode,
          can_listen: canListen,
          can_speak: canSpeak
        })
      });
      const session = await res.json();
      currentKaraokeSession = session;
      renderKaraokeSession(session);
    }

    function renderKaraokeSession(session) {
      document.getElementById('karaokeSongVibe').textContent = `🎵 ${session.title} (${session.artist}) — ${session.vibe_it}`;
      const container = document.getElementById('karaokeLinesContainer');
      container.innerHTML = '';

      (session.lines || []).forEach((line, idx) => {
        const card = document.createElement('div');
        card.style.cssText = 'background:#070b14;border:1px solid var(--border);border-radius:10px;padding:12px;';

        let challengeHtml = '';
        if (session.mode === 'stop_and_fill') {
          challengeHtml = `
            <div style="margin-top:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
              <span style="font-size:0.8rem;color:#fde047;">🛑 La canzone si ferma qui! Completa la parola (${line.target_cefr} — "${line.target_translation_it}"):</span>
              <input type="text" id="kAns_${idx}" placeholder="Scrivi o pronuncia la parola tedesca..." style="width:210px;cursor:text;" />
              <button class="primary" onclick="submitKaraokeLine(${idx}, document.getElementById('kAns_${idx}').value)">Verifica</button>
              <button onclick="submitKaraokeLine(${idx}, '${line.target_word}')" style="font-size:0.76rem;">💡 Rivela ('${line.target_word}')</button>
            </div>
          `;
        } else {
          const optsBtns = (line.MultipleChoiceOptions_it || []).map(opt => `
            <button onclick="submitKaraokeLine(${idx}, '${opt.replace(/'/g, "\\'")}')" style="font-size:0.8rem;padding:5px 10px;">
              🇮🇹 ${opt}
            </button>
          `).join('');
          challengeHtml = `
            <div style="margin-top:8px;">
              <div style="font-size:0.8rem;color:#60a5fa;margin-bottom:6px;">
                ⚡ La canzone scorre! Qual è il significato esatto di <strong>"${line.target_word}"</strong> (${line.target_cefr})?
              </div>
              <div style="display:flex;gap:6px;flex-wrap:wrap;">${optsBtns}</div>
            </div>
          `;
        }

        card.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="badge">Verso ${idx + 1} (${line.start_ms / 1000}s – ${line.end_ms / 1000}s)</span>
            <button onclick="speakText('${line.lyrics_de.replace(/'/g, "\\'")}', 'de')" style="font-size:0.75rem;padding:3px 8px;">🔊 Canta Verso</button>
          </div>
          <div style="margin-top:8px;">${line.colored_html}</div>
          <div style="font-size:0.8rem;color:var(--muted);margin-top:4px;">🇮🇹 <em>${line.translation_it}</em></div>
          ${challengeHtml}
          <div id="kFeedback_${idx}" style="margin-top:6px;font-size:0.84rem;font-weight:600;"></div>
        `;
        container.appendChild(card);
      });
    }

    async function submitKaraokeLine(lineIdx, answer) {
      if (!currentKaraokeSession) return;
      const res = await fetch('/api/karaoke/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile_id: currentProfile,
          song_id: currentKaraokeSession.song_id,
          line_index: lineIdx,
          user_answer: answer,
          mode: currentKaraokeSession.mode
        })
      });
      const out = await res.json();
      const fb = document.getElementById(`kFeedback_${lineIdx}`);
      if (fb) {
        fb.style.color = out.correct ? '#4ade80' : '#f87171';
        fb.textContent = out.feedback_it;
      }
    }

    function playKaraokeMelodyBeat() {
      const bar = document.getElementById('karaokeBeatBar');
      const status = document.getElementById('karaokeBeatStatus');
      let pct = 0;
      const timer = setInterval(() => {
        pct += 12.5;
        if (bar) bar.style.width = `${Math.min(100, pct)}%`;
        if (pct >= 100) clearInterval(timer);
      }, 320);

      if (!canListen || !currentKaraokeSession) {
        if (status) status.textContent = '🔇 Beat Visivo Silenzioso in corso (Piano B attivo!)';
        return;
      }
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioCtx();
        const notes = currentKaraokeSession.melody_notes_hz || [261.63, 329.63, 392.00, 523.25];
        notes.forEach((freq, i) => {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = 'triangle';
          osc.frequency.value = freq;
          gain.gain.setValueAtTime(0.12, ctx.currentTime + i * 0.28);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + (i + 1) * 0.27);
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start(ctx.currentTime + i * 0.28);
          osc.stop(ctx.currentTime + (i + 1) * 0.28);
        });
      } catch (e) {}
    }

    // ================= CORE VOICE ORB & STUDIO FUNCTIONS =================
    function setOrbVisualState(state, statusText, subText) {
      orbState = state;
      const orb = document.getElementById('micOrbBtn');
      orb.className = `mic-orb ${state === 'idle' ? '' : state}`;
      if (state === 'idle') {
        orb.textContent = canSpeak ? '🎙️' : '✍️';
        document.getElementById('orbStatusText').textContent = statusText || (canSpeak ? 'Tocca il Pallino per parlare con Frau Blücher' : '🙊 Piano B attivo: rispondi per iscritto qui sotto');
      } else if (state === 'listening') {
        orb.textContent = '⏹️';
        document.getElementById('orbStatusText').textContent = statusText || '🔴 Ti ascolto... (Tocca per inviare)';
      } else if (state === 'thinking') {
        orb.textContent = '⏳';
        document.getElementById('orbStatusText').textContent = statusText || '🧠 Frau Blücher & ADK elaborano...';
      } else if (state === 'speaking') {
        orb.textContent = '🔊';
        document.getElementById('orbStatusText').textContent = statusText || '🗣️ Frau Blücher sta parlando (Tocca per Barge-In!)';
      }
      if (subText) document.getElementById('orbSubStatusText').textContent = subText;
    }

    async function loadState() {
      const layout = detectClientLayout();
      const res = await fetch(`/api/state?profile=${currentProfile}&layout=${layout}`);
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

      if (data.modality) renderModalityState(data.modality);
      if (data.scenarios) renderScenariosBar(data.scenarios);
      if (data.karaoke_songs) populateKaraokeSelector(data.karaoke_songs);

      ['dueWordsBar', 'orbDueWords'].forEach(id => {
        const bar = document.getElementById(id);
        bar.innerHTML = '';
        data.due_words.forEach(w => {
          const chip = document.createElement('span');
          chip.className = `due-chip ${w.gender_code ? 'de-noun gender-' + w.gender_code.toLowerCase() : ''}`;
          if (w.gender_code) {
            chip.setAttribute('data-gender', w.gender_code);
            chip.setAttribute('data-article', w.article || '');
          }
          chip.textContent = `${w.lemma} (${w.translation_it})`;
          bar.appendChild(chip);
        });
      });

      const grid = document.getElementById('heatmapGrid');
      grid.innerHTML = '';
      data.curriculum_grid.forEach(item => {
        const tile = document.createElement('div');
        tile.className = `word-tile ${item.status}`;
        const genderClass = item.gender_code ? `de-noun gender-${item.gender_code.toLowerCase()}` : '';
        tile.innerHTML = `
          <div class="hw ${genderClass}" data-gender="${item.gender_code || ''}" data-article="${item.article || ''}">${item.lemma}</div>
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
        📊 Stato: <strong>${item.status.toUpperCase()}</strong> | Intervallo: <strong>${item.interval_days} giorni</strong><br/>
        <div style="margin-top:6px;color:var(--muted);">${hist}</div>
      `;
    }

    function appendChatMessage(role, persona, htmlOrText) {
      const box = document.getElementById('chatBox');
      const div = document.createElement('div');
      div.className = `msg ${role}`;
      div.innerHTML = `<div class="msg-meta">${persona}</div><div>${htmlOrText}</div>`;
      box.appendChild(div);
      box.scrollTop = box.scrollHeight;
    }

    function speakText(text, lang) {
      if (!canListen || !('speechSynthesis' in window)) {
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

    async function toggleOrbTap() {
      if (!canSpeak) {
        document.getElementById('orbTextInput').focus();
        return;
      }
      if (orbState === 'speaking') {
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();
        setOrbVisualState('idle', '🛑 Barge-In! Frau Blücher fermata.');
        return;
      }
      if (orbState === 'listening') {
        if (activeRecognition) { activeRecognition.stop(); activeRecognition = null; }
        if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
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
            if (e.results[i].isFinal) finalTranscript += e.results[i][0].transcript;
            else interim += e.results[i][0].transcript;
          }
          document.getElementById('orbUserText').textContent = finalTranscript || interim || '...';
        };
        rec.onerror = () => { activeRecognition = null; setOrbVisualState('idle'); };
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
      document.getElementById('orbTextInput').focus();
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
        body: JSON.stringify({
          profile_id: currentProfile,
          query,
          is_session_start: isStart,
          client_layout: detectClientLayout()
        })
      });
      const data = await res.json();
      handleTurnResponse(data);
    }

    function handleTurnResponse(data) {
      const traj = data.trajectory;
      document.getElementById('orbUserText').textContent = traj.user_input;
      document.getElementById('orbTutorLabel').textContent = `🤖 ${traj.active_persona} (${traj.voice}):`;
      document.getElementById('orbTutorText').innerHTML = traj.annotated_response_html || traj.final_response;

      const roleClass = traj.language.includes('it') ? 'coach' : 'tutor';
      appendChatMessage(roleClass, `🤖 ${traj.active_persona} (${traj.voice})`, traj.annotated_response_html || traj.final_response);
      document.getElementById('activeVoiceBadge').textContent = traj.voice;

      speakText(traj.final_response, traj.language);
      updateInspector(data);
      renderState(data.state);
      if (data.a2ui_messages) {
        renderA2UISurface(data.a2ui_messages);
      }
    }

    function renderA2UISurface(messages) {
      const container = document.getElementById('a2uiOrbSurface');
      if (!container) return;
      const updateMsg = messages.find(m => m.action === 'updateComponents');
      if (!updateMsg || !updateMsg.components) return;
      container.innerHTML = `<div style="font-size:0.74rem;color:var(--accent);font-weight:600;">✨ Google A2UI v0.9 Generative UI Surface (Catalog: ${updateMsg.catalogId})</div>`;

      updateMsg.components.forEach(comp => {
        const p = comp.props || {};
        const card = document.createElement('div');
        card.style.cssText = 'background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:12px;font-size:0.86rem;';

        if (comp.type === 'FideExamOutcomeCard') {
          card.style.borderLeft = '4px solid #38bdf8';
          card.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
              <strong>🏆 FIDE B1 Exam Outcome Rubric (Stile "Finnish It!")</strong>
              <span class="badge">${p.fide_level || 'B1'} (${p.overall_pct || 80}%)</span>
            </div>
            <div style="font-size:0.76rem;color:var(--muted);">
              Aufgabe: ${p.aufgabenerfuellung_pct}% · Flüssigkeit: ${p.fluessigkeit_pct}% · Wortschatz: ${p.wortschatz_pct}% · Grammatik: ${p.strukturen_pct}%
            </div>
            <div style="margin-top:6px;color:#4ade80;">🇩🇪 <strong>Native B1 Rewrite:</strong> "${p.rewrite_annotated_html || p.native_b1_rewrite || ''}"</div>
            <div style="margin-top:4px;font-size:0.78rem;color:#cbd5e1;">💡 🇮🇹 ${p.next_step_advice_it || ''}</div>
          `;
        } else if (comp.type === 'GrammarDiffCard') {
          card.style.borderLeft = '4px solid #22c55e';
          card.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
              <strong>📝 A2UI · GrammarDiffCard & Native Rewrite</strong>
              <span class="badge">${p.cefr_score || 'B1'}</span>
            </div>
            <div style="color:var(--muted);font-size:0.8rem;">🗣️ Tua frase: <em>"${p.user_sentence || ''}"</em></div>
            <div style="color:#4ade80;margin-top:4px;">🇩🇪 <strong>B1 Native:</strong> "${p.native_b1_rewrite || ''}"</div>
            <div style="margin-top:6px;font-size:0.8rem;color:#cbd5e1;">💡 🇮🇹 ${p.grammar_rule_it || ''}</div>
          `;
        } else if (comp.type === 'VocabFlashcard') {
          const col = p.gender_color_hex || '#38bdf8';
          card.style.borderLeft = `4px solid ${col}`;
          card.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <strong style="color:${col};font-size:1rem;">🗂️ ${p.headword || ''}</strong>
              <span class="badge">SRS: ${p.status || 'new'} (${p.interval_days || 0}d)</span>
            </div>
            <div style="margin-top:4px;">🇮🇹 ${p.translation_it || ''}</div>
            <div style="margin-top:4px;color:var(--muted);font-style:italic;">🇩🇪 "${p.example_de || ''}"</div>
          `;
        } else if (comp.type === 'NounGenderXRayCard') {
          card.style.borderLeft = '4px solid #f472b6';
          const nounsList = (p.nouns || []).map(n => `<span style="color:${n.color_hex};font-weight:700;">${n.article} ${n.surface} (${n.color_name_it})</span>`).join(' · ');
          card.innerHTML = `
            <div><strong>⚧️ A2UI · Cross-Stack Noun Gender X-Ray (🌸 die · 🩵 der · 🩶 das)</strong></div>
            <div style="margin-top:6px;">${nounsList}</div>
          `;
        } else if (comp.type === 'VisualScenarioCard') {
          selectScenario(p);
          card.style.borderLeft = '4px solid #fde047';
          card.innerHTML = `<div>🎬 <strong>Scena Aggiornata dalla Regia:</strong> ${p.title_de || ''} (${p.interlocutor_mood_de || ''})</div>`;
        } else if (comp.type === 'FideReadinessGauge') {
          card.style.borderLeft = '4px solid #38bdf8';
          card.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <strong>📊 FIDE Zürich Readiness</strong>
              <span class="badge">${p.estimated_level || 'B1-'}</span>
            </div>
            <div style="margin-top:6px;font-size:0.78rem;">Sprechen B1: <strong>${p.sprechen_pct || 70}%</strong> · Wortschatz Goethe B1: <strong>${p.wortschatz_pct || 50}%</strong></div>
            <div style="margin-top:4px;font-size:0.78rem;color:var(--muted);">${p.next_milestone_it || ''}</div>
          `;
        } else {
          card.innerHTML = `<div><strong>🧩 A2UI · ${comp.type}</strong></div>`;
        }
        container.appendChild(card);
      });
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
      box.textContent = '⏳ Esecuzione delle 8 suite ADK Trajectory Evaluation in corso...';
      const res = await fetch('/api/eval', { method: 'POST' });
      const summary = await res.json();
      box.textContent = JSON.stringify(summary, null, 2);
      const vBadge = document.getElementById('verdictBadge');
      vBadge.textContent = `🧪 EVALS: ${summary.status} (${summary.total_suites} suites · Score ${summary.overall_tool_trajectory_score})`;
      vBadge.style.color = '#38bdf8';
    }

    function switchProfile() {
      currentProfile = document.getElementById('profileSelect').value;
      document.getElementById('chatBox').innerHTML = '';
      activeScenario = null;
      loadState();
    }

    window.addEventListener('DOMContentLoaded', async () => {
      const params = new URLSearchParams(window.location.search);
      const modeParam = params.get('mode');
      const initialMode = modeParam === 'studio' ? 'studio' : (modeParam === 'karaoke' ? 'karaoke' : 'orb');
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
                layout = qs.get("layout", ["mobile_portrait"])[0]
                self._send_json(backend.get_state(profile_id=profile_id, client_layout=layout))
                return
            if parsed.path == "/api/scenarios/detail":
                qs = parse_qs(parsed.query)
                profile_id = qs.get("profile", ["riccardo"])[0]
                scenario_id = qs.get("scenario_id", ["zuerich_park_hund"])[0]
                layout = qs.get("layout", ["mobile_portrait"])[0]
                self._send_json(
                    backend.get_scenario_detail(
                        profile_id=profile_id,
                        scenario_id=scenario_id,
                        client_layout=layout,
                    )
                )
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
                    client_layout=payload.get("client_layout", "mobile_portrait"),
                )
                self._send_json(res)
                return
            if parsed.path == "/api/scenarios/mutate":
                res = backend.mutate_scenario(
                    profile_id=payload.get("profile_id", "riccardo"),
                    scenario_id=payload.get("scenario_id", "zuerich_park_hund"),
                    director_feedback_it=payload.get("director_feedback_it", ""),
                    client_layout=payload.get("client_layout", "mobile_portrait"),
                )
                self._send_json(res)
                return
            if parsed.path == "/api/modality":
                res = backend.set_modality(
                    profile_id=payload.get("profile_id", "riccardo"),
                    can_listen=bool(payload.get("can_listen", True)),
                    can_speak=bool(payload.get("can_speak", True)),
                )
                self._send_json(res)
                return
            if parsed.path == "/api/karaoke/start":
                res = backend.start_karaoke(
                    profile_id=payload.get("profile_id", "riccardo"),
                    song_id=payload.get("song_id", "fliegerlied"),
                    mode=payload.get("mode", "stop_and_fill"),
                    can_listen=payload.get("can_listen"),
                    can_speak=payload.get("can_speak"),
                )
                self._send_json(res)
                return
            if parsed.path == "/api/karaoke/answer":
                res = backend.submit_karaoke_answer(
                    profile_id=payload.get("profile_id", "riccardo"),
                    song_id=payload.get("song_id", "fliegerlied"),
                    line_index=int(payload.get("line_index", 0)),
                    user_answer=payload.get("user_answer", ""),
                    mode=payload.get("mode", "stop_and_fill"),
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
