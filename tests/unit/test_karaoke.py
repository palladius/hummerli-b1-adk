"""Unit tests for Track 5: Oktoberfest 'Karaoke B2' (Scientific CEFR Pre-Computation)
and Cross-App Duolingo Silent/No-Mic 'Piano B' Modality.
"""

from pathlib import Path

from hummerli.karaoke import (
    CEFR_COLOR_BANDS,
    KaraokeEngine,
    verify_karaoke_cefr_integrity,
)


def test_precomputed_oktoberfest_catalog_and_scientific_goethe_cefr_integrity():
    """Verifies that all 5 Oktoberfest/Kult songs are pre-computed and pass scientific Goethe CEFR integrity."""
    engine = KaraokeEngine()
    songs = engine.list_songs()
    song_ids = {s.song_id for s in songs}
    assert {
        "fliegerlied",
        "joanna",
        "wahnsinn",
        "atemlos",
        "neunundneunzig_luftballons",
    }.issubset(song_ids)

    report = verify_karaoke_cefr_integrity(engine.songs)
    assert report["valid"] is True, f"Integrity errors: {report['errors']}"
    assert report["total_songs"] >= 5
    assert report["total_tokens"] >= 60
    assert CEFR_COLOR_BANDS["green_a1_a2"]["color_hex"] == "#22c55e"
    assert CEFR_COLOR_BANDS["blue_b1"]["color_hex"] == "#3b82f6"
    assert CEFR_COLOR_BANDS["red_b2"]["color_hex"] == "#ef4444"


def test_karaoke_mode1_stop_and_fill_gap(tmp_path: Path):
    """Mode 1 ('stop_and_fill'): blanks out the target B1/B2 word and validates spoken or typed answer."""
    engine = KaraokeEngine(data_dir=tmp_path)
    session = engine.start_session(
        profile_id="riccardo",
        song_id="wahnsinn",
        mode="stop_and_fill",
        can_listen=True,
        can_speak=True,
    )
    assert session["song_id"] == "wahnsinn"
    assert session["mode"] == "stop_and_fill"
    first_line = session["lines"][0]
    assert "[_____]" in first_line["masked_lyrics_de"]
    target_word = first_line["target_word"]

    # Correct answer
    res_ok = engine.submit_answer(
        profile_id="riccardo",
        song_id="wahnsinn",
        line_index=0,
        user_answer=target_word,
        mode="stop_and_fill",
    )
    assert res_ok["correct"] is True
    assert res_ok["score_delta"] > 0

    # Wrong answer
    res_bad = engine.submit_answer(
        profile_id="riccardo",
        song_id="wahnsinn",
        line_index=0,
        user_answer="Kartoffelsalat",
        mode="stop_and_fill",
    )
    assert res_bad["correct"] is False
    assert target_word in res_bad["feedback_it"]


def test_karaoke_mode2_flow_and_translate_five_choices(tmp_path: Path):
    """Mode 2 ('flow_and_translate'): presents 5 close Italian translations while the song flows."""
    engine = KaraokeEngine(data_dir=tmp_path)
    session = engine.start_session(
        profile_id="riccardo",
        song_id="fliegerlied",
        mode="flow_and_translate",
        can_listen=True,
        can_speak=True,
    )
    first_line = session["lines"][0]
    assert len(first_line["MultipleChoiceOptions_it"]) == 5
    correct_it = first_line["target_translation_it"]
    assert correct_it in first_line["MultipleChoiceOptions_it"]

    res_ok = engine.submit_answer(
        profile_id="riccardo",
        song_id="fliegerlied",
        line_index=0,
        user_answer=correct_it,
        mode="flow_and_translate",
    )
    assert res_ok["correct"] is True


def test_duolingo_style_2x2_silent_and_no_mic_piano_b_matrix(tmp_path: Path):
    """Verifies that '🔇 Non posso ascoltare' and '🙊 Non posso parlare' adapt Karaoke & app modality."""
    engine = KaraokeEngine(data_dir=tmp_path)

    # 1. Quiet office / sleeping wife: No Audio + No Mic
    prefs = engine.set_modality_preferences(
        profile_id="riccardo",
        can_listen=False,
        can_speak=False,
    )
    assert prefs.can_listen is False
    assert prefs.can_speak is False
    assert prefs.active_audio_channel == "silent_visual_beat"
    assert prefs.active_input_channel == "text_or_chips_only"
    assert "Piano B" in prefs.banner_it

    session_silent = engine.start_session(
        profile_id="riccardo",
        song_id="joanna",
        mode="stop_and_fill",
        can_listen=prefs.can_listen,
        can_speak=prefs.can_speak,
    )
    assert session_silent["audio_strategy"] == "silent_visual_beat"
    assert session_silent["input_strategy"] == "text_or_chips_only"
