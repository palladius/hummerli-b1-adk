"""Curriculum loader and query repository for Goethe B1 and family curricula."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


DEFAULT_CURRICULA_DIR = Path(__file__).resolve().parents[2] / "data" / "curricula"


class VocabularyEntry(BaseModel):
    """Represents a single target vocabulary lemma in a curriculum."""

    lemma: str
    pos: str
    article: Optional[str] = None
    plural: Optional[str] = None
    cefr_level: str = "B1"
    topic: str = "General"
    translation_it: str = ""
    example_de: str = ""

    @property
    def display_headword(self) -> str:
        """Returns formatted headword with article if noun."""
        if self.article and not self.lemma.lower().startswith(f"{self.article.lower()} "):
            return f"{self.article} {self.lemma}"
        return self.lemma


class CurriculumRepository:
    """Loads and queries vocabulary curricula from disk."""

    def __init__(self, curricula_dir: Optional[Path] = None) -> None:
        self.curricula_dir = Path(curricula_dir) if curricula_dir else DEFAULT_CURRICULA_DIR
        self._cache: dict[str, list[VocabularyEntry]] = {}

    def load_curriculum(self, curriculum_id: str) -> list[VocabularyEntry]:
        """Loads all entries for a given curriculum ID (e.g. 'goethe_b1')."""
        if curriculum_id in self._cache:
            return self._cache[curriculum_id]

        file_path = self.curricula_dir / f"{curriculum_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Curriculum file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as fp:
            raw_list = json.load(fp)

        entries = [VocabularyEntry(**item) for item in raw_list]
        self._cache[curriculum_id] = entries
        return entries

    def get_by_lemma(self, curriculum_id: str, lemma: str) -> Optional[VocabularyEntry]:
        """Finds a vocabulary entry by case-insensitive lemma match."""
        target = lemma.strip().lower()
        for entry in self.load_curriculum(curriculum_id):
            if entry.lemma.lower() == target or entry.display_headword.lower() == target:
                return entry
        return None

    def filter_entries(
        self,
        curriculum_id: str,
        pos: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> list[VocabularyEntry]:
        """Filters curriculum entries by part-of-speech and/or topic substring."""
        entries = self.load_curriculum(curriculum_id)
        results = []
        for entry in entries:
            if pos and entry.pos.lower() != pos.lower():
                continue
            if topic and topic.lower() not in entry.topic.lower():
                continue
            results.append(entry)
        return results
