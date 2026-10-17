"""Unit tests for Hummerli ADK Tools and Dual-Persona Agent (Frau Blücher & Rijckard)."""

from pathlib import Path

from hummerli.tools import HummerliToolset
from hummerli.agent import create_hummerli_agent, HummerliAgent


def test_adk_toolset_contracts(tmp_path: Path):
    toolset = HummerliToolset(data_dir=tmp_path)

    # 1. get_profile_context
    ctx = toolset.get_profile_context("riccardo")
    assert ctx["profile_id"] == "riccardo"
    assert ctx["target_level"] == "B1"
    assert ctx["tutor_voice"] == "de-DE-Neural2-F"
    assert ctx["coach_voice"] == "it-IT-Neural2-C"

    # 2. get_due_words
    due = toolset.get_due_words("riccardo", limit=3)
    assert len(due) == 3
    assert all("lemma" in w and "example_de" in w for w in due)

    # 3. record_word_attempt
    res = toolset.record_word_attempt(
        profile_id="riccardo",
        lemma="abholen",
        quality=5,
        user_sentence="Ich muss meine Kinder von der Schule abholen.",
        tutor_comment="Sehr gut, trennbares Verb korrekt am Ende!",
        used_actively=True,
    )
    assert res["lemma"] == "abholen"
    assert res["status"] == "learning"
    assert res["interval_days"] == 1

    # 4. explain_in_italian (Rijckard coach intervention)
    coach_res = toolset.explain_in_italian(
        concept_or_phrase="abholen",
        user_question="Non ho capito cosa significa abholen e come si usa.",
        profile_id="riccardo",
    )
    assert coach_res["persona"] == "Rijckard"
    assert coach_res["voice"] == "it-IT-Neural2-C"
    assert coach_res["language"] == "it"
    assert "abholen" in coach_res["explanation_it"].lower()
    assert coach_res["handoff_back_to"] == "Frau Leonie Blücher"


def test_agent_creation_and_subagents(tmp_path: Path):
    agent = create_hummerli_agent(data_dir=tmp_path)
    assert isinstance(agent, HummerliAgent)
    assert agent.name == "frau_bluecher"
    assert "rijckard_coach" in [sa.name for sa in agent.sub_agents]
    tool_names = [t.__name__ for t in agent.tools]
    assert "get_profile_context" in tool_names
    assert "get_due_words" in tool_names
    assert "record_word_attempt" in tool_names
    assert "explain_in_italian" in tool_names
