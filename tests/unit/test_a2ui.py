"""Unit tests for Google A2UI v0.9 Generative UI protocol & widget composition in Hummerli (Tracks 1–5)."""

from pathlib import Path

from hummerli.a2ui import HUMMERLI_A2UI_CATALOG_SCHEMA, build_a2ui_surface_for_turn
from hummerli.agent import create_hummerli_agent


def test_a2ui_catalog_and_surface_generation(tmp_path: Path):
    """Verifies that Hummerli generates valid A2UI v0.9 createSurface and updateComponents messages across all tracks."""
    assert HUMMERLI_A2UI_CATALOG_SCHEMA["version"] == "0.9"
    for expected_widget in (
        "GrammarDiffCard",
        "VocabFlashcard",
        "MultipleChoiceQuiz",
        "FideReadinessGauge",
        "VisualScenarioCard",
        "FideExamOutcomeCard",
        "InteractiveSceneExplorerCard",
        "NounGenderXRayCard",
        "KaraokeB2StageCard",
    ):
        assert expected_widget in HUMMERLI_A2UI_CATALOG_SCHEMA["widgets"]

    agent = create_hummerli_agent(data_dir=tmp_path)
    assert agent.toolset is not None

    due = agent.toolset.get_due_words("riccardo", limit=3)
    hm = agent.toolset.get_profile_context("riccardo")["srs_heatmap"]

    # 1. Confusion turn ("Non ho capito Antrag") -> VocabFlashcard (with Azzurrino #38bdf8 for der) + MultipleChoiceQuiz
    traj_conf = agent.run_turn(
        user_input="Non ho capito cosa significa Antrag.",
        profile_id="riccardo",
    )
    msgs = build_a2ui_surface_for_turn(traj_conf, due, hm)
    assert len(msgs) == 2
    assert msgs[0].action == "createSurface"
    assert msgs[1].action == "updateComponents"
    widget_types = {c.type for c in msgs[1].components}
    assert {"VocabFlashcard", "MultipleChoiceQuiz", "FideReadinessGauge"}.issubset(widget_types)

    # 2. Active usage turn ("abholen") -> GrammarDiffCard + FideExamOutcomeCard + FideReadinessGauge
    traj_use = agent.run_turn(
        user_input="Ich muss heute Nachmittag meine Kinder von der Schule abholen.",
        profile_id="riccardo",
    )
    msgs_use = build_a2ui_surface_for_turn(traj_use, due, hm)
    widget_types_use = {c.type for c in msgs_use[1].components}
    assert {"GrammarDiffCard", "FideExamOutcomeCard", "FideReadinessGauge"}.issubset(widget_types_use)

    # 3. Track 2 Director Override -> VisualScenarioCard + InteractiveSceneExplorerCard
    traj_dir = agent.run_turn(
        user_input="Si ma voglio ristorante indiano, invece di italiano e la tizia e' molto maleducata con me.",
        profile_id="riccardo",
    )
    msgs_dir = build_a2ui_surface_for_turn(traj_dir, due, hm)
    widget_types_dir = {c.type for c in msgs_dir[1].components}
    assert {"VisualScenarioCard", "InteractiveSceneExplorerCard"}.issubset(widget_types_dir)

    # 4. Track 4 Noun Gender X-Ray -> NounGenderXRayCard
    traj_gen = agent.run_turn(
        user_input="Che genere hanno Parkbank, Hund e Geschäft?",
        profile_id="riccardo",
    )
    msgs_gen = build_a2ui_surface_for_turn(traj_gen, due, hm)
    widget_types_gen = {c.type for c in msgs_gen[1].components}
    assert "NounGenderXRayCard" in widget_types_gen

    # 5. Track 5 Karaoke B2 -> KaraokeB2StageCard
    traj_kar = agent.run_turn(
        user_input="Karaoke Wahnsinn ma sono in zona silenziosa: non posso ascoltare e non posso parlare",
        profile_id="riccardo",
    )
    msgs_kar = build_a2ui_surface_for_turn(traj_kar, due, hm)
    widget_types_kar = {c.type for c in msgs_kar[1].components}
    assert "KaraokeB2StageCard" in widget_types_kar
