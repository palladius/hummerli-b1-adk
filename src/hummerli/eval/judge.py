"""Level-2 LLM-as-Judge Trajectory & Pedagogical Analyzer and Dual-Repo Bug Router."""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from hummerli.agent import TurnTrajectory


AnomalyCategory = Literal["harness", "skill", "model"]
AnomalySeverity = Literal["high", "medium", "low"]


class EvalAnomaly(BaseModel):
    """Represents a detected flaw in either the agent harness, skill prompt, or model behavior."""

    code: str
    category: AnomalyCategory
    severity: AnomalySeverity = "high"
    message: str
    evidence: str = ""


class TurnVerdict(BaseModel):
    """Judge verdict for a single conversational turn."""

    passed: bool
    score: float
    turn: TurnTrajectory
    anomalies: list[EvalAnomaly] = Field(default_factory=list)
    audio_gcs_uri: Optional[str] = None


class GitHubIssuePayload(BaseModel):
    """Structured GitHub issue payload ready for `gh issue create` on the public or private repo."""

    title: str
    body: str
    labels: list[str]
    target_repo: str
    gh_cli_command: str


class JudgeAnalyzer:
    """Evaluates turn trajectories for both Harness/Tool errors and Pedagogical/Model errors."""

    ENGLISH_LEAK_PATTERNS = (
        r"\bgreat job\b",
        r"\bwell done\b",
        r"\byou used the word\b",
        r"\bgreat!\b",
        r"\bgood job\b",
    )

    FALSE_CORRECTION_PATTERNS = (
        r"['\"]?gefahren['\"]?\s+ist\s+falsch",
        r"['\"]?abgeholt['\"]?\s+ist\s+falsch",
        r"['\"]?eingereicht['\"]?\s+ist\s+falsch",
    )

    def evaluate_turn(
        self,
        turn: TurnTrajectory,
        target_lemmata: Optional[list[str]] = None,
        audio_gcs_uri: Optional[str] = None,
    ) -> TurnVerdict:
        """Evaluates a single TurnTrajectory for harness, skill, and model anomalies."""
        target_lemmata = target_lemmata or []
        anomalies: list[EvalAnomaly] = []

        user_lower = turn.user_input.lower()
        resp_lower = turn.final_response.lower()
        called_tools = {tc.tool_name for tc in turn.tool_calls}

        # 1. Harness Check: Did the learner use a target lemma without `record_word_attempt` being called?
        for lemma in target_lemmata:
            if lemma.lower() in user_lower and "record_word_attempt" not in called_tools:
                anomalies.append(
                    EvalAnomaly(
                        code="MISSING_SRS_RECORD_ON_WORD_USE",
                        category="harness",
                        severity="high",
                        message=(
                            f"Learner used target word '{lemma}' in sentence, but agent failed to invoke "
                            "`record_word_attempt` tool."
                        ),
                        evidence=f"user_input={turn.user_input!r}, tool_calls={list(called_tools)}",
                    )
                )

        # 2. Skill Check: Did Frau Blücher or Rijckard leak English instead of German/Italian?
        for pat in self.ENGLISH_LEAK_PATTERNS:
            if re.search(pat, resp_lower):
                anomalies.append(
                    EvalAnomaly(
                        code="WRONG_TUTOR_LANGUAGE",
                        category="skill",
                        severity="high",
                        message="Tutor responded in English instead of Standard-Hochdeutsch (or Italian via Rijckard).",
                        evidence=turn.final_response,
                    )
                )
                break

        # 3. Model Check: False grammar correction on valid German participles
        for pat in self.FALSE_CORRECTION_PATTERNS:
            if re.search(pat, resp_lower):
                anomalies.append(
                    EvalAnomaly(
                        code="FALSE_GRAMMAR_CORRECTION",
                        category="model",
                        severity="high",
                        message="Tutor hallucinated a grammar error on a grammatically correct German Partizip II.",
                        evidence=turn.final_response,
                    )
                )
                break

        # 4. Skill Check: Overly vague or generic praise ("Bravo!") without constructive B1 context
        if "bravo!" in resp_lower and len(turn.final_response.split()) < 10:
            anomalies.append(
                EvalAnomaly(
                    code="VAGUE_FEEDBACK",
                    category="skill",
                    severity="medium",
                    message="Tutor gave vague feedback ('Bravo!') without B1 sentence reinforcement.",
                    evidence=turn.final_response,
                )
            )

        passed = len(anomalies) == 0
        score = max(0.0, round(1.0 - 0.35 * len(anomalies), 2))
        return TurnVerdict(
            passed=passed,
            score=score,
            turn=turn,
            anomalies=anomalies,
            audio_gcs_uri=audio_gcs_uri,
        )


class BugRouter:
    """Routes detected anomalies to either the public code repo or the private companion vault repo."""

    def __init__(
        self,
        public_repo: str = "palladius/hummerli-b1-adk",
        private_repo: str = "palladius/hummerli-b1-adk-pvt",
    ) -> None:
        self.public_repo = public_repo
        self.private_repo = private_repo

    def select_target_repo(
        self,
        anomaly: EvalAnomaly,
        verdict: TurnVerdict,
        is_personal_session: bool = False,
    ) -> str:
        """Privacy-enforcing routing: personal sessions, audio links, or model/skill transcript bugs -> PRIVATE."""
        if (
            is_personal_session
            or verdict.audio_gcs_uri is not None
            or verdict.turn.profile_id in {"riccardo", "alessandro", "sebastian"}
            or anomaly.category in {"model", "skill"}
        ):
            return self.private_repo
        return self.public_repo

    def build_issues_from_verdict(
        self,
        verdict: TurnVerdict,
        is_personal_session: bool = False,
    ) -> list[GitHubIssuePayload]:
        """Builds actionable GitHub issue payloads for all anomalies in a TurnVerdict."""
        issues: list[GitHubIssuePayload] = []
        for anomaly in verdict.anomalies:
            target_repo = self.select_target_repo(
                anomaly, verdict, is_personal_session=is_personal_session
            )
            labels = [f"bug:{anomaly.category}", f"severity:{anomaly.severity}", "eval-judge"]
            title = f"[{anomaly.category.upper()}][{anomaly.code}] {anomaly.message[:72]}"

            audio_line = (
                f"- **GCS Audio Recording**: `{verdict.audio_gcs_uri}`\n"
                if verdict.audio_gcs_uri
                else ""
            )
            tool_names = [tc.tool_name for tc in verdict.turn.tool_calls]
            body = (
                f"## Hummerli Automated Judge Report (`{anomaly.code}`)\n\n"
                f"- **Category**: `{anomaly.category}`\n"
                f"- **Severity**: `{anomaly.severity}`\n"
                f"- **Profile**: `{verdict.turn.profile_id}`\n"
                f"{audio_line}"
                f"- **Cosa ha detto l'utente**: `{verdict.turn.user_input}`\n"
                f"- **Tool invocati dalla LLM**: `{tool_names}`\n"
                f"- **Risposta della LLM**: `{verdict.turn.final_response}`\n\n"
                f"### Problema Rilevato\n{anomaly.message}\n"
            )
            label_flags = " ".join(f'--label "{lbl}"' for lbl in labels)
            gh_cmd = (
                f'gh issue create --repo "{target_repo}" '
                f'--title "{title}" {label_flags} --body-file -'
            )
            issues.append(
                GitHubIssuePayload(
                    title=title,
                    body=body,
                    labels=labels,
                    target_repo=target_repo,
                    gh_cli_command=gh_cmd,
                )
            )
        return issues


def generate_daily_digest(
    profile_id: str,
    date_str: str,
    verdicts: list[TurnVerdict],
    bug_router: Optional[BugRouter] = None,
) -> str:
    """Generates the Italian/German Markdown Daily Digest for the private repository."""
    router = bug_router or BugRouter()
    total = len(verdicts)
    passed = sum(1 for v in verdicts if v.passed)

    lines = [
        f"# 🐎 Hummerli Daily Judge Digest — `{profile_id}` ({date_str})",
        "",
        f"- **Turni analizzati**: {total}",
        f"- **Turni superati senza anomalie**: {passed}/{total}",
        "",
    ]

    for idx, v in enumerate(verdicts, start=1):
        status_icon = "✅" if v.passed else "❌"
        tool_summary = (
            ", ".join(
                f"`{tc.tool_name}({tc.tool_args})`" for tc in v.turn.tool_calls
            )
            or "_Nessun tool invocato_"
        )
        lines.extend(
            [
                f"## Turno {idx} {status_icon} (Score: {v.score})",
                "",
                "### 🗣️ Cosa ha detto Riccardo",
                f"> {v.turn.user_input}",
                "",
                "### 🤖 Cosa ha fatto la LLM",
                f"- **Persona attiva**: `{v.turn.active_persona}` (`{v.turn.language}`)",
                f"- **Tool ADK chiamati**: {tool_summary}",
                f"- **Risposta**: {v.turn.final_response}",
                "",
            ]
        )
        if v.anomalies:
            lines.append("### 🚨 Cosa ha SBAGLIATO la LLM")
            issues = router.build_issues_from_verdict(v, is_personal_session=True)
            for anomaly, issue in zip(v.anomalies, issues):
                lines.append(
                    f"- **`{anomaly.code}`** (`{anomaly.category}` / `{anomaly.severity}`): "
                    f"{anomaly.message} → Bug destinato a `{issue.target_repo}`"
                )
            lines.append("")
        else:
            lines.extend(
                [
                    "### 🚨 Cosa ha SBAGLIATO la LLM",
                    "- _Nessun errore rilevato: traiettoria ADK e pedagogia B1 corrette._",
                    "",
                ]
            )

    return "\n".join(lines)
