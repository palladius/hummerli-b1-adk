"""Tests for Level-2 LLM-as-Judge Trajectory & Pedagogical Analyzer and Dual-Repo Bug Router."""

from hummerli.agent import TurnTrajectory, ToolCallEvent
from hummerli.eval.judge import (
    JudgeAnalyzer,
    BugRouter,
    generate_daily_digest,
)


def test_judge_detects_harness_missing_srs_tool_call():
    """When Riccardo uses 'abholen' in a sentence and the agent forgets record_word_attempt, Judge flags a harness bug."""
    analyzer = JudgeAnalyzer()

    bad_turn = TurnTrajectory(
        user_input="Ich muss heute meine Kinder von der Schule abholen.",
        profile_id="riccardo",
        active_persona="Frau Leonie Blücher",
        language="de",
        tool_calls=[],  # BUG: forgot to call record_word_attempt!
        final_response="Sehr gut! Das hast du schön gesagt. Was machst du danach?",
    )

    verdict = analyzer.evaluate_turn(bad_turn, target_lemmata=["abholen"])
    assert verdict.passed is False
    assert any(a.code == "MISSING_SRS_RECORD_ON_WORD_USE" for a in verdict.anomalies)
    assert any(a.category == "harness" for a in verdict.anomalies)


def test_judge_detects_pedagogical_and_model_errors():
    """Judge catches wrong language (English), vague feedback ('Bravo!'), and false grammar corrections."""
    analyzer = JudgeAnalyzer()

    # 1. Wrong language (English instead of German/Italian)
    english_turn = TurnTrajectory(
        user_input="Ich habe den Antrag bei der Gemeinde eingereicht.",
        profile_id="riccardo",
        active_persona="Frau Leonie Blücher",
        language="de",
        tool_calls=[
            ToolCallEvent(
                tool_name="record_word_attempt",
                tool_args={"profile_id": "riccardo", "lemma": "Antrag", "quality": 5},
            )
        ],
        final_response="Great job Riccardo! You used the word correctly in your sentence.",
    )
    v_eng = analyzer.evaluate_turn(english_turn, target_lemmata=["Antrag"])
    assert v_eng.passed is False
    assert any(a.code == "WRONG_TUTOR_LANGUAGE" and a.category == "skill" for a in v_eng.anomalies)

    # 2. False grammar correction + vague feedback
    false_corr_turn = TurnTrajectory(
        user_input="Ich bin gestern nach Zürich gefahren.",
        profile_id="riccardo",
        active_persona="Frau Leonie Blücher",
        language="de",
        tool_calls=[],
        final_response="Bravo! Aber 'gefahren' ist falsch.",
    )
    v_false = analyzer.evaluate_turn(false_corr_turn, target_lemmata=[])
    assert v_false.passed is False
    codes = {a.code for a in v_false.anomalies}
    assert "FALSE_GRAMMAR_CORRECTION" in codes
    assert any(a.category == "model" for a in v_false.anomalies)


def test_dual_repo_bug_router_public_vs_private():
    """Verifies that synthetic harness bugs go to public repo while personal/audio/model bugs go to private repo."""
    analyzer = JudgeAnalyzer()
    router = BugRouter(
        public_repo="palladius/hummerli-b1-adk",
        private_repo="palladius/hummerli-b1-adk-pvt",
    )

    # Synthetic harness bug (no personal audio, pure tool call failure) -> PUBLIC repo
    harness_turn = TurnTrajectory(
        user_input="Ich muss meine Kinder abholen.",
        profile_id="synthetic_ci",
        tool_calls=[],
        final_response="Sehr gut gemacht in diesem Satz!",
    )
    v_harness = analyzer.evaluate_turn(harness_turn, target_lemmata=["abholen"])
    issues_public = router.build_issues_from_verdict(v_harness, is_personal_session=False)
    assert len(issues_public) >= 1
    assert issues_public[0].target_repo == "palladius/hummerli-b1-adk"
    assert "bug:harness" in issues_public[0].labels

    # Riccardo's real session with GCS audio evidence or model/skill bug -> PRIVATE repo
    personal_turn = TurnTrajectory(
        user_input="Ich habe den Antrag eingereicht.",
        profile_id="riccardo",
        tool_calls=[],
        final_response="Great job! Well done!",
    )
    v_personal = analyzer.evaluate_turn(
        personal_turn,
        target_lemmata=["Antrag"],
        audio_gcs_uri="gs://hummerli-audio-vault/profiles/riccardo/sessions/2026-10-17/001_user.ogg",
    )
    issues_private = router.build_issues_from_verdict(v_personal, is_personal_session=True)
    assert len(issues_private) >= 1
    assert all(iss.target_repo == "palladius/hummerli-b1-adk-pvt" for iss in issues_private)
    assert "gs://hummerli-audio-vault/" in issues_private[0].body


def test_generate_daily_digest_markdown():
    """Verifies the Daily Digest Markdown contains what Riccardo said, what LLM did, and what LLM got wrong."""
    analyzer = JudgeAnalyzer()
    router = BugRouter()

    good_turn = TurnTrajectory(
        user_input="Ich muss heute meine Kinder von der Schule abholen.",
        profile_id="riccardo",
        tool_calls=[
            ToolCallEvent(
                tool_name="record_word_attempt",
                tool_args={"profile_id": "riccardo", "lemma": "abholen", "quality": 5},
            )
        ],
        final_response="Ausgezeichnet! Sie haben 'abholen' perfekt am Satzende benutzt.",
    )
    bad_turn = TurnTrajectory(
        user_input="Ich habe ein neues Gesuch bei der Gemeinde eingereicht.",
        profile_id="riccardo",
        tool_calls=[],
        final_response="Great! Bravo!",
    )

    v1 = analyzer.evaluate_turn(good_turn, target_lemmata=["abholen"])
    v2 = analyzer.evaluate_turn(bad_turn, target_lemmata=["Gesuch"])

    digest_md = generate_daily_digest(
        profile_id="riccardo",
        date_str="2026-10-17",
        verdicts=[v1, v2],
        bug_router=router,
    )

    assert "2026-10-17" in digest_md
    assert "Cosa ha detto Riccardo" in digest_md
    assert "Cosa ha fatto la LLM" in digest_md
    assert "Cosa ha SBAGLIATO la LLM" in digest_md
    assert "MISSING_SRS_RECORD_ON_WORD_USE" in digest_md
    assert "palladius/hummerli-b1-adk-pvt" in digest_md
