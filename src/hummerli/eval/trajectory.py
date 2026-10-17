"""Level-1 ADK Trajectory Evaluator for Hummerli `.test.json` conversation suites."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Optional

from hummerli.agent import ToolCallEvent, create_hummerli_agent


class TrajectoryEvaluator:
    """Evaluates ADK tool call trajectories and response keywords against `.test.json` fixtures."""

    def score_tool_trajectory(
        self,
        expected_tool_use: list[dict[str, Any]],
        actual_tool_calls: list[ToolCallEvent],
    ) -> float:
        """Computes tool_trajectory_avg_score in [0.0, 1.0] comparing expected vs actual tool calls."""
        if not expected_tool_use:
            return 1.0 if not actual_tool_calls else 0.0
        if not actual_tool_calls:
            return 0.0

        matched_count = 0
        for idx, exp in enumerate(expected_tool_use):
            if idx >= len(actual_tool_calls):
                break
            act = actual_tool_calls[idx]
            if act.tool_name != exp.get("tool_name"):
                continue
            exp_args = exp.get("tool_args", {})
            args_ok = True
            for k, v in exp_args.items():
                if act.tool_args.get(k) != v:
                    args_ok = False
                    break
            if args_ok:
                matched_count += 1

        # Penalize extra unexpected tool calls if any
        denom = max(len(expected_tool_use), len(actual_tool_calls))
        return round(matched_count / denom, 4)

    def score_reference_keywords(
        self,
        reference_keywords: list[str],
        final_response: str,
    ) -> float:
        """Computes fraction of expected reference keywords present in the final response."""
        if not reference_keywords:
            return 1.0
        resp_lower = final_response.lower()
        hits = sum(1 for kw in reference_keywords if kw.lower() in resp_lower)
        return round(hits / len(reference_keywords), 4)

    def evaluate_suite(
        self,
        suite_path: Path,
        data_dir: Optional[Path] = None,
    ) -> dict[str, Any]:
        """Executes a single `.test.json` trajectory suite in an isolated workspace and returns metrics."""
        spec = json.loads(suite_path.read_text(encoding="utf-8"))
        eval_set_id = spec.get("eval_set_id", suite_path.stem.replace(".test", ""))
        profile_id = spec.get("profile_id", "riccardo")

        if data_dir is not None:
            suite_data_dir = data_dir / eval_set_id
            suite_data_dir.mkdir(parents=True, exist_ok=True)
            res = self._run_turns(spec, profile_id, suite_data_dir)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                res = self._run_turns(spec, profile_id, Path(tmp))

        return {
            "eval_set_id": eval_set_id,
            "description": spec.get("description", ""),
            **res,
        }

    def _run_turns(
        self,
        spec: dict[str, Any],
        profile_id: str,
        suite_data_dir: Path,
    ) -> dict[str, Any]:
        agent = create_hummerli_agent(data_dir=suite_data_dir)
        turn_results: list[dict[str, Any]] = []
        tool_scores: list[float] = []
        kw_scores: list[float] = []
        all_passed = True

        for turn_spec in spec.get("turns", []):
            turn_id = turn_spec.get("turn_id", "turn")
            query = turn_spec["query"]
            is_start = bool(turn_spec.get("is_session_start", False))

            traj = agent.run_turn(
                user_input=query,
                profile_id=profile_id,
                is_session_start=is_start,
            )

            expected_tools = turn_spec.get("expected_tool_use", [])
            t_score = self.score_tool_trajectory(expected_tools, traj.tool_calls)
            k_score = self.score_reference_keywords(
                turn_spec.get("reference_keywords", []),
                traj.final_response,
            )

            exp_persona = turn_spec.get("expected_persona")
            persona_ok = exp_persona is None or traj.active_persona == exp_persona
            exp_lang = turn_spec.get("expected_language")
            lang_ok = exp_lang is None or traj.language == exp_lang

            turn_passed = (t_score == 1.0) and (k_score == 1.0) and persona_ok and lang_ok
            if not turn_passed:
                all_passed = False

            tool_scores.append(t_score)
            kw_scores.append(k_score)
            turn_results.append(
                {
                    "turn_id": turn_id,
                    "passed": turn_passed,
                    "tool_trajectory_score": t_score,
                    "keyword_score": k_score,
                    "active_persona": traj.active_persona,
                    "language": traj.language,
                    "actual_tool_calls": [tc.model_dump() for tc in traj.tool_calls],
                    "final_response": traj.final_response,
                }
            )

        avg_tool = round(sum(tool_scores) / len(tool_scores), 4) if tool_scores else 1.0
        avg_kw = round(sum(kw_scores) / len(kw_scores), 4) if kw_scores else 1.0
        return {
            "passed": all_passed,
            "tool_trajectory_avg_score": avg_tool,
            "keyword_avg_score": avg_kw,
            "turns": turn_results,
        }


def run_all_trajectory_evals(
    trajectories_dir: Path,
    data_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Runs all `*.test.json` suites in trajectories_dir and optionally writes a summary report."""
    evaluator = TrajectoryEvaluator()
    suite_files = sorted(trajectories_dir.glob("*.test.json"))
    suites_report: dict[str, Any] = {}
    tool_scores: list[float] = []
    kw_scores: list[float] = []
    all_passed = True

    for suite_file in suite_files:
        res = evaluator.evaluate_suite(suite_file, data_dir=data_dir)
        suite_id = res["eval_set_id"]
        suites_report[suite_id] = res
        tool_scores.append(res["tool_trajectory_avg_score"])
        kw_scores.append(res["keyword_avg_score"])
        if not res["passed"]:
            all_passed = False

    overall_tool = round(sum(tool_scores) / len(tool_scores), 4) if tool_scores else 0.0
    overall_kw = round(sum(kw_scores) / len(kw_scores), 4) if kw_scores else 0.0
    summary = {
        "status": "SUCCESS" if all_passed and suite_files else "FAILED",
        "total_suites": len(suite_files),
        "overall_tool_trajectory_score": overall_tool,
        "overall_keyword_score": overall_kw,
        "suites": suites_report,
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "trajectory_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return summary
