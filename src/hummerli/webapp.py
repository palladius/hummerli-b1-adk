"""Interactive Web Application & Live Trajectory Dashboard for Hummerli (Goethe B1 ADK Tutor)."""

from __future__ import annotations

import json
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


class HummerliWebBackend:
    """Stateful backend powering the Hummerli Web UI, SRS Heatmap, Live Chat, and Eval Dashboard."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = data_dir
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
        }

    def handle_chat(
        self,
        profile_id: str,
        query: str,
        is_session_start: bool = False,
        barge_in: bool = False,
    ) -> dict[str, Any]:
        """Runs a conversational turn through the ADK agent, evaluates with Level-2 Judge, and returns updated state."""
        assert self.agent.toolset is not None
        due_before = self.agent.toolset.get_due_words(profile_id=profile_id, limit=3)
        target_lemmata = [w["lemma"] for w in due_before]

        traj = self.agent.run_turn(
            user_input=query,
            profile_id=profile_id,
            is_session_start=is_session_start,
            barge_in=barge_in,
        )

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
            tool_calls=[],  # Harness bug: forgot record_word_attempt!
            final_response="Great job Riccardo! Bravo!",  # Skill bug: English + vague!
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


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>🐎 Hummerli B1 ADK — Oral Tutor, SRS Heatmap & Trajectory Eval Studio</title>
  <style>
    :root {
      --bg: #0f172a;
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
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 24px;
      background: #0b1120;
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
      gap: 12px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 700;
      font-size: 1.2rem;
    }
    .badge {
      padding: 3px 10px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 600;
      background: var(--panel-alt);
      color: var(--accent);
      border: 1px solid var(--border);
    }
    .controls {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    select, button, input {
      background: var(--panel);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 8px 13px;
      border-radius: 8px;
      font-size: 0.9rem;
      cursor: pointer;
    }
    button:hover { border-color: var(--accent); }
    button.primary {
      background: #0284c7;
      border-color: #38bdf8;
      font-weight: 600;
    }
    button.danger {
      background: #991b1b;
      border-color: #ef4444;
      font-weight: 600;
    }
    .layout {
      display: grid;
      grid-template-columns: 1.15fr 1fr 1.05fr;
      gap: 16px;
      padding: 16px 24px;
      max-width: 1800px;
      margin: 0 auto;
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
      font-size: 1.05rem;
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
      font-size: 0.78rem;
      padding: 5px 10px;
      background: var(--panel-alt);
    }
    .chat-box {
      height: 410px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 10px;
      background: #0b1120;
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
    .msg.user {
      align-self: flex-end;
      background: #0369a1;
    }
    .msg.tutor {
      align-self: flex-start;
      background: var(--panel-alt);
      border-left: 4px solid var(--accent);
    }
    .msg.coach {
      align-self: flex-start;
      background: #1e3a2f;
      border-left: 4px solid var(--green);
    }
    .msg-meta {
      font-size: 0.72rem;
      color: var(--muted);
      margin-bottom: 4px;
    }
    .chat-input-row {
      display: flex;
      gap: 8px;
    }
    .chat-input-row input {
      flex: 1;
      cursor: text;
    }
    .stats-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
    }
    .stat-pill {
      background: #0b1120;
      padding: 8px 10px;
      border-radius: 8px;
      text-align: center;
      border: 1px solid var(--border);
    }
    .stat-pill .num { font-size: 1.25rem; font-weight: 700; }
    .stat-pill .lbl { font-size: 0.72rem; color: var(--muted); }
    .heatmap-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(125px, 1fr));
      gap: 8px;
      max-height: 420px;
      overflow-y: auto;
      padding: 4px;
    }
    .word-tile {
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: #0b1120;
      cursor: pointer;
      transition: transform 0.1s;
    }
    .word-tile:hover { transform: translateY(-2px); border-color: var(--accent); }
    .word-tile.mastered { background: rgba(34, 197, 94, 0.18); border-color: var(--green); }
    .word-tile.learning { background: rgba(234, 179, 8, 0.18); border-color: var(--yellow); }
    .word-tile.struggling { background: rgba(239, 68, 68, 0.24); border-color: var(--swiss-red); }
    .word-tile .hw { font-weight: 600; font-size: 0.88rem; }
    .word-tile .it { font-size: 0.75rem; color: var(--muted); }
    .word-tile .iv { font-size: 0.7rem; margin-top: 4px; color: var(--accent); }
    pre.code-box {
      background: #0b1120;
      padding: 10px;
      border-radius: 8px;
      border: 1px solid var(--border);
      font-size: 0.78rem;
      overflow-x: auto;
      max-height: 220px;
      margin: 0;
      color: #e2e8f0;
    }
    .due-list {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
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
      <span>🐎🇨🇭 Hummerli B1 ADK Studio</span>
      <span class="badge" id="profileBadge">Riccardo · Goethe B1</span>
      <span class="badge">Frau Leonie Blücher + Rijckard Coach</span>
    </div>
    <div class="controls">
      <label for="profileSelect" style="font-size:0.85rem;color:var(--muted);">Profilo Famiglia:</label>
      <select id="profileSelect" onchange="switchProfile()">
        <option value="riccardo">🇨🇭 Riccardo (Goethe B1 / FIDE Zürich)</option>
        <option value="ale">👦 Alessandro (P3 · DE/FR/EN)</option>
        <option value="sebi">🧒 Sebastian (P1 · Early DE/EN)</option>
      </select>
      <label style="font-size:0.82rem;display:flex;align-items:center;gap:5px;">
        <input type="checkbox" id="ttsToggle" checked /> 🔊 Voce TTS
      </label>
      <button class="danger" onclick="bargeIn()">🛑 Barge-In (Zittisci)</button>
      <button class="primary" onclick="runAllEvals()">🧪 Esegui 4 Suite EVAL</button>
    </div>
  </header>

  <main class="layout">
    <!-- COLUMN 1: LIVE CONVERSATION & SCENARIO TRIGGERS -->
    <section class="card">
      <h2>
        <span>🎙️ Conversazione Live (Frau Blücher & Rijckard)</span>
        <span class="badge" id="activeVoiceBadge">de-DE-Neural2-F</span>
      </h2>

      <div style="font-size:0.78rem;color:var(--muted);">Scenari Rapidi (1-Click Trajectory Test):</div>
      <div class="scenario-bar">
        <button onclick="sendQuick('Hallo Frau Blücher, starten wir eine neue Übung für heute!', true)">1️⃣ Inizia Sessione B1</button>
        <button onclick="sendQuick('Ich muss heute Nachmittag meine Kinder von der Schule abholen.', false)">2️⃣ Usa 'abholen' (Mastery q=5)</button>
        <button onclick="sendQuick('Scusa, non ho capito cosa significa Antrag in questo contesto.', false)">3️⃣ 'Non ho capito Antrag' (Rijckard 🇮🇹)</button>
        <button onclick="sendQuick('Non ricordo cosa vuol dire Behörde, me lo spieghi in italiano?', false)">4️⃣ 'Non ricordo Behörde' (Reset 🔴)</button>
        <button onclick="triggerFlawedTurn()" style="border-color:#ef4444;color:#fca5a5;">5️⃣ Simula Bug LLM (Judge + BugRouter)</button>
      </div>

      <div>
        <span style="font-size:0.78rem;color:var(--muted);">Parole target della sessione (`get_due_words`):</span>
        <div class="due-list" id="dueWordsBar" style="margin-top:4px;"></div>
      </div>

      <div class="chat-box" id="chatBox"></div>

      <div class="chat-input-row">
        <button onclick="startVoiceInput()" id="micBtn" title="Parla al microfono (Hochdeutsch o Italiano)">🎤 Parla</button>
        <input type="text" id="chatInput" placeholder="Scrivi o parla in Tedesco (es. 'Ich muss die Kinder abholen') o Italiano ('Non ho capito...')..." onkeydown="if(event.key==='Enter') sendChat()" />
        <button class="primary" onclick="sendChat()">Invia</button>
      </div>
    </section>

    <!-- COLUMN 2: GOETHE B1 SRS HEATMAP -->
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

      <div id="wordDetailBox" style="font-size:0.82rem;background:#0b1120;padding:10px;border-radius:8px;border:1px solid var(--border);">
        💡 <em>Clicca su qualsiasi tessera del vocabolario per vedere la frase d'esempio B1, l'intervallo SM-2 e lo storico dei tuoi tentativi.</em>
      </div>
    </section>

    <!-- COLUMN 3: ADK TRAJECTORY & LEVEL-2 JUDGE INSPECTOR -->
    <section class="card">
      <h2>
        <span>🔬 ADK Trajectory & Level-2 LLM-as-Judge</span>
        <span class="badge" id="verdictBadge">In attesa</span>
      </h2>

      <div style="font-size:0.8rem;color:var(--muted);">Ultimo Turno — Tool ADK Chiamati (`TurnTrajectory.tool_calls`):</div>
      <pre class="code-box" id="trajectoryBox">Nessun turno ancora eseguito. Clicca su "1️⃣ Inizia Sessione B1" a sinistra!</pre>

      <div style="font-size:0.8rem;color:var(--muted);">Level-2 Judge Verdict & Dual-Repo Bug Router (`public` vs `pvt`):</div>
      <pre class="code-box" id="judgeBox">Il giudice analizza ogni turno separando bug di Harness (tool mancanti) da bug di Modello/Skill (lingua errata, correzioni false).</pre>

      <div style="font-size:0.8rem;color:var(--muted);">📋 Daily Digest Markdown (`hummerli-b1-adk-pvt/digests/`) & Risultati Suite EVAL:</div>
      <pre class="code-box" id="digestBox" style="max-height:240px;"></pre>
    </section>
  </main>

  <script>
    let currentProfile = 'riccardo';

    async function loadState() {
      const res = await fetch(`/api/state?profile=${currentProfile}`);
      const data = await res.json();
      renderState(data);
    }

    function renderState(data) {
      const p = data.profile;
      const hm = p.srs_heatmap;
      document.getElementById('profileBadge').textContent = `${p.display_name} · ${p.target_level}`;
      document.getElementById('curriculumNameBadge').textContent = p.curriculum;
      document.getElementById('cntMastered').textContent = hm.mastered_green;
      document.getElementById('cntLearning').textContent = hm.learning_yellow;
      document.getElementById('cntStruggling').textContent = hm.struggling_red;
      document.getElementById('cntUnseen').textContent = hm.unseen;

      const dueBar = document.getElementById('dueWordsBar');
      dueBar.innerHTML = '';
      data.due_words.forEach(w => {
        const chip = document.createElement('span');
        chip.className = 'due-chip';
        chip.textContent = `${w.display_headword} (${w.translation_it}) [${w.srs_status}]`;
        dueBar.appendChild(chip);
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
      if (!document.getElementById('ttsToggle').checked || !('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text.replace(/\\[.*?\\]:/g, ''));
      u.lang = lang.includes('it') ? 'it-IT' : 'de-DE';
      window.speechSynthesis.speak(u);
    }

    function bargeIn() {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      appendChatMessage('user', '🛑 Barge-In Triggered', '[Interruzione vocale immediata: playback di Frau Blücher fermato]');
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
      appendChatMessage('user', `🗣️ ${currentProfile}`, query);

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id: currentProfile, query, is_session_start: isStart })
      });
      const data = await res.json();
      const traj = data.trajectory;
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

    function startVoiceInput() {
      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRec) {
        alert('Il tuo browser non supporta Web Speech API; usa la barra di testo.');
        return;
      }
      bargeIn();
      const rec = new SpeechRec();
      rec.lang = 'de-DE';
      rec.interimResults = false;
      const btn = document.getElementById('micBtn');
      btn.textContent = '🔴 Ascolto...';
      rec.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        document.getElementById('chatInput').value = transcript;
        btn.textContent = '🎤 Parla';
        sendChat(false);
      };
      rec.onerror = () => { btn.textContent = '🎤 Parla'; };
      rec.onend = () => { btn.textContent = '🎤 Parla'; };
      rec.start();
    }

    window.addEventListener('DOMContentLoaded', async () => {
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
            if parsed.path in {"/", "/index.html"}:
                self._send_html(DASHBOARD_HTML)
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
    host: str = "127.0.0.1",
    port: int = 8788,
    data_dir: Optional[Path] = None,
) -> None:
    """Starts the Hummerli Web Studio HTTP server."""
    backend = HummerliWebBackend(data_dir=data_dir)
    handler_cls = make_handler(backend)
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer((host, port), handler_cls)
    print(f"🐎 Hummerli Web Studio listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
