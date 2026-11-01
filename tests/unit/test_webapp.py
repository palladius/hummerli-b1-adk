"""Unit tests for the Hummerli Interactive Web Application & REST API (Tracks 1–5)."""

from pathlib import Path

from hummerli.webapp import DASHBOARD_HTML, HummerliWebBackend


def test_webapp_backend_state_and_chat(tmp_path: Path):
    """Verifies that the web backend returns profile state, heatmap, scenarios, karaoke, and processes chat turns."""
    backend = HummerliWebBackend(data_dir=tmp_path)

    state = backend.get_state(profile_id="riccardo", client_layout="mobile_portrait")
    assert state["profile"]["profile_id"] == "riccardo"
    assert state["profile"]["srs_heatmap"]["total_curriculum"] >= 25
    assert len(state["curriculum_grid"]) >= 25
    assert len(state["due_words"]) == 3
    assert len(state["scenarios"]) == 3
    assert state["scenarios"][0]["aspect_ratio"] == "1:1"
    assert len(state["karaoke_songs"]) >= 5
    assert state["gender_palette"]["F"]["color_hex"] == "#f472b6"
    assert state["gender_palette"]["M"]["color_hex"] == "#38bdf8"
    assert state["gender_palette"]["N"]["color_hex"] == "#94a3b8"

    # 1. Start session turn
    turn_start = backend.handle_chat(
        profile_id="riccardo",
        query="Hallo Frau Blücher, starten wir eine neue Übung!",
        is_session_start=True,
    )
    assert turn_start["trajectory"]["active_persona"] == "Frau Leonie Blücher"
    assert "annotated_response_html" in turn_start["trajectory"]
    tool_names = [tc["tool_name"] for tc in turn_start["trajectory"]["tool_calls"]]
    assert "get_profile_context" in tool_names
    assert "get_due_words" in tool_names
    assert turn_start["verdict"]["passed"] is True

    # 2. Active usage of 'abholen' updates the SRS grid and generates FideExamOutcomeCard
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


def test_webapp_scenarios_hotspots_karaoke_and_modality_endpoints(tmp_path: Path):
    """Tests Track 2 Director Override, Track 3 Scene Hotspots, Track 4 Gender CSS/JS, and Track 5 Karaoke + Piano B."""
    backend = HummerliWebBackend(data_dir=tmp_path)

    # Track 2: Mutate scenario with Italian director feedback
    mutated = backend.mutate_scenario(
        profile_id="riccardo",
        scenario_id="zuerich_park_hund",
        director_feedback_it="Si ma voglio ristorante indiano, invece di italiano e la tizia e' molto maleducata con me.",
        client_layout="desktop_landscape",
    )
    assert mutated["aspect_ratio"] == "16:9"
    assert "Indisches Restaurant" in mutated["title_de"]
    assert len(mutated["hotspots"]) >= 5
    assert len(mutated["sample_conversation"]["lines"]) >= 4

    # Track 5: Modality Piano B + Karaoke B2
    mod = backend.set_modality(profile_id="riccardo", can_listen=False, can_speak=False)
    assert mod["can_listen"] is False
    assert mod["can_speak"] is False
    assert mod["active_audio_channel"] == "silent_visual_beat"

    k_sess = backend.start_karaoke(
        profile_id="riccardo",
        song_id="wahnsinn",
        mode="stop_and_fill",
    )
    assert k_sess["song_id"] == "wahnsinn"
    assert k_sess["audio_strategy"] == "silent_visual_beat"

    k_ans = backend.submit_karaoke_answer(
        profile_id="riccardo",
        song_id="wahnsinn",
        line_index=0,
        user_answer="Hölle",
        mode="stop_and_fill",
    )
    assert k_ans["correct"] is True

    # Verify DASHBOARD_HTML includes Track 3, Track 4 (Ctrl+G & Rosa/Azzurrino/Grigio), and Track 5 UI elements
    assert "#f472b6" in DASHBOARD_HTML
    assert "#38bdf8" in DASHBOARD_HTML
    assert "#94a3b8" in DASHBOARD_HTML
    assert "gender-xray-active" in DASHBOARD_HTML
    assert "1. Vocabulary" in DASHBOARD_HTML
    assert "2. Sample Conversation" in DASHBOARD_HTML
    assert "Karaoke B2" in DASHBOARD_HTML


def test_webapp_backend_eval_and_flawed_turn_simulation(tmp_path: Path):
    """Verifies running all 8 trajectory eval suites and simulating a flawed LLM turn for the Judge & BugRouter UI."""
    backend = HummerliWebBackend(data_dir=tmp_path)

    eval_summary = backend.run_evals()
    assert eval_summary["status"] == "SUCCESS"
    assert eval_summary["total_suites"] == 8
    assert eval_summary["overall_tool_trajectory_score"] == 1.0

    flawed = backend.simulate_flawed_turn(profile_id="riccardo")
    assert flawed["verdict"]["passed"] is False
    assert len(flawed["issues"]) >= 1
    assert flawed["issues"][0]["target_repo"] == "palladius/hummerli-b1-adk-pvt"
    assert "Cosa ha SBAGLIATO la LLM" in flawed["digest_markdown"]
