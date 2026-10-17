"""Multi-profile family configuration manager for Riccardo, Alessandro, and Sebastian."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """Configuration for a learner profile in Hummerli."""

    profile_id: str
    display_name: str
    target_level: str
    curriculum: str
    primary_language: str = "de"
    support_language: str = "it"
    languages: list[str] = Field(default_factory=lambda: ["de", "it"])
    topics: list[str] = Field(default_factory=list)
    strictness: int = 3
    allow_swear_words: bool = False
    speed: str = "1.0x"
    kid_friendly: bool = False
    tutor_voice: str = "de-DE-Neural2-F"
    coach_voice: str = "it-IT-Neural2-C"


DEFAULT_PROFILES: dict[str, UserProfile] = {
    "riccardo": UserProfile(
        profile_id="riccardo",
        display_name="Riccardo",
        target_level="B1",
        curriculum="goethe_b1",
        primary_language="de",
        support_language="it",
        languages=["de", "it", "en"],
        topics=[
            "Zürich Einbürgerung",
            "FIDE Exam (Hören & Sprechen)",
            "Swiss Politics & Abstimmungen",
            "Cantons & Gemeinde",
            "Daily Life & Family",
        ],
        strictness=4,
        allow_swear_words=False,
        speed="1.0x",
        kid_friendly=False,
    ),
    "ale": UserProfile(
        profile_id="ale",
        display_name="Alessandro (P3)",
        target_level="A1-A2",
        curriculum="tandem_p3",
        primary_language="de",
        support_language="it",
        languages=["de", "fr", "en", "it"],
        topics=["Stories", "Nature", "Primary 3 School", "Drama Club", "Chess"],
        strictness=2,
        allow_swear_words=False,
        speed="1.25x",
        kid_friendly=True,
    ),
    "sebi": UserProfile(
        profile_id="sebi",
        display_name="Sebastian (P1)",
        target_level="Early Immersion",
        curriculum="tandem_p1",
        primary_language="de",
        support_language="it",
        languages=["de", "en", "it"],
        topics=["Animals", "Numbers", "Phonics", "Horse Riding"],
        strictness=1,
        allow_swear_words=False,
        speed="1.25x",
        kid_friendly=True,
    ),
}


class ProfileManager:
    """Manages learner profiles and their pedagogical settings."""

    def __init__(self, profiles: Optional[dict[str, UserProfile]] = None) -> None:
        self._profiles: dict[str, UserProfile] = dict(profiles or DEFAULT_PROFILES)

    def list_profiles(self) -> list[str]:
        """Returns list of available profile IDs."""
        return list(self._profiles.keys())

    def get_profile(self, profile_id: str) -> UserProfile:
        """Returns the UserProfile for a given profile_id or raises KeyError."""
        key = profile_id.strip().lower()
        if key not in self._profiles:
            raise KeyError(f"Unknown learner profile: '{profile_id}'. Available: {self.list_profiles()}")
        return self._profiles[key]
