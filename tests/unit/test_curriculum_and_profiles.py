"""Unit tests for Goethe B1 Wortliste curriculum and Multi-Profile loader."""

import pytest
from hummerli.curriculum import CurriculumRepository, VocabularyEntry
from hummerli.profiles import ProfileManager, UserProfile


def test_load_goethe_b1_curriculum():
    repo = CurriculumRepository()
    entries = repo.load_curriculum("goethe_b1")
    assert len(entries) >= 25
    assert all(isinstance(e, VocabularyEntry) for e in entries)

    # Must include Riccardo's iconic examples from spec ('abholen', 'Antrag')
    abholen = repo.get_by_lemma("goethe_b1", "abholen")
    assert abholen is not None
    assert abholen.pos == "verb"
    assert abholen.cefr_level == "B1"
    assert "abholen" in abholen.example_de.lower() or "abgeholt" in abholen.example_de.lower()
    assert abholen.translation_it != ""

    antrag = repo.get_by_lemma("goethe_b1", "Antrag")
    assert antrag is not None
    assert antrag.article == "der"


def test_filter_curriculum_by_pos_and_topic():
    repo = CurriculumRepository()
    verbs = repo.filter_entries("goethe_b1", pos="verb")
    nouns = repo.filter_entries("goethe_b1", pos="noun")
    assert len(verbs) >= 8
    assert len(nouns) >= 8

    civic = repo.filter_entries("goethe_b1", topic="Zürich & Einbürgerung")
    assert len(civic) >= 5


def test_load_family_profiles():
    pm = ProfileManager()
    profiles = pm.list_profiles()
    assert {"riccardo", "ale", "sebi"}.issubset(set(profiles))

    ricc = pm.get_profile("riccardo")
    assert isinstance(ricc, UserProfile)
    assert ricc.target_level == "B1"
    assert ricc.curriculum == "goethe_b1"
    assert ricc.primary_language == "de"
    assert ricc.support_language == "it"
    assert ricc.kid_friendly is False

    ale = pm.get_profile("ale")
    assert ale.curriculum == "tandem_p3"
    assert ale.kid_friendly is True
    assert ale.allow_swear_words is False
    assert "fr" in ale.languages

    sebi = pm.get_profile("sebi")
    assert sebi.curriculum == "tandem_p1"
    assert sebi.kid_friendly is True
    assert sebi.strictness == 1


def test_unknown_profile_raises():
    pm = ProfileManager()
    with pytest.raises(KeyError):
        pm.get_profile("non_existent_user")
