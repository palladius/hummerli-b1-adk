"""Typer CLI for Hummerli: SRS inspection, Trajectory Evals, Daily Judge Digest, and Turn Simulation."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from hummerli.agent import ToolCallEvent, TurnTrajectory, create_hummerli_agent
from hummerli.eval.judge import BugRouter, JudgeAnalyzer, generate_daily_digest
from hummerli.eval.trajectory import run_all_trajectory_evals

app = typer.Typer(
    name="hummerli",
    help="Hummerli (FIDE / Goethe B1 Zürich) Oral Tutor, SM-2 SRS Engine & Trajectory Evaluator.",
    add_completion=False,
)
console = Console()

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAJECTORIES_DIR = REPO_ROOT / "tests" / "evals" / "trajectories"
DEFAULT_EVAL_RESULTS_DIR = REPO_ROOT / "data" / "eval_results"


@app.command("srs")
def srs_cmd(
    profile: str = typer.Option("riccardo", "--profile", "-p", help="Learner profile ID."),
    limit: int = typer.Option(5, "--limit", "-n", help="Number of due words to preview."),
    data_dir: Optional[Path] = typer.Option(None, "--data-dir", help="Custom data directory."),
) -> None:
    """Displays the learner's SRS mastery heatmap summary and top due B1 words."""
    agent = create_hummerli_agent(data_dir=data_dir)
    assert agent.toolset is not None
    ctx = agent.toolset.get_profile_context(profile_id=profile)
    due = agent.toolset.get_due_words(profile_id=profile, limit=limit)

    summary = ctx["srs_heatmap"]
    console.print(
        f"[bold cyan]🐎 Hummerli SRS Status — {ctx['display_name']} ({ctx['target_level']})[/bold cyan]"
    )
    console.print(
        f"Curriculum: [bold]{ctx['curriculum']}[/bold] | "
        f"Total: {summary['total_curriculum']} | "
        f"[green]Mastered: {summary['mastered_green']}[/green] | "
        f"[yellow]Learning: {summary['learning_yellow']}[/yellow] | "
        f"[red]Struggling: {summary['struggling_red']}[/red] | "
        f"Unseen: {summary['unseen']}"
    )

    table = Table(title=f"Top {len(due)} Due Vocabulary Words")
    table.add_column("Headword", style="bold")
    table.add_column("POS")
    table.add_column("Status")
    table.add_column("Interval (d)")
    table.add_column("Italian")
    for w in due:
        table.add_row(
            w["display_headword"],
            w["pos"],
            w["srs_status"],
            str(w["interval_days"]),
            w["translation_it"],
        )
    console.print(table)


@app.command("eval")
def eval_cmd(
    trajectories_dir: Path = typer.Option(
        DEFAULT_TRAJECTORIES_DIR, "--trajectories-dir", help="Path to .test.json suites."
    ),
    export_report: bool = typer.Option(
        False, "--export-report", help="Export JSON summary report."
    ),
    output_dir: Path = typer.Option(
        DEFAULT_EVAL_RESULTS_DIR, "--output-dir", help="Directory for exported eval report."
    ),
) -> None:
    """Runs all Level-1 ADK Trajectory evaluation suites and prints scores."""
    out = output_dir if export_report else None
    summary = run_all_trajectory_evals(
        trajectories_dir=trajectories_dir,
        output_dir=out,
    )
    console.print(
        f"[bold]ADK Trajectory Evaluation Status:[/bold] {summary['status']} "
        f"(Suites: {summary['total_suites']}, "
        f"Tool Trajectory Score: {summary['overall_tool_trajectory_score']}, "
        f"Keyword Score: {summary['overall_keyword_score']})"
    )
    for suite_id, suite_res in summary["suites"].items():
        badge = "✅ PASS" if suite_res["passed"] else "❌ FAIL"
        console.print(
            f"  • {badge} [bold]{suite_id}[/bold]: "
            f"tool_trajectory_avg_score={suite_res['tool_trajectory_avg_score']}, "
            f"keyword_avg_score={suite_res['keyword_avg_score']}"
        )
    if summary["status"] != "SUCCESS":
        raise typer.Exit(code=1)


@app.command("digest")
def digest_cmd(
    profile: str = typer.Option("riccardo", "--profile", "-p", help="Learner profile ID."),
    date_str: str = typer.Option(
        default_factory=lambda: date.today().isoformat(),
        help="Session date (YYYY-MM-DD).",
    ),
    output_dir: Optional[Path] = typer.Option(
        None, "--output-dir", help="Optional directory to write the Markdown digest."
    ),
) -> None:
    """Generates a Level-2 LLM-as-Judge Daily Digest (with sample good + flawed trajectories)."""
    analyzer = JudgeAnalyzer()
    router = BugRouter()

    sample_good = TurnTrajectory(
        user_input="Ich muss heute meine Kinder von der Schule abholen.",
        profile_id=profile,
        tool_calls=[
            ToolCallEvent(
                tool_name="record_word_attempt",
                tool_args={"profile_id": profile, "lemma": "abholen", "quality": 5},
            )
        ],
        final_response="Ausgezeichnet! Sie haben 'abholen' perfekt am Satzende verwendet.",
    )
    sample_flawed = TurnTrajectory(
        user_input="Ich habe gestern den Antrag bei der Gemeinde eingereicht.",
        profile_id=profile,
        tool_calls=[],
        final_response="Great job! Bravo!",
    )

    verdicts = [
        analyzer.evaluate_turn(sample_good, target_lemmata=["abholen"]),
        analyzer.evaluate_turn(
            sample_flawed,
            target_lemmata=["Antrag"],
            audio_gcs_uri=f"gs://hummerli-audio-vault/profiles/{profile}/sessions/{date_str}/002_user.ogg",
        ),
    ]
    md = generate_daily_digest(
        profile_id=profile,
        date_str=date_str,
        verdicts=verdicts,
        bug_router=router,
    )
    console.print(md)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_file = output_dir / f"{date_str}-{profile}-digest.md"
        out_file.write_text(md, encoding="utf-8")


@app.command("simulate")
def simulate_cmd(
    query: str = typer.Option(..., "--query", "-q", help="User utterance in German or Italian."),
    profile: str = typer.Option("riccardo", "--profile", "-p", help="Learner profile ID."),
    session_start: bool = typer.Option(False, "--session-start", help="Start a new session."),
    data_dir: Optional[Path] = typer.Option(None, "--data-dir", help="Custom data directory."),
) -> None:
    """Simulates a single conversational turn with Frau Blücher / Rijckard and prints the ADK trajectory."""
    agent = create_hummerli_agent(data_dir=data_dir)
    traj = agent.run_turn(
        user_input=query,
        profile_id=profile,
        is_session_start=session_start,
    )
    console.print(f"[bold]Active Persona:[/bold] {traj.active_persona} ({traj.voice})")
    console.print("[bold]ADK Tool Trajectory:[/bold]")
    for tc in traj.tool_calls:
        console.print(f"  → {tc.tool_name}({tc.tool_args})")
    console.print(f"\n[bold green]Response:[/bold green]\n{traj.final_response}")


@app.command("web")
def web_cmd(
    host: str = typer.Option("127.0.0.1", "--host", help="Host address to bind."),
    port: int = typer.Option(8788, "--port", "-p", help="Port for the Hummerli Web Studio."),
    data_dir: Optional[Path] = typer.Option(None, "--data-dir", help="Custom data directory."),
) -> None:
    """Launches the interactive Hummerli B1 Web Studio (Chat, Voice, SRS Heatmap & Trajectory Eval Inspector)."""
    from hummerli.webapp import run_web_server

    run_web_server(host=host, port=port, data_dir=data_dir)


if __name__ == "__main__":
    app()
