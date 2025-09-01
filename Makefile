.PHONY: setup run test compose-up
setup:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
test:
	pytest -q
compose-up:
	docker compose up --build
