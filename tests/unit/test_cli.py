"""Unit tests for the Hummerli Typer CLI (`srs`, `eval`, `digest`, `simulate`)."""

from pathlib import Path
from typer.testing import CliRunner

from hummerli.cli import app

runner = CliRunner()


def test_cli_srs_and_simulate(tmp_path: Path):
    """Verifies `hummerli srs` and `hummerli simulate` commands work against an isolated data_dir."""
    res_srs = runner.invoke(
        app,
        ["srs", "--profile", "riccardo", "--data-dir", str(tmp_path)],
    )
    assert res_srs.exit_code == 0
    assert "Riccardo" in res_srs.stdout
    assert "abholen" in res_srs.stdout

    res_sim = runner.invoke(
        app,
        [
            "simulate",
            "--profile",
            "riccardo",
            "--query",
            "Ich muss heute meine Kinder von der Schule abholen.",
            "--data-dir",
            str(tmp_path),
        ],
    )
    assert res_sim.exit_code == 0
    assert "record_word_attempt" in res_sim.stdout
    assert "Ausgezeichnet" in res_sim.stdout


def test_cli_eval_and_digest(tmp_path: Path):
    """Verifies `hummerli eval --export-report` and `hummerli digest` commands."""
    res_eval = runner.invoke(
        app,
        ["eval", "--export-report", "--output-dir", str(tmp_path)],
    )
    assert res_eval.exit_code == 0
    assert "SUCCESS" in res_eval.stdout
    assert (tmp_path / "trajectory_summary.json").exists()

    res_digest = runner.invoke(
        app,
        ["digest", "--profile", "riccardo", "--output-dir", str(tmp_path)],
    )
    assert res_digest.exit_code == 0
    assert "Cosa ha detto Riccardo" in res_digest.stdout
    assert "Cosa ha fatto la LLM" in res_digest.stdout
    assert "Cosa ha SBAGLIATO la LLM" in res_digest.stdout
