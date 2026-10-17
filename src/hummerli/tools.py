"""ADK Tools for Hummerli (SRS scheduling, profile lookup, and Rijckard Italian Coach)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from hummerli.curriculum import CurriculumRepository
from hummerli.profiles import ProfileManager
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

    def get_profile_context(self, profile_id: str = "riccardo") -> dict[str, Any]:
        """Loads learner profile metadata and current SRS heatmap summary.

        Args:
            profile_id: Learner profile identifier ('riccardo', 'ale', or 'sebi').
        """
        profile = self.profile_manager.get_profile(profile_id)
        heatmap = self.srs_engine.get_heatmap_summary(profile_id)
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
            result.append(
                {
                    "lemma": entry.lemma,
                    "display_headword": entry.display_headword,
                    "pos": entry.pos,
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
        """Records the learner's attempt at a target lemma and updates SM-2 intervals.

        Args:
            profile_id: Learner profile identifier.
            lemma: Target German word lemma (e.g., 'abholen', 'Antrag').
            quality: SM-2 score from 0 (blackout) to 5 (perfect active usage).
            user_sentence: Transcript of what the user said.
            tutor_comment: Brief pedagogical note on grammar/pronunciation/usage.
            used_actively: True if produced by the user, False if only understood passively.
        """
        card = self.srs_engine.record_attempt(
            profile_id=profile_id,
            lemma=lemma,
            quality=quality,
            user_sentence=user_sentence,
            tutor_comment=tutor_comment,
            used_actively=used_actively,
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
        }

    def explain_in_italian(
        self,
        concept_or_phrase: str,
        user_question: str,
        profile_id: str = "riccardo",
    ) -> dict[str, Any]:
        """Triggers Rijckard (Italian Coach persona) when the learner signals confusion.

        Args:
            concept_or_phrase: The German lemma or grammar rule that caused confusion.
            user_question: What the user asked (e.g., 'Non ho capito cosa significa abholen').
            profile_id: Learner profile identifier.
        """
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
