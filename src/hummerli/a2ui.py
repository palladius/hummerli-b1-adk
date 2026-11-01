"""Google A2UI v0.9 (Agent-to-UI) Protocol & Pedagogical Widget Catalog for Hummerli B1 (Tracks 1–5)."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from hummerli.agent import TurnTrajectory
from hummerli.gender import GENDER_PALETTE


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
    "VisualScenarioCard",
    "FideExamOutcomeCard",
    "InteractiveSceneExplorerCard",
    "NounGenderXRayCard",
    "KaraokeB2StageCard",
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
            "description": "Renders a German vocabulary card with Cross-Stack Gender X-Ray (🌸 Rosa #f472b6 for die/F, 🩵 Azzurrino #38bdf8 for der/M, 🩶 Grigio #94a3b8 for das/N).",
            "props": {
                "headword": "string (e.g. 'der Antrag')",
                "gender": "string ('der' | 'die' | 'das' | 'verb')",
                "gender_color_hex": "string ('#f472b6' | '#38bdf8' | '#94a3b8' | '#f59e0b')",
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
        "VisualScenarioCard": {
            "description": "Track 2: Renders the Entropic Visual Scenario with 1:1 (mobile) or 16:9 (desktop) illustration, interlocutor mood, test questions, and Italian Director ('Regia in Italiano') override.",
            "props": {
                "scenario_id": "string",
                "title_de": "string",
                "interlocutor_mood_de": "string",
                "aspect_ratio": "string ('1:1' | '16:9')",
                "image_data_url": "string",
                "target_words": "list of strings",
                "test_questions_de": "list of strings",
                "director_notes_it": "string",
            },
        },
        "FideExamOutcomeCard": {
            "description": "Track 2: Outcome-based FIDE B1 oral rubric card showing the 4 FIDE dimensions, level badge ('B1 Pass ✅'), and Native B1 Rewrite.",
            "props": {
                "fide_level": "string",
                "overall_pct": "integer",
                "aufgabenerfuellung_pct": "integer",
                "fluessigkeit_pct": "integer",
                "wortschatz_pct": "integer",
                "strukturen_pct": "integer",
                "native_b1_rewrite": "string",
                "rewrite_annotated_html": "string",
                "next_step_advice_it": "string",
            },
        },
        "InteractiveSceneExplorerCard": {
            "description": "Track 3: Renders a visual situation with 2 interactive buttons: '1. Vocabulary' (SVG arrows pointing to objects on the image) and '2. Sample Conversation' (bold Rosa/Azzurrino/Grigio nouns + TTS + Roleplay).",
            "props": {
                "scenario_id": "string",
                "title_de": "string",
                "image_data_url": "string",
                "hotspots": "list of SceneVocabHotspot objects",
                "sample_conversation": "SampleConversation object",
            },
        },
        "NounGenderXRayCard": {
            "description": "Track 4: Displays resolved German nouns in Rosa (#f472b6 die/F), Azzurrino (#38bdf8 der/M), and Grigio (#94a3b8 das/N) with on-demand Ctrl+G / Double-Tap reveal.",
            "props": {
                "annotated_html": "string",
                "nouns": "list of NounGenderAnnotation objects",
                "palette": "GENDER_PALETTE dict",
            },
        },
        "KaraokeB2StageCard": {
            "description": "Track 5: Oktoberfest Karaoke B2 stage with Green (A1-A2), Blue (B1), Red (B2) lyrics, Mode 1 Cloze Gap, Mode 2 5-Choice Translation, and Duolingo Silent/No-Mic 'Piano B'.",
            "props": {
                "song_id": "string",
                "title": "string",
                "artist": "string",
                "mode": "string ('stop_and_fill' | 'flow_and_translate')",
                "audio_strategy": "string",
                "input_strategy": "string",
                "modality_banner_it": "string",
                "lines": "list of KaraokeLine objects",
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
    """Composes an A2UI v0.9 message stream (`createSurface` + `updateComponents`) for the current turn."""
    components: list[A2UIComponent] = []

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

    # Track 5: Karaoke B2 Stage Card
    if "start_karaoke_session" in called_tools:
        out = called_tools["start_karaoke_session"].tool_output or {}
        components.append(
            A2UIComponent(
                id=f"karaoke_{out.get('song_id', 'fliegerlied')}",
                type="KaraokeB2StageCard",
                props=out,
            )
        )

    # Track 4: Noun Gender X-Ray Card
    if "analyze_german_nouns_gender" in called_tools:
        out = called_tools["analyze_german_nouns_gender"].tool_output or {}
        components.append(
            A2UIComponent(
                id="gender_xray",
                type="NounGenderXRayCard",
                props=out,
            )
        )

    # Track 2: Director Mutated Visual Scenario Card
    if "mutate_scenario_with_director_notes" in called_tools:
        out = called_tools["mutate_scenario_with_director_notes"].tool_output or {}
        components.append(
            A2UIComponent(
                id=f"visual_scene_{out.get('scenario_id', 'custom')}",
                type="VisualScenarioCard",
                props=out,
            )
        )
        components.append(
            A2UIComponent(
                id=f"explorer_{out.get('scenario_id', 'custom')}",
                type="InteractiveSceneExplorerCard",
                props={
                    "scenario_id": out.get("scenario_id", "custom"),
                    "title_de": out.get("title_de", ""),
                    "image_data_url": out.get("image_data_url", ""),
                    "hotspots": out.get("hotspots", []),
                    "sample_conversation": out.get("sample_conversation", {}),
                },
            )
        )

    # Track 3: Interactive Scene Explorer Card (1. Vocabulary SVG Arrows + 2. Sample Conversation)
    if "get_scene_vocabulary_and_dialogue" in called_tools:
        out = called_tools["get_scene_vocabulary_and_dialogue"].tool_output or {}
        components.append(
            A2UIComponent(
                id=f"explorer_{out.get('scenario_id', 'zuerich_park_hund')}",
                type="InteractiveSceneExplorerCard",
                props=out,
            )
        )

    # Session start: ScenarioRoleplayCard
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

    # Rijckard Coach intervention: VocabFlashcard (with Rosa/Azzurrino/Grigio) + MultipleChoiceQuiz
    if "explain_in_italian" in called_tools:
        tc = called_tools["explain_in_italian"]
        concept = tc.tool_args.get("concept_or_phrase", "Antrag")
        out = tc.tool_output or {}
        gender = "verb"
        for prefix in ("der ", "die ", "das "):
            if str(out.get("explanation_it", "")).lower().find(prefix) != -1:
                gender = prefix.strip()
        if concept and concept[0].isupper() and gender == "verb":
            gender = "die" if concept.endswith("e") or concept.endswith("ung") else "der"

        color_map = {
            "die": GENDER_PALETTE["F"]["color_hex"],
            "der": GENDER_PALETTE["M"]["color_hex"],
            "das": GENDER_PALETTE["N"]["color_hex"],
            "verb": "#f59e0b",
        }
        components.append(
            A2UIComponent(
                id=f"flashcard_{concept.lower()}",
                type="VocabFlashcard",
                props={
                    "headword": f"{gender} {concept}" if gender in {"der", "die", "das"} else concept,
                    "gender": gender,
                    "gender_color_hex": color_map.get(gender, "#f59e0b"),
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

    # Active word attempt: GrammarDiffCard + FideExamOutcomeCard (Track 2)
    if "record_word_attempt" in called_tools and "explain_in_italian" not in called_tools:
        tc = called_tools["record_word_attempt"]
        args = tc.tool_args
        out = tc.tool_output or {}
        lemma = args.get("lemma", "abholen")
        quality = int(args.get("quality", 5))
        fide_out = out.get("fide_outcome") or {}
        if not any(c.type == "GrammarDiffCard" for c in components):
            components.append(
                A2UIComponent(
                    id=f"diff_{lemma.lower()}",
                    type="GrammarDiffCard",
                    props={
                        "user_sentence": traj.user_input,
                        "native_b1_rewrite": fide_out.get(
                            "native_b1_rewrite",
                            traj.user_input
                            if quality >= 5
                            else f"Ich möchte heute {lemma} auf der Gemeinde erledigen.",
                        ),
                        "grammar_rule_it": args.get(
                            "tutor_comment",
                            f"Ottimo uso attivo di '{lemma}' in struttura B1!",
                        ),
                        "cefr_score": fide_out.get(
                            "fide_level",
                            "B1 ✅ (FIDE Ready)" if quality >= 4 else "A2+ (Rinforzare)",
                        ),
                    },
                )
            )
        if fide_out and not any(c.type == "FideExamOutcomeCard" for c in components):
            components.append(
                A2UIComponent(
                    id=f"fide_outcome_{lemma.lower()}",
                    type="FideExamOutcomeCard",
                    props=fide_out,
                )
            )

    # Always append FideReadinessGauge
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
