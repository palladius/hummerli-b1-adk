"""Unit tests for Track 2 (Entropic Scenarios, Italian Director Override, FIDE Outcome Rubric)
and Track 3 (Interactive Scene Vocabulary SVG Arrow Hotspots & Sample Conversations).
"""

from pathlib import Path

from hummerli.scenarios import (
    ScenarioEngine,
    evaluate_fide_turn_outcome,
)


def test_generate_three_zero_click_entropic_scenarios_and_aspect_ratios(tmp_path: Path):
    """Verifies zero-click generation of 3 entropic scenarios and client viewport aspect ratio detection."""
    engine = ScenarioEngine(data_dir=tmp_path)

    mobile_scenarios = engine.generate_entropic_scenarios(
        profile_id="riccardo",
        count=3,
        client_layout="mobile_portrait",
    )
    assert len(mobile_scenarios) == 3
    for sc in mobile_scenarios:
        assert sc.aspect_ratio == "1:1"
        assert sc.client_layout == "mobile_portrait"
        assert sc.image_data_url.startswith("data:image/svg+xml;utf8,")
        assert len(sc.target_words) >= 1
        assert len(sc.test_questions_de) >= 2
        assert len(sc.hotspots) >= 5
        assert len(sc.sample_conversation.lines) >= 4

    desktop_scenarios = engine.generate_entropic_scenarios(
        profile_id="riccardo",
        count=3,
        client_layout="desktop_landscape",
    )
    assert desktop_scenarios[0].aspect_ratio == "16:9"
    assert desktop_scenarios[0].client_layout == "desktop_landscape"


def test_zurich_park_scene_hotspots_arrows_and_dog_sample_conversation(tmp_path: Path):
    """Track 3: Verifies the Zürich Park scene hotspots (SVG arrow coordinates + Rosa/Azzurrino/Grigio) and dog-walking dialogue."""
    engine = ScenarioEngine(data_dir=tmp_path)
    park = engine.get_scenario_by_id("zuerich_park_hund", profile_id="riccardo")

    hotspot_by_lemma = {h.lemma: h for h in park.hotspots}
    assert {"Parkbank", "Baum", "Rentner", "Wiese", "Hund", "Geschäft"}.issubset(
        set(hotspot_by_lemma.keys())
    )

    # Check Rosa (die/F), Azzurrino (der/M), Grigio (das/N) and SVG arrow coordinates (0..100)
    assert hotspot_by_lemma["Parkbank"].gender == "F"
    assert hotspot_by_lemma["Parkbank"].article == "die"
    assert hotspot_by_lemma["Parkbank"].color_hex == "#f472b6"
    assert 0 <= hotspot_by_lemma["Parkbank"].label_x <= 100
    assert 0 <= hotspot_by_lemma["Parkbank"].target_x <= 100

    assert hotspot_by_lemma["Hund"].gender == "M"
    assert hotspot_by_lemma["Hund"].article == "der"
    assert hotspot_by_lemma["Hund"].color_hex == "#38bdf8"

    assert hotspot_by_lemma["Geschäft"].gender == "N"
    assert hotspot_by_lemma["Geschäft"].article == "das"
    assert hotspot_by_lemma["Geschäft"].color_hex == "#94a3b8"

    # Check sample conversation lines & bold/annotated nouns
    full_de = " ".join(line.text_de for line in park.sample_conversation.lines)
    assert "Schönes Wetter heute" in full_de
    assert "Kommen Sie oft hierher" in full_de
    assert "Hund" in full_de and "Wiese" in full_de and "Geschäft" in full_de
    assert any("de-noun" in line.annotated_html for line in park.sample_conversation.lines)


def test_italian_director_override_indian_restaurant_rude_waitress(tmp_path: Path):
    """Track 2: Mutating a scenario with Italian director notes changes setting & mood while preserving SRS target words."""
    engine = ScenarioEngine(data_dir=tmp_path)
    initial = engine.generate_entropic_scenarios(profile_id="riccardo", count=1)[0]
    original_srs_words = initial.target_words

    mutated = engine.mutate_scenario_with_director_notes(
        profile_id="riccardo",
        current_scenario_id=initial.scenario_id,
        director_feedback_it="Si ma voglio ristorante indiano, invece di italiano e la tizia e' molto maleducata con me.",
        client_layout="mobile_portrait",
    )

    assert mutated.target_words == original_srs_words
    assert "Indisch" in mutated.title_de or "Indisches Restaurant" in mutated.location_de
    assert "unhöflich" in mutated.interlocutor_mood_de.lower() or "genervt" in mutated.interlocutor_mood_de.lower()
    assert mutated.director_notes_it != ""
    assert len(mutated.hotspots) >= 5
    assert len(mutated.sample_conversation.lines) >= 4


def test_fide_b1_outcome_rubric_and_native_rewrite():
    """Track 2: Evaluates user spoken/written turns on the 4 FIDE B1 dimensions and provides a Native B1 Rewrite."""
    outcome_good = evaluate_fide_turn_outcome(
        user_sentence="Ich möchte heute den Antrag auf Einbürgerung bei der Gemeinde einreichen, weil ich seit zehn Jahren in Zürich wohne.",
        target_words=["Antrag", "Einbürgerung", "Gemeinde"],
    )
    assert outcome_good.fide_level in {"B1 Pass ✅", "B2 🌟"}
    assert outcome_good.overall_pct >= 75
    assert outcome_good.native_b1_rewrite != ""
    assert outcome_good.next_step_advice_it != ""

    outcome_short = evaluate_fide_turn_outcome(
        user_sentence="Ich Antrag heute.",
        target_words=["Antrag"],
    )
    assert outcome_short.fide_level in {"A1", "A2", "A2+"}
    assert "Antrag" in outcome_short.native_b1_rewrite
