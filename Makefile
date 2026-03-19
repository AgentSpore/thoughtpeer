.PHONY: run dev test smoke

run:
	uvicorn thoughtpeer.main:app --host 0.0.0.0 --port 8000

dev:
	uv sync && PYTHONPATH=src uvicorn thoughtpeer.main:app --reload --port 8000

test:
	uv run pytest tests/ -v

smoke:
	PYTHONPATH=src uv run python smoke_test.py
