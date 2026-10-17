"""Trajectory evaluation tests for Hummerli ADK agent flows."""

from pathlib import Path

from hummerli.agent import TurnTrajectory, ToolCallEvent
from hummerli.eval.trajectory import TrajectoryEvaluator, run_all_trajectory_evals


TRAJECTORIES_DIR = Path(__file__).parent / "trajectories"


def test_all_adk_trajectory_fixtures_pass(tmp_path: Path):
    """Runs all 4 ADK .test.json trajectory suites and asserts 100% tool trajectory accuracy."""
    summary = run_all_trajectory_evals(
        trajectories_dir=TRAJECTORIES_DIR,
        data_dir=tmp_path,
    )
    assert summary["status"] == "SUCCESS"
    assert summary["total_suites"] == 4
    assert summary["overall_tool_trajectory_score"] == 1.0
    assert summary["overall_keyword_score"] == 1.0

    for suite_id in [
        "session_init_b1",
        "word_mastery_abholen",
        "coach_handoff_non_ho_capito",
        "struggling_word_retry",
    ]:
        suite_res = summary["suites"][suite_id]
        assert suite_res["passed"] is True, f"Suite {suite_id} failed: {suite_res}"
        assert suite_res["tool_trajectory_avg_score"] == 1.0


def test_trajectory_scorer_detects_missing_or_wrong_tools():
    """Verifies that TrajectoryEvaluator catches missing tool calls or wrong arguments."""
    evaluator = TrajectoryEvaluator()

    expected = [
        {"tool_name": "get_profile_context", "tool_args": {"profile_id": "riccardo"}},
        {"tool_name": "get_due_words", "tool_args": {"profile_id": "riccardo", "limit": 3}},
    ]

    # Case 1: Exact match -> 1.0
    actual_good = [
        ToolCallEvent(tool_name="get_profile_context", tool_args={"profile_id": "riccardo"}),
        ToolCallEvent(tool_name="get_due_words", tool_args={"profile_id": "riccardo", "limit": 3}),
    ]
    assert evaluator.score_tool_trajectory(expected, actual_good) == 1.0

    # Case 2: Only called 1 of 2 expected tools -> 0.5
    actual_partial = [
        ToolCallEvent(tool_name="get_profile_context", tool_args={"profile_id": "riccardo"}),
    ]
    score_partial = evaluator.score_tool_trajectory(expected, actual_partial)
    assert 0.4 <= score_partial <= 0.6

    # Case 3: Called completely wrong tool -> 0.0
    actual_wrong = [
        ToolCallEvent(tool_name="explain_in_italian", tool_args={"concept_or_phrase": "x"}),
    ]
    assert evaluator.score_tool_trajectory(expected, actual_wrong) == 0.0
