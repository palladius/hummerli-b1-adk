"""Google A2UI v0.9 (Agent-to-UI) Protocol & Pedagogical Widget Catalog for Hummerli B1."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from hummerli.agent import TurnTrajectory


A2UIActionType = Literal[
    "createSurface",
    "updateComponents",
    "updateDataModel",
    "deleteSurface",
]

WidgetType = Literal[
    "GrammarDiffCard",
    "VocabFlashcard",
    "MultipleChoiceQuiz",
    "FideReadinessGauge",
    "ScenarioRoleplayCard",
]


class A2UIComponent(BaseModel):
    """A single declarative UI component in an A2UI v0.9 surface adjacency list."""

    id: str
    type: WidgetType
    props: dict[str, Any] = Field(default_factory=dict)


class A2UIMessage(BaseModel):
    """An A2UI v0.9 protocol message streamed from the ADK Agent to the Client Renderer."""

    version: str = "0.9"
    action: A2UIActionType
    surfaceId: str = "hummerli_orb_surface"
    catalogId: str = "hummerli.b1.catalog.v1"
    components: list[A2UIComponent] = Field(default_factory=list)
    dataModel: dict[str, Any] = Field(default_factory=dict)


# Official A2UI v0.9 Prompt-First Catalog Schema injected into Gemini's system instruction
HUMMERLI_A2UI_CATALOG_SCHEMA: dict[str, Any] = {
    "catalogId": "hummerli.b1.catalog.v1",
    "version": "0.9",
    "widgets": {
        "GrammarDiffCard": {
            "description": "Renders a side-by-side comparison of what the learner said vs the natural B1 High German rewrite, plus a short Italian grammar tip.",
            "props": {
                "user_sentence": "string",
                "native_b1_rewrite": "string",
                "grammar_rule_it": "string",
                "cefr_score": "string (e.g. 'A2+', 'B1 ✅')",
            },
        },
        "VocabFlashcard": {
            "description": "Renders a color-coded German vocabulary card (🔵 der, 🔴 die, 🟢 das, ⚡ verb) with Italian translation, example sentence, and SM-2 interval.",
            "props": {
                "headword": "string (e.g. 'der Antrag')",
                "gender": "string ('der' | 'die' | 'das' | 'verb')",
                "translation_it": "string",
                "example_de": "string",
                "interval_days": "integer",
                "status": "string ('new' | 'learning' | 'mastered' | 'struggling')",
            },
        },
        "MultipleChoiceQuiz": {
            "description": "Renders an interactive 3-option situational quiz ('Was sagt man auf der Gemeinde?') that the user can tap directly.",
            "props": {
                "question_de": "string",
                "options": "list of 3 strings",
                "correct_index": "integer (0..2)",
                "explanation_it": "string",
            },
        },
        "FideReadinessGauge": {
            "description": "Outcome-based progress card showing estimated FIDE / Goethe B1 readiness across Sprechen, Hören, and Wortschatz.",
            "props": {
                "estimated_level": "string (e.g. 'B1- (78%)')",
                "sprechen_pct": "integer (0..100)",
                "wortschatz_pct": "integer (0..100)",
                "next_milestone_it": "string",
            },
        },
        "ScenarioRoleplayCard": {
            "description": "Sets the Zurich civic/daily-life roleplay scene with goal and target words to use.",
            "props": {
                "title": "string (e.g. '🏛️ Kreisbüro Zürich — Einbürgerung')",
                "situation_de": "string",
                "target_words": "list of strings",
            },
        },
    },
}


def build_a2ui_surface_for_turn(
    traj: TurnTrajectory,
    due_words: list[dict[str, Any]],
    srs_heatmap: dict[str, int],
    llm_a2ui_components: Optional[list[dict[str, Any]]] = None,
) -> list[A2UIMessage]:
    """Composes an A2UI v0.9 message stream (`createSurface` + `updateComponents`) for the current turn.

    Combines any LLM-chosen A2UI widgets with deterministic pedagogical widgets derived from the ADK tool trajectory.
    """
    components: list[A2UIComponent] = []

    # 1. Include valid widgets directly proposed by Gemini via A2UI v0.9 prompt-first JSON
    valid_types = set(HUMMERLI_A2UI_CATALOG_SCHEMA["widgets"].keys())
    if llm_a2ui_components:
        for idx, raw_comp in enumerate(llm_a2ui_components):
            w_type = raw_comp.get("type")
            if w_type in valid_types and isinstance(raw_comp.get("props"), dict):
                components.append(
                    A2UIComponent(
                        id=raw_comp.get("id") or f"llm_w_{idx}",
                        type=w_type,
                        props=raw_comp["props"],
                    )
                )

    called_tools = {tc.tool_name: tc for tc in traj.tool_calls}

    # 2. If session started (`get_due_words` + `get_profile_context`), compose a ScenarioRoleplayCard + FideReadinessGauge
    if "get_profile_context" in called_tools and not any(
        c.type == "ScenarioRoleplayCard" for c in components
    ):
        components.append(
            A2UIComponent(
                id="scene_init",
                type="ScenarioRoleplayCard",
                props={
                    "title": "🏛️ Kreisbüro Zürich — FIDE B1 Sprechen",
                    "situation_de": "Sie sind beim Schalter der Gemeinde Zürich. Bauen Sie die Zielwörter natürlich in das Gespräch mit Frau Blücher ein.",
                    "target_words": [w["display_headword"] for w in due_words],
                },
            )
        )

    # 3. If Rijckard Coach intervened (`explain_in_italian`), compose a VocabFlashcard + MultipleChoiceQuiz
    if "explain_in_italian" in called_tools:
        tc = called_tools["explain_in_italian"]
        concept = tc.tool_args.get("concept_or_phrase", "Antrag")
        out = tc.tool_output or {}
        headword = concept
        gender = "verb"
        for prefix in ("der ", "die ", "das "):
            if str(out.get("explanation_it", "")).lower().find(prefix) != -1:
                gender = prefix.strip()
        if concept and concept[0].isupper() and gender == "verb":
            gender = "die" if concept.endswith("e") or concept.endswith("ung") else "der"

        components.append(
            A2UIComponent(
                id=f"flashcard_{concept.lower()}",
                type="VocabFlashcard",
                props={
                    "headword": f"{gender} {concept}" if gender in {"der", "die", "das"} else concept,
                    "gender": gender,
                    "translation_it": out.get("explanation_it", ""),
                    "example_de": out.get("example_de", f"Können Sie '{concept}' in einem Satz benutzen?"),
                    "interval_days": 0,
                    "status": "struggling" if "record_word_attempt" in called_tools else "learning",
                },
            )
        )
        if not any(c.type == "MultipleChoiceQuiz" for c in components):
            components.append(
                A2UIComponent(
                    id=f"quiz_{concept.lower()}",
                    type="MultipleChoiceQuiz",
                    props={
                        "question_de": f"Welcher Satz mit '{concept}' passt beim Gespräch auf der Gemeinde Zürich?",
                        "options": [
                            f"Ich möchte heute das Formular für '{concept}' einreichen.",
                            f"Ich habe gestern '{concept}' gegessen.",
                            f"'{concept}' fährt um acht Uhr am Bahnhof ab.",
                        ],
                        "correct_index": 0,
                        "explanation_it": f"In ambito comunale a Zurigo si usa '{concept}' per pratiche e documenti ufficiali.",
                    },
                )
            )

    # 4. If `record_word_attempt` was called on a user sentence, compose GrammarDiffCard + VocabFlashcard
    if "record_word_attempt" in called_tools and "explain_in_italian" not in called_tools:
        tc = called_tools["record_word_attempt"]
        args = tc.tool_args
        out = tc.tool_output or {}
        lemma = args.get("lemma", "abholen")
        quality = int(args.get("quality", 5))
        if not any(c.type == "GrammarDiffCard" for c in components):
            components.append(
                A2UIComponent(
                    id=f"diff_{lemma.lower()}",
                    type="GrammarDiffCard",
                    props={
                        "user_sentence": traj.user_input,
                        "native_b1_rewrite": traj.user_input
                        if quality >= 5
                        else f"Ich möchte heute {lemma} auf der Gemeinde erledigen.",
                        "grammar_rule_it": args.get(
                            "tutor_comment",
                            f"Ottimo uso attivo di '{lemma}' in struttura B1!",
                        ),
                        "cefr_score": "B1 ✅ (FIDE Ready)" if quality >= 4 else "A2+ (Rinforzare)",
                    },
                )
            )

    # 5. Always append FideReadinessGauge (Outcome-Based bar like "Finnish It!")
    total = max(1, srs_heatmap.get("total_curriculum", 26))
    practiced = srs_heatmap.get("mastered_green", 0) + srs_heatmap.get("learning_yellow", 0)
    wortschatz_pct = min(100, int(round((practiced / total) * 100)) + 45)
    sprechen_pct = 78 if practiced >= 1 else 68
    if not any(c.type == "FideReadinessGauge" for c in components):
        components.append(
            A2UIComponent(
                id="fide_gauge",
                type="FideReadinessGauge",
                props={
                    "estimated_level": "B1- (Quasi pronto per FIDE!)" if practiced >= 1 else "A2+ → Target B1",
                    "sprechen_pct": sprechen_pct,
                    "wortschatz_pct": wortschatz_pct,
                    "next_milestone_it": (
                        f"Padroneggiate {practiced}/{total} parole chiave Goethe B1. "
                        "Usa le 3 parole di oggi in frasi subordinate (weil/dass) per consolidare il B1!"
                    ),
                },
            )
        )

    return [
        A2UIMessage(
            action="createSurface",
            surfaceId="hummerli_orb_surface",
            catalogId="hummerli.b1.catalog.v1",
        ),
        A2UIMessage(
            action="updateComponents",
            surfaceId="hummerli_orb_surface",
            catalogId="hummerli.b1.catalog.v1",
            components=components,
            dataModel={
                "active_persona": traj.active_persona,
                "language": traj.language,
                "practiced_words": practiced,
                "total_words": total,
            },
        ),
    ]
