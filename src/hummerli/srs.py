"""SuperMemo SM-2 / Leitner Spaced Repetition (SRS) Engine for Hummerli."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from hummerli.curriculum import CurriculumRepository, VocabularyEntry
from hummerli.profiles import ProfileManager


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Riccardo's spec interval progression for mastered cards (in days):
# 1st pass -> 1d, 2nd pass -> 7d, 3rd pass -> 15d, 4th pass -> 30d, 5th+ pass -> 90d
MILESTONE_INTERVALS_DAYS = [1, 7, 15, 30, 90]


class AttemptRecord(BaseModel):
    """Single historical attempt on a vocabulary lemma."""

    timestamp: str
    quality: int  # 0..5 SM-2 score
    user_sentence: str = ""
    tutor_comment: str = ""
    used_actively: bool = True


class SRSCard(BaseModel):
    """Spaced repetition state for a single lemma and learner profile."""

    lemma: str
    repetition_count: int = 0
    ease_factor: float = 2.5
    interval_days: int = 0
    next_review_due: Optional[str] = None
    last_score: Optional[int] = None
    status: Literal["new", "learning", "mastered", "struggling"] = "new"
    history: list[AttemptRecord] = Field(default_factory=list)


class SRSEngine:
    """Manages SM-2 / Leitner scheduling, struggling-word prioritization, and JSON persistence."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        curriculum_repo: Optional[CurriculumRepository] = None,
        profile_manager: Optional[ProfileManager] = None,
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.curriculum_repo = curriculum_repo or CurriculumRepository()
        self.profile_manager = profile_manager or ProfileManager()

    def _state_file(self, profile_id: str) -> Path:
        user_dir = self.data_dir / "users" / profile_id.strip().lower()
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "srs_state.json"

    def load_state(self, profile_id: str) -> dict[str, SRSCard]:
        """Loads persisted SRS cards for a learner profile."""
        path = self._state_file(profile_id)
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as fp:
            raw = json.load(fp)
        return {k: SRSCard(**v) for k, v in raw.items()}

    def save_state(self, profile_id: str, cards: dict[str, SRSCard]) -> None:
        """Persists SRS cards for a learner profile to JSON."""
        path = self._state_file(profile_id)
        serializable = {k: v.model_dump() for k, v in cards.items()}
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(serializable, fp, indent=2, ensure_ascii=False)

    def get_card(self, profile_id: str, lemma: str) -> SRSCard:
        """Returns the current SRSCard for a lemma (or a fresh card if unseen)."""
        cards = self.load_state(profile_id)
        for key, card in cards.items():
            if key.lower() == lemma.strip().lower():
                return card
        return SRSCard(lemma=lemma.strip())

    def record_attempt(
        self,
        profile_id: str,
        lemma: str,
        quality: int,
        user_sentence: str = "",
        tutor_comment: str = "",
        used_actively: bool = True,
        now: Optional[datetime] = None,
    ) -> SRSCard:
        """Updates SM-2 parameters for a lemma after a conversational turn."""
        q = max(0, min(5, int(quality)))
        current_time = now or datetime.now(timezone.utc)

        cards = self.load_state(profile_id)
        # Match canonical lemma from curriculum if available
        profile = self.profile_manager.get_profile(profile_id)
        vocab_entry = self.curriculum_repo.get_by_lemma(profile.curriculum, lemma)
        canonical_lemma = vocab_entry.lemma if vocab_entry else lemma.strip()

        card = cards.get(canonical_lemma, SRSCard(lemma=canonical_lemma))

        # Standard SM-2 ease factor update
        ef_delta = 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
        card.ease_factor = round(max(1.3, card.ease_factor + ef_delta), 3)
        card.last_score = q

        if q >= 3:
            card.repetition_count += 1
            idx = min(card.repetition_count - 1, len(MILESTONE_INTERVALS_DAYS) - 1)
            card.interval_days = MILESTONE_INTERVALS_DAYS[idx]
            card.status = "mastered" if card.repetition_count >= 3 else "learning"
        else:
            # "La lingua batte dove il dente duole": reset interval for immediate reinforcement
            card.repetition_count = 0
            card.interval_days = 0
            card.status = "struggling"

        due_dt = current_time + timedelta(days=card.interval_days)
        card.next_review_due = due_dt.isoformat()
        card.history.append(
            AttemptRecord(
                timestamp=current_time.isoformat(),
                quality=q,
                user_sentence=user_sentence,
                tutor_comment=tutor_comment,
                used_actively=used_actively,
            )
        )

        cards[canonical_lemma] = card
        self.save_state(profile_id, cards)
        return card

    def get_due_words(
        self,
        profile_id: str,
        limit: int = 3,
        now: Optional[datetime] = None,
    ) -> list[VocabularyEntry]:
        """Selects up to `limit` target words for the session.

        Priority order:
        1. Struggling words (🔴 status == 'struggling' and due <= now)
        2. Due review words (🟡/🟢 next_review_due <= now)
        3. New unseen words from the profile's curriculum
        """
        current_time = now or datetime.now(timezone.utc)
        profile = self.profile_manager.get_profile(profile_id)
        entries = self.curriculum_repo.load_curriculum(profile.curriculum)
        cards = self.load_state(profile_id)

        struggling: list[VocabularyEntry] = []
        due_reviews: list[VocabularyEntry] = []
        unseen: list[VocabularyEntry] = []

        for entry in entries:
            card = cards.get(entry.lemma)
            if card is None:
                unseen.append(entry)
                continue

            is_due = True
            if card.next_review_due:
                due_dt = datetime.fromisoformat(card.next_review_due)
                if due_dt.tzinfo is None:
                    due_dt = due_dt.replace(tzinfo=timezone.utc)
                is_due = due_dt <= current_time

            if is_due:
                if card.status == "struggling":
                    struggling.append(entry)
                else:
                    due_reviews.append(entry)

        selected = (struggling + due_reviews + unseen)[: max(1, limit)]
        return selected

    def get_heatmap_summary(self, profile_id: str) -> dict[str, int]:
        """Returns 🟢 Mastered, 🟡 Learning, 🔴 Struggling, and Unseen counts for the Astro dashboard."""
        profile = self.profile_manager.get_profile(profile_id)
        entries = self.curriculum_repo.load_curriculum(profile.curriculum)
        cards = self.load_state(profile_id)

        mastered = sum(1 for c in cards.values() if c.status == "mastered")
        learning = sum(1 for c in cards.values() if c.status == "learning")
        struggling = sum(1 for c in cards.values() if c.status == "struggling")
        unseen = max(0, len(entries) - (mastered + learning + struggling))

        return {
            "total_curriculum": len(entries),
            "mastered_green": mastered,
            "learning_yellow": learning,
            "struggling_red": struggling,
            "unseen": unseen,
        }
