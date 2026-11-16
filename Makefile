.PHONY: install test lint data
install: ; pip install -e ".[dev]"
test:    ; pytest -q
lint:    ; ruff check src tests scripts
data:    ; python scripts/run_phase1.py --months 12
