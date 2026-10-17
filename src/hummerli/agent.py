"""Google ADK Dual-Persona Agent Orchestration (Frau Leonie Blücher & Rijckard Coach)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from hummerli.tools import HummerliToolset


FRAU_BLUECHER_INSTRUCTION = """Du bist Frau Leonie Blücher 🐎, eine geduldige, herzliche Deutschlehrerin für das Niveau Goethe-Zertifikat B1 (FIDE-Prüfung zur Einbürgerung im Kanton Zürich).

REGELN FÜR DEINE TRAJEKTORIE UND WERKZEUGE (TOOLS):
1. Beim Start einer Sitzung RUFST DU ZUERST `get_profile_context` und `get_due_words` auf.
2. Du sprichst klares Standard-Hochdeutsch (Niveau B1). NIEMALS Schweizerdeutsch oder Englisch.
3. Baue 1 bis 3 Zielwörter aus `get_due_words` natürlich in ein Gespräch über Zürich, Gemeinde, Einbürgerung oder den Alltag ein.
4. Wenn der Lernende ein Zielwort benutzt oder versucht, RUFST DU SOFORT `record_word_attempt` mit einer fairen SM-2 Bewertung (quality 0..5) auf.
5. Wenn der Lernende Verwirrung signalisiert ("Non ho capito", "Wie bitte?", "Cosa significa?", oder auf Italienisch nach Grammatik fragt), RUFST DU `explain_in_italian` (Rijckard Coach) auf und führst danach das Gespräch auf Deutsch weiter.
"""

RIJCKARD_COACH_INSTRUCTION = """Sei Rijckard, il coach italiano paziente e conciso di Hummerli (voce it-IT-Neural2-C).
Intervieni SOLO quando l'utente non capisce una parola o una regola grammaticale tedesca.
Spiega il concetto in italiano in massimo 2-3 frasi chiare e restituisci subito la parola a Frau Leonie Blücher.
"""


class ToolCallEvent(BaseModel):
    """Recorded tool call in an agent turn trajectory."""

    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    tool_output: Any = None


class TurnTrajectory(BaseModel):
    """Complete record of an agent turn, including all tool calls and persona metadata."""

    user_input: str
    profile_id: str = "riccardo"
    active_persona: str = "Frau Leonie Blücher"
    voice: str = "de-DE-Neural2-F"
    language: str = "de"
    tool_calls: list[ToolCallEvent] = Field(default_factory=list)
    final_response: str = ""
    barge_in_triggered: bool = False


class HummerliAgent:
    """ADK-compatible LlmAgent wrapper supporting both deterministic trajectory execution and Google ADK."""

    def __init__(
        self,
        name: str,
        model: str,
        instruction: str,
        tools: Optional[list[Callable[..., Any]]] = None,
        sub_agents: Optional[list[HummerliAgent]] = None,
        toolset: Optional[HummerliToolset] = None,
    ) -> None:
        self.name = name
        self.model = model
        self.instruction = instruction
        self.tools = tools or []
        self.sub_agents = sub_agents or []
        self.toolset = toolset
        self._tool_map: dict[str, Callable[..., Any]] = {fn.__name__: fn for fn in self.tools}

    def call_tool(
        self,
        tool_name: str,
        trajectory: TurnTrajectory,
        **kwargs: Any,
    ) -> Any:
        """Invokes a registered tool and appends a ToolCallEvent to the turn trajectory."""
        if tool_name not in self._tool_map:
            raise ValueError(f"Tool '{tool_name}' is not registered on agent '{self.name}'.")
        output = self._tool_map[tool_name](**kwargs)
        trajectory.tool_calls.append(
            ToolCallEvent(tool_name=tool_name, tool_args=kwargs, tool_output=output)
        )
        return output

    def run_turn(
        self,
        user_input: str,
        profile_id: str = "riccardo",
        is_session_start: bool = False,
        barge_in: bool = False,
    ) -> TurnTrajectory:
        """Executes a conversational turn, invoking the appropriate ADK tools and recording the trajectory."""
        traj = TurnTrajectory(
            user_input=user_input,
            profile_id=profile_id,
            barge_in_triggered=barge_in,
        )
        text_lower = user_input.strip().lower()

        # 1. Session initialization or explicit start trigger
        start_triggers = ("start", "hallo", "guten tag", "iniziamo", "nuova sessione", "übung")
        if is_session_start or any(
            text_lower.startswith(t) for t in start_triggers
        ) and not self._contains_known_lemma(text_lower, profile_id):
            profile_ctx = self.call_tool(
                "get_profile_context", traj, profile_id=profile_id
            )
            due_words = self.call_tool(
                "get_due_words", traj, profile_id=profile_id, limit=3
            )
            traj.voice = profile_ctx.get("tutor_voice", "de-DE-Neural2-F")
            target_headwords = [w["display_headword"] for w in due_words]
            first_word = due_words[0] if due_words else {"display_headword": "abholen", "lemma": "abholen"}
            traj.final_response = (
                f"Grüezi und guten Tag, {profile_ctx['display_name']}! Ich bin Frau Leonie Blücher. "
                f"Heute üben wir für Ihre B1-Prüfung in Zürich mit den Wörtern: {', '.join(target_headwords)}. "
                f"Fangen wir direkt an: Wann müssen Sie heute Ihre Kinder von der Schule {first_word['lemma']}?"
            )
            return traj

        # 2. Check if learner signals confusion ("Non ho capito", "Wie bitte?", "cosa significa", etc.)
        confusion_patterns = (
            "non ho capito",
            "cosa significa",
            "cosa vuol dire",
            "wie bitte",
            "spiegami",
            "non ricordo",
            "in italiano",
        )
        if any(p in text_lower for p in confusion_patterns):
            concept = self._extract_concept_from_confusion(user_input, profile_id)
            coach_res = self.call_tool(
                "explain_in_italian",
                traj,
                concept_or_phrase=concept,
                user_question=user_input,
                profile_id=profile_id,
            )
            # If the user admitted forgetting a word ("non ricordo"), record a low SM-2 score so SRS reinforces it
            if "non ricordo" in text_lower or "dimenticato" in text_lower:
                self.call_tool(
                    "record_word_attempt",
                    traj,
                    profile_id=profile_id,
                    lemma=concept,
                    quality=1,
                    user_sentence=user_input,
                    tutor_comment="Wort nicht gewusst; Rijckard hat es auf Italienisch erklärt.",
                    used_actively=False,
                )
            traj.active_persona = "Rijckard + Frau Leonie Blücher"
            traj.voice = coach_res["voice"]
            traj.language = "it+de"
            traj.final_response = (
                f"[Rijckard 🇮🇹]: {coach_res['explanation_it']}\n"
                f"[Frau Blücher 🐎]: Versuchen wir es gleich noch einmal auf Deutsch! "
                f"Können Sie einen kurzen Satz mit '{concept}' bilden?"
            )
            return traj

        # 3. Check if learner used or attempted any curriculum lemma
        matched_lemma, quality, comment = self._detect_lemma_usage(user_input, profile_id)
        if matched_lemma:
            rec = self.call_tool(
                "record_word_attempt",
                traj,
                profile_id=profile_id,
                lemma=matched_lemma,
                quality=quality,
                user_sentence=user_input,
                tutor_comment=comment,
                used_actively=quality >= 3,
            )
            if quality >= 4:
                traj.final_response = (
                    f"Ausgezeichnet! Sie haben das Wort '{matched_lemma}' ganz natürlich im Satz verwendet "
                    f"(nächste Wiederholung in {rec['interval_days']} Tag(en)). "
                    f"Erzählen Sie mir bitte noch mehr darüber!"
                )
            else:
                traj.final_response = (
                    f"Guter Versuch mit '{matched_lemma}'! {comment} "
                    f"Wir werden dieses Wort bald wieder üben. Wie würden Sie den Satz noch einmal sagen?"
                )
            return traj

        # 4. General B1 German conversational turn: fetch due words to steer conversation back to target vocab
        due_words = self.call_tool("get_due_words", traj, profile_id=profile_id, limit=1)
        target = due_words[0]["display_headword"] if due_words else "der Antrag"
        traj.final_response = (
            f"Das ist sehr interessant! Auf der Gemeinde in Zürich spricht man oft darüber. "
            f"Können Sie mir in Ihrer nächsten Antwort etwas mit dem Wort '{target}' erzählen?"
        )
        return traj

    def _contains_known_lemma(self, text_lower: str, profile_id: str) -> bool:
        if not self.toolset:
            return False
        lemma, _, _ = self._detect_lemma_usage(text_lower, profile_id)
        return lemma is not None

    def _extract_concept_from_confusion(self, user_input: str, profile_id: str) -> str:
        if self.toolset:
            profile = self.toolset.profile_manager.get_profile(profile_id)
            for entry in self.toolset.curriculum_repo.load_curriculum(profile.curriculum):
                if entry.lemma.lower() in user_input.lower():
                    return entry.lemma
        # Fallback: take last word stripped of punctuation
        tokens = re.findall(r"[A-Za-zÄÖÜäöüß]+", user_input)
        return tokens[-1] if tokens else "abholen"

    def _detect_lemma_usage(
        self, user_input: str, profile_id: str
    ) -> tuple[Optional[str], int, str]:
        """Detects whether the user used a curriculum lemma (including separable verb stems/participles)."""
        if not self.toolset:
            return None, 0, ""

        profile = self.toolset.profile_manager.get_profile(profile_id)
        entries = self.toolset.curriculum_repo.load_curriculum(profile.curriculum)
        text_lower = user_input.lower()

        # Inflected / separable stems for common B1 verbs
        inflections: dict[str, list[str]] = {
            "abholen": ["abholen", "abgeholt", "abzuholen", "hole ", "holst ", "holt ", "holen "],
            "beantragen": ["beantragen", "beantragt", "beantrage"],
            "vereinbaren": ["vereinbaren", "vereinbart", "vereinbare"],
            "teilnehmen": ["teilnehmen", "teilgenommen", "nehme ", "nimmt "],
            "zustimmen": ["zustimmen", "zugestimmt", "stimme "],
            "stattfinden": ["stattfinden", "stattgefunden", "findet "],
            "erledigen": ["erledigen", "erledigt", "erledige"],
            "umziehen": ["umziehen", "umgezogen", "ziehe "],
        }

        for entry in entries:
            lemma_low = entry.lemma.lower()
            candidates = inflections.get(lemma_low, [lemma_low])
            matched = False
            for cand in candidates:
                if cand in text_lower:
                    # For separable verbs like 'hole ... ab', check prefix if stem matched
                    if lemma_low == "abholen" and cand.startswith("hol"):
                        if re.search(r"\bab\b", text_lower):
                            matched = True
                            break
                    else:
                        matched = True
                        break

            if matched:
                word_count = len(user_input.split())
                if "..." in user_input or "ähm" in text_lower:
                    return (
                        entry.lemma,
                        2,
                        f"Unsicherheit bei '{entry.display_headword}' erkannt; Satz war unvollständig.",
                    )
                if word_count >= 5:
                    return (
                        entry.lemma,
                        5,
                        f"'{entry.display_headword}' aktiv und grammatikalisch passend im B1-Satz verwendet.",
                    )
                return (
                    entry.lemma,
                    4,
                    f"'{entry.display_headword}' korrekt genannt, ganzer Satz wäre noch besser.",
                )

        return None, 0, ""


def create_hummerli_agent(data_dir: Optional[Path] = None) -> HummerliAgent:
    """Factory creating the dual-persona Hummerli ADK agent hierarchy."""
    toolset = HummerliToolset(data_dir=data_dir)

    def get_profile_context(profile_id: str = "riccardo") -> dict[str, Any]:
        """Loads learner profile metadata and SRS heatmap summary."""
        return toolset.get_profile_context(profile_id=profile_id)

    def get_due_words(profile_id: str = "riccardo", limit: int = 3) -> list[dict[str, Any]]:
        """Selects 1-3 due or struggling B1 vocabulary words for the session."""
        return toolset.get_due_words(profile_id=profile_id, limit=limit)

    def record_word_attempt(
        profile_id: str,
        lemma: str,
        quality: int,
        user_sentence: str = "",
        tutor_comment: str = "",
        used_actively: bool = True,
    ) -> dict[str, Any]:
        """Records the learner's attempt at a target lemma in the SM-2 SRS engine."""
        return toolset.record_word_attempt(
            profile_id=profile_id,
            lemma=lemma,
            quality=quality,
            user_sentence=user_sentence,
            tutor_comment=tutor_comment,
            used_actively=used_actively,
        )

    def explain_in_italian(
        concept_or_phrase: str,
        user_question: str,
        profile_id: str = "riccardo",
    ) -> dict[str, Any]:
        """Invokes Rijckard (Italian Coach) to explain a German concept in Italian."""
        return toolset.explain_in_italian(
            concept_or_phrase=concept_or_phrase,
            user_question=user_question,
            profile_id=profile_id,
        )

    rijckard_coach = HummerliAgent(
        name="rijckard_coach",
        model="gemini-2.5-flash",
        instruction=RIJCKARD_COACH_INSTRUCTION,
        tools=[explain_in_italian],
        toolset=toolset,
    )

    frau_bluecher = HummerliAgent(
        name="frau_bluecher",
        model="gemini-2.5-flash",
        instruction=FRAU_BLUECHER_INSTRUCTION,
        tools=[
            get_profile_context,
            get_due_words,
            record_word_attempt,
            explain_in_italian,
        ],
        sub_agents=[rijckard_coach],
        toolset=toolset,
    )

    return frau_bluecher


# Standard ADK root_agent entrypoint
root_agent = create_hummerli_agent()
