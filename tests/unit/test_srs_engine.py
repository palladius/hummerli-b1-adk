"""Unit tests for SuperMemo SM-2 / Leitner Spaced Repetition (SRS) Engine."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from hummerli.srs import SRSEngine, SRSCard


def test_srs_interval_progression_on_success(tmp_path: Path):
    """Mastered words progress through Riccardo's spec intervals: 1 -> 7 -> 15 -> 30 -> 90 days."""
    engine = SRSEngine(data_dir=tmp_path)
    now = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)

    # 1st correct review (q=5) -> 1 day
    card = engine.record_attempt(
        profile_id="riccardo",
        lemma="abholen",
        quality=5,
        user_sentence="Ich hole meine Kinder von der Schule ab.",
        tutor_comment="Perfekt! Trennbares Verb richtig am Satzende benutzt.",
        used_actively=True,
        now=now,
    )
    assert card.repetition_count == 1
    assert card.interval_days == 1
    assert card.status == "learning"

    # 2nd correct review (q=5) -> 7 days ("non lo fai per sette giorni")
    card = engine.record_attempt(
        profile_id="riccardo",
        lemma="abholen",
        quality=5,
        user_sentence="Gestern habe ich meinen Freund vom Bahnhof abgeholt.",
        tutor_comment="Sehr gut im Perfekt verwendet!",
        used_actively=True,
        now=now + timedelta(days=1),
    )
    assert card.repetition_count == 2
    assert card.interval_days == 7

    # 3rd correct review (q=4) -> 15 days
    card = engine.record_attempt(
        profile_id="riccardo",
        lemma="abholen",
        quality=4,
        user_sentence="Kannst du bitte das Paket bei der Post abholen?",
        tutor_comment="Korrekt verwendet.",
        used_actively=True,
        now=now + timedelta(days=8),
    )
    assert card.repetition_count == 3
    assert card.interval_days == 15
    assert card.status == "mastered"

    # 4th correct review (q=5) -> 30 days
    card = engine.record_attempt(
        profile_id="riccardo",
        lemma="abholen",
        quality=5,
        user_sentence="Ich werde meinen neuen Pass beim Passbüro abholen.",
        tutor_comment="Ausgezeichnet!",
        used_actively=True,
        now=now + timedelta(days=23),
    )
    assert card.repetition_count == 4
    assert card.interval_days == 30

    # 5th correct review (q=5) -> 90 days ("ogni tre mesi")
    card = engine.record_attempt(
        profile_id="riccardo",
        lemma="abholen",
        quality=5,
        user_sentence="Wir holen die Gäste am Flughafen Zürich ab.",
        tutor_comment="Meisterhaft!",
        used_actively=True,
        now=now + timedelta(days=53),
    )
    assert card.repetition_count == 5
    assert card.interval_days == 90


def test_srs_failure_resets_and_prioritizes_struggling_words(tmp_path: Path):
    """Failed attempts (q < 3) reset repetitions and put the word at the top of due queue."""
    engine = SRSEngine(data_dir=tmp_path)
    now = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)

    # First pass 'Antrag'
    engine.record_attempt(
        profile_id="riccardo",
        lemma="Antrag",
        quality=5,
        user_sentence="Ich habe den Antrag ausgefüllt.",
        tutor_comment="Gut!",
        now=now,
    )

    # Fail 'Behörde' (q=1)
    failed_card = engine.record_attempt(
        profile_id="riccardo",
        lemma="Behörde",
        quality=1,
        user_sentence="Ich gehe zu die... ähm... non mi ricordo.",
        tutor_comment="Kein Problem! Das Wort ist 'die Behörde'.",
        used_actively=False,
        now=now,
    )
    assert failed_card.repetition_count == 0
    assert failed_card.interval_days == 0
    assert failed_card.status == "struggling"
    assert failed_card.ease_factor < 2.5

    # Due words right now should prioritize struggling 'Behörde' first, and exclude 'Antrag' (due tomorrow)
    due = engine.get_due_words("riccardo", limit=3, now=now)
    assert len(due) == 3
    assert due[0].lemma == "Behörde"
    assert all(d.lemma != "Antrag" for d in due)


def test_srs_persistence_and_heatmap_summary(tmp_path: Path):
    """State persists to JSON and reloads accurately with heatmap counts (green/yellow/red)."""
    engine1 = SRSEngine(data_dir=tmp_path)
    now = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)

    # Make 'abholen' mastered (3 passes)
    for i in range(3):
        engine1.record_attempt("riccardo", "abholen", quality=5, now=now + timedelta(days=i * 10))
    # Make 'Gesuch' learning (1 pass)
    engine1.record_attempt("riccardo", "Gesuch", quality=4, now=now)
    # Make 'Abstimmung' struggling (1 fail)
    engine1.record_attempt("riccardo", "Abstimmung", quality=1, now=now)

    # Reload from disk in a fresh SRSEngine instance
    engine2 = SRSEngine(data_dir=tmp_path)
    summary = engine2.get_heatmap_summary("riccardo")
    assert summary["mastered_green"] == 1
    assert summary["learning_yellow"] == 1
    assert summary["struggling_red"] == 1
    assert summary["unseen"] >= 20

    abholen_card = engine2.get_card("riccardo", "abholen")
    assert isinstance(abholen_card, SRSCard)
    assert len(abholen_card.history) == 3
