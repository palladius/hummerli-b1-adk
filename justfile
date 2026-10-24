set dotenv-load := true

default:
    @just --list

# Run all unit and trajectory evaluation tests
test:
    PYTHONPATH=src .venv/bin/pytest

# Run only trajectory and LLM-as-Judge evaluations
eval:
    PYTHONPATH=src .venv/bin/pytest tests/evals/ -v

# Run standalone ADK Trajectory Quality Flywheel report
eval-report:
    PYTHONPATH=src .venv/bin/python -m hummerli.cli eval --export-report

# Show SRS vocabulary status for a profile (default: riccardo)
srs profile="riccardo":
    PYTHONPATH=src .venv/bin/python -m hummerli.cli srs --profile {{profile}}

# Generate daily LLM-as-Judge evaluation digest
digest profile="riccardo":
    PYTHONPATH=src .venv/bin/python -m hummerli.cli digest --profile {{profile}}

# Launch Hummerli Server on 0.0.0.0:8788 (accessible from Computer + Phone via Wi-Fi / Tailscale)
web port="8788":
    PYTHONPATH=src .venv/bin/python -m hummerli.cli web --host 0.0.0.0 --port {{port}}

# Open Hummerli as a standalone frameless Desktop App window (Pallino Vocale mode)
app port="8788":
    google-chrome --app="http://localhost:{{port}}/?mode=orb" --window-size=460,820 >/dev/null 2>&1 &
