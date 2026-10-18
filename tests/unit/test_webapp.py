"""Unit tests for the Hummerli Interactive Web Application & REST API."""

import json
from pathlib import Path

from hummerli.webapp import HummerliWebBackend


def test_webapp_backend_state_and_chat(tmp_path: Path):
    """Verifies that the web backend returns profile state, heatmap, and processes chat turns with Judge verdicts."""
    backend = HummerliWebBackend(data_dir=tmp_path)

    state = backend.get_state(profile_id="riccardo")
    assert state["profile"]["profile_id"] == "riccardo"
    assert state["profile"]["srs_heatmap"]["total_curriculum"] >= 25
    assert len(state["curriculum_grid"]) >= 25
    assert len(state["due_words"]) == 3

    # 1. Start session turn
    turn_start = backend.handle_chat(
        profile_id="riccardo",
        query="Hallo Frau Blücher, starten wir eine neue Übung!",
        is_session_start=True,
    )
    assert turn_start["trajectory"]["active_persona"] == "Frau Leonie Blücher"
    tool_names = [tc["tool_name"] for tc in turn_start["trajectory"]["tool_calls"]]
    assert "get_profile_context" in tool_names
    assert "get_due_words" in tool_names
    assert turn_start["verdict"]["passed"] is True

    # 2. Active usage of 'abholen' updates the SRS grid to 'mastered'
    turn_use = backend.handle_chat(
        profile_id="riccardo",
        query="Ich muss heute Nachmittag meine Kinder von der Schule abholen.",
        is_session_start=False,
    )
    assert any(
        tc["tool_name"] == "record_word_attempt"
        for tc in turn_use["trajectory"]["tool_calls"]
    )
    abholen_tile = next(
        w for w in turn_use["state"]["curriculum_grid"] if w["lemma"] == "abholen"
    )
    assert abholen_tile["status"] == "learning"
    assert abholen_tile["interval_days"] == 1

    # 3. Second active usage of 'abholen' advances interval to 7 days
    turn_use_2 = backend.handle_chat(
        profile_id="riccardo",
        query="Gestern habe ich meinen Freund am Zürcher Hauptbahnhof abgeholt.",
        is_session_start=False,
    )
    abholen_tile_2 = next(
        w for w in turn_use_2["state"]["curriculum_grid"] if w["lemma"] == "abholen"
    )
    assert abholen_tile_2["repetition_count"] == 2
    assert abholen_tile_2["interval_days"] == 7


def test_webapp_backend_eval_and_flawed_turn_simulation(tmp_path: Path):
    """Verifies running the 4 trajectory eval suites and simulating a flawed LLM turn for the Judge & BugRouter UI."""
    backend = HummerliWebBackend(data_dir=tmp_path)

    eval_summary = backend.run_evals()
    assert eval_summary["status"] == "SUCCESS"
    assert eval_summary["total_suites"] == 4
    assert eval_summary["overall_tool_trajectory_score"] == 1.0

    # Simulate a flawed turn where the LLM forgets record_word_attempt and replies in English
    flawed = backend.simulate_flawed_turn(profile_id="riccardo")
    assert flawed["verdict"]["passed"] is False
    assert len(flawed["issues"]) >= 1
    assert flawed["issues"][0]["target_repo"] == "palladius/hummerli-b1-adk-pvt"
    assert "Cosa ha SBAGLIATO la LLM" in flawed["digest_markdown"]
