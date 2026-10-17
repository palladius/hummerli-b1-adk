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
