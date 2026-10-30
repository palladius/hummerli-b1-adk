"""Unit tests for Google A2UI v0.9 Generative UI protocol & widget composition in Hummerli."""

from pathlib import Path

from hummerli.a2ui import HUMMERLI_A2UI_CATALOG_SCHEMA, build_a2ui_surface_for_turn
from hummerli.agent import create_hummerli_agent


def test_a2ui_catalog_and_surface_generation(tmp_path: Path):
    """Verifies that Hummerli generates valid A2UI v0.9 createSurface and updateComponents messages."""
    assert HUMMERLI_A2UI_CATALOG_SCHEMA["version"] == "0.9"
    assert "GrammarDiffCard" in HUMMERLI_A2UI_CATALOG_SCHEMA["widgets"]
    assert "VocabFlashcard" in HUMMERLI_A2UI_CATALOG_SCHEMA["widgets"]
    assert "MultipleChoiceQuiz" in HUMMERLI_A2UI_CATALOG_SCHEMA["widgets"]
    assert "FideReadinessGauge" in HUMMERLI_A2UI_CATALOG_SCHEMA["widgets"]

    agent = create_hummerli_agent(data_dir=tmp_path)
    assert agent.toolset is not None

    # 1. Confusion turn ("Non ho capito Antrag") -> generates VocabFlashcard + MultipleChoiceQuiz + FideReadinessGauge
    traj_conf = agent.run_turn(
        user_input="Non ho capito cosa significa Antrag.",
        profile_id="riccardo",
    )
    due = agent.toolset.get_due_words("riccardo", limit=3)
    hm = agent.toolset.get_profile_context("riccardo")["srs_heatmap"]
    msgs = build_a2ui_surface_for_turn(traj_conf, due, hm)

    assert len(msgs) == 2
    assert msgs[0].action == "createSurface"
    assert msgs[1].action == "updateComponents"
    widget_types = {c.type for c in msgs[1].components}
    assert "VocabFlashcard" in widget_types
    assert "MultipleChoiceQuiz" in widget_types
    assert "FideReadinessGauge" in widget_types

    # 2. Active usage turn ("abholen") -> generates GrammarDiffCard + FideReadinessGauge
    traj_use = agent.run_turn(
        user_input="Ich muss heute Nachmittag meine Kinder von der Schule abholen.",
        profile_id="riccardo",
    )
    msgs_use = build_a2ui_surface_for_turn(traj_use, due, hm)
    widget_types_use = {c.type for c in msgs_use[1].components}
    assert "GrammarDiffCard" in widget_types_use
    assert "FideReadinessGauge" in widget_types_use
