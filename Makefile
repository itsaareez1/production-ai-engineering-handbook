.PHONY: help venv run test lint labs verify verify-db verify-docker docker down clean

PY := .venv/bin/python

help:
	@echo "make venv           create .venv and install dependencies"
	@echo "make all            run every book listing"
	@echo "make test           run the test suite (offline, mock provider)"
	@echo "make lint           flake8 over the code"
	@echo "make labs           run the offline labs (1-4, 6, 7)"
	@echo "make verify         lint + tests + listings + labs: the manual release check"
	@echo "make verify-db      Postgres integration tests and Listing 14.2"
	@echo "                    (needs ATLAS_TEST_DATABASE_URL, a disposable database)"
	@echo "make verify-docker  Lab 5: build, start, and verify the Compose stack"
	@echo "make docker / down  start / stop the Compose stack"
	@echo "make clean          remove generated files"

venv:
	python3 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r requirements-dev.txt

all:
	$(PY) run.py --all

test:
	$(PY) -m pytest tests/ -q

lint:
	$(PY) -m flake8 atlas tests labs listings run.py

labs:
	$(PY) labs/lab01-rag/lab.py
	$(PY) labs/lab02-model-gateway/lab.py
	$(PY) labs/lab03-evaluation/lab.py
	$(PY) labs/lab04-agent-security/lab.py
	$(PY) labs/lab06-observability/lab.py
	$(PY) labs/lab07-production-readiness/lab.py --quick

verify: lint test all labs
	$(PY) listings/ch21/validate_21_1.py
	diff Dockerfile listings/ch44/Dockerfile
	diff docker-compose.yml listings/ch44/docker-compose.yml
	@echo "verify: all offline checks passed"

verify-db:
	@test -n "$(ATLAS_TEST_DATABASE_URL)" || (echo "set ATLAS_TEST_DATABASE_URL" && exit 1)
	$(PY) -m pytest tests/integration -q
	$(PY) listings/ch14/verify_14_2.py "$(ATLAS_TEST_DATABASE_URL)"

verify-docker:
	$(PY) labs/lab05-deployment/lab.py
	$(PY) labs/lab05-deployment/lab.py --down

docker:
	docker compose up --build

down:
	docker compose down -v

clean:
	rm -rf __pycache__ .pytest_cache instructions .replay
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
