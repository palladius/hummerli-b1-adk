"""ADK Tools for Hummerli (SRS scheduling, profile lookup, Rijckard Coach, Entropic Scenarios,
Interactive Scene Hotspots, Cross-Stack Noun Gender X-Ray, and Oktoberfest Karaoke B2 + Silent Mode).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from hummerli.curriculum import CurriculumRepository
from hummerli.gender import GenderResolver, annotate_german_text
from hummerli.karaoke import KaraokeEngine
from hummerli.profiles import ProfileManager
from hummerli.scenarios import ScenarioEngine, evaluate_fide_turn_outcome
from hummerli.srs import SRSEngine


class HummerliToolset:
    """Stateful toolset bound to a data directory and curriculum repository."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        curriculum_repo: Optional[CurriculumRepository] = None,
        profile_manager: Optional[ProfileManager] = None,
    ) -> None:
        self.curriculum_repo = curriculum_repo or CurriculumRepository()
        self.profile_manager = profile_manager or ProfileManager()
        self.srs_engine = SRSEngine(
            data_dir=data_dir,
            curriculum_repo=self.curriculum_repo,
            profile_manager=self.profile_manager,
        )
        self.gender_resolver = GenderResolver(curriculum_repo=self.curriculum_repo)
        self.scenario_engine = ScenarioEngine(
            data_dir=data_dir,
            curriculum_repo=self.curriculum_repo,
            profile_manager=self.profile_manager,
        )
        self.karaoke_engine = KaraokeEngine(data_dir=data_dir)

    def get_profile_context(self, profile_id: str = "riccardo") -> dict[str, Any]:
        """Loads learner profile metadata and current SRS heatmap summary.

        Args:
            profile_id: Learner profile identifier ('riccardo', 'ale', or 'sebi').
        """
        profile = self.profile_manager.get_profile(profile_id)
        heatmap = self.srs_engine.get_heatmap_summary(profile_id)
        modality = self.karaoke_engine.get_modality_preferences(profile_id)
        return {
            "profile_id": profile.profile_id,
            "display_name": profile.display_name,
            "target_level": profile.target_level,
            "curriculum": profile.curriculum,
            "primary_language": profile.primary_language,
            "support_language": profile.support_language,
            "topics": profile.topics,
            "strictness": profile.strictness,
            "kid_friendly": profile.kid_friendly,
            "tutor_voice": profile.tutor_voice,
            "coach_voice": profile.coach_voice,
            "srs_heatmap": heatmap,
            "modality": modality.model_dump(),
        }

    def get_due_words(self, profile_id: str = "riccardo", limit: int = 3) -> list[dict[str, Any]]:
        """Selects 1-3 due or struggling vocabulary lemmata for the current session.

        Args:
            profile_id: Learner profile identifier.
            limit: Maximum number of target words to return (default 3).
        """
        entries = self.srs_engine.get_due_words(profile_id=profile_id, limit=limit)
        result = []
        for entry in entries:
            card = self.srs_engine.get_card(profile_id, entry.lemma)
            gender_ann = self.gender_resolver.resolve_word(entry.lemma, entry.article)
            result.append(
                {
                    "lemma": entry.lemma,
                    "display_headword": entry.display_headword,
                    "pos": entry.pos,
                    "article": entry.article,
                    "gender_code": gender_ann.gender if gender_ann else None,
                    "gender_color_hex": gender_ann.color_hex if gender_ann else None,
                    "cefr_level": entry.cefr_level,
                    "topic": entry.topic,
                    "translation_it": entry.translation_it,
                    "example_de": entry.example_de,
                    "srs_status": card.status,
                    "repetition_count": card.repetition_count,
                    "interval_days": card.interval_days,
                }
            )
        return result

    def record_word_attempt(
        self,
        profile_id: str,
        lemma: str,
        quality: int,
        user_sentence: str = "",
        tutor_comment: str = "",
        used_actively: bool = True,
    ) -> dict[str, Any]:
        """Records the learner's attempt at a target lemma and updates SM-2 intervals."""
        card = self.srs_engine.record_attempt(
            profile_id=profile_id,
            lemma=lemma,
            quality=quality,
            user_sentence=user_sentence,
            tutor_comment=tutor_comment,
            used_actively=used_actively,
        )
        fide_outcome = evaluate_fide_turn_outcome(
            user_sentence=user_sentence or lemma,
            target_words=[lemma],
        )
        return {
            "profile_id": profile_id,
            "lemma": card.lemma,
            "quality": card.last_score,
            "status": card.status,
            "repetition_count": card.repetition_count,
            "ease_factor": card.ease_factor,
            "interval_days": card.interval_days,
            "next_review_due": card.next_review_due,
            "fide_outcome": fide_outcome.model_dump(),
        }

    def explain_in_italian(
        self,
        concept_or_phrase: str,
        user_question: str,
        profile_id: str = "riccardo",
    ) -> dict[str, Any]:
        """Triggers Rijckard (Italian Coach persona) when the learner signals confusion."""
        profile = self.profile_manager.get_profile(profile_id)
        entry = self.curriculum_repo.get_by_lemma(profile.curriculum, concept_or_phrase)

        if entry:
            explanation = (
                f"Ciao {profile.display_name}! Te lo spiego subito in italiano: "
                f"'{entry.display_headword}' ({entry.pos}, livello {entry.cefr_level}) significa "
                f"'{entry.translation_it}'. Esempio pratico: \"{entry.example_de}\". "
                f"Ora ripasso subito la parola a Frau Blücher così lo provi in una frase!"
            )
        else:
            explanation = (
                f"Ciao {profile.display_name}! Ecco una spiegazione rapida su '{concept_or_phrase}': "
                f"in tedesco B1 attenzione alla posizione del verbo (secondo posto nella frase principale, "
                f"in fondo nelle subordinate o coi verbi separabili). Ripasso la linea a Frau Blücher!"
            )

        return {
            "persona": "Rijckard",
            "voice": profile.coach_voice,
            "language": "it",
            "concept": concept_or_phrase,
            "user_question": user_question,
            "explanation_it": explanation,
            "handoff_back_to": "Frau Leonie Blücher",
        }

    # --- Track 2: Entropic Scenarios, Italian Director Override & FIDE Outcome ---
    def generate_entropic_scenarios(
        self,
        profile_id: str = "riccardo",
        count: int = 3,
        client_layout: str = "mobile_portrait",
    ) -> list[dict[str, Any]]:
        """Generates 3 ready-to-play Entropic Visual Scenarios anchored to the learner's due SRS words."""
        layout = "desktop_landscape" if client_layout == "desktop_landscape" else "mobile_portrait"
        scenarios = self.scenario_engine.generate_entropic_scenarios(
            profile_id=profile_id,
            count=count,
            client_layout=layout,  # type: ignore[arg-type]
        )
        return [s.model_dump() for s in scenarios]

    def mutate_scenario_with_director_notes(
        self,
        profile_id: str,
        current_scenario_id: str,
        director_feedback_it: str,
        client_layout: str = "mobile_portrait",
    ) -> dict[str, Any]:
        """Mutates the active visual scenario using Italian Director Notes while preserving SRS target words."""
        layout = "desktop_landscape" if client_layout == "desktop_landscape" else "mobile_portrait"
        mutated = self.scenario_engine.mutate_scenario_with_director_notes(
            profile_id=profile_id,
            current_scenario_id=current_scenario_id,
            director_feedback_it=director_feedback_it,
            client_layout=layout,  # type: ignore[arg-type]
        )
        return mutated.model_dump()

    def evaluate_fide_turn(
        self,
        user_sentence: str,
        target_words: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Evaluates a user sentence on the 4 FIDE B1 oral rubric dimensions and returns a Native B1 Rewrite."""
        return evaluate_fide_turn_outcome(
            user_sentence=user_sentence,
            target_words=target_words,
        ).model_dump()

    # --- Track 3: Interactive Scene Vocabulary Hotspots (SVG Arrows) & Sample Conversations ---
    def get_scene_vocabulary_and_dialogue(
        self,
        profile_id: str = "riccardo",
        scenario_id: str = "zuerich_park_hund",
    ) -> dict[str, Any]:
        """Returns the interactive SVG arrow hotspots ('1. Vocabulary') and dialogue ('2. Sample Conversation') for a scene."""
        return self.scenario_engine.get_scene_vocabulary_and_dialogue(
            profile_id=profile_id,
            scenario_id=scenario_id,
        )

    # --- Track 4: Cross-Stack German Noun Gender X-Ray (Rosa/Azzurrino/Grigio) ---
    def analyze_german_nouns_gender(self, text_de: str) -> dict[str, Any]:
        """Resolves German nouns in text_de to Feminine (Rosa #f472b6), Masculine (Azzurrino #38bdf8), or Neuter (Grigio #94a3b8)."""
        return annotate_german_text(text_de=text_de, resolver=self.gender_resolver)

    # --- Track 5: Oktoberfest Karaoke B2 & Cross-App Silent/No-Mic 'Piano B' ---
    def set_modality_preferences(
        self,
        profile_id: str = "riccardo",
        can_listen: bool = True,
        can_speak: bool = True,
    ) -> dict[str, Any]:
        """Updates Duolingo-style 'Piano B' modality preferences ('🔇 Non posso ascoltare' / '🙊 Non posso parlare')."""
        return self.karaoke_engine.set_modality_preferences(
            profile_id=profile_id,
            can_listen=can_listen,
            can_speak=can_speak,
        ).model_dump()

    def start_karaoke_session(
        self,
        profile_id: str = "riccardo",
        song_id: str = "fliegerlied",
        mode: str = "stop_and_fill",
        can_listen: bool = True,
        can_speak: bool = True,
    ) -> dict[str, Any]:
        """Starts an Oktoberfest Karaoke B2 session with pre-computed CEFR colors and Mode 1/2 challenges."""
        k_mode = "flow_and_translate" if mode == "flow_and_translate" else "stop_and_fill"
        return self.karaoke_engine.start_session(
            profile_id=profile_id,
            song_id=song_id,
            mode=k_mode,  # type: ignore[arg-type]
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
        """Submits and scores a learner's answer in Karaoke B2 Mode 1 (gap fill) or Mode 2 (5-option translation)."""
        k_mode = "flow_and_translate" if mode == "flow_and_translate" else "stop_and_fill"
        return self.karaoke_engine.submit_answer(
            profile_id=profile_id,
            song_id=song_id,
            line_index=line_index,
            user_answer=user_answer,
            mode=k_mode,  # type: ignore[arg-type]
        )
