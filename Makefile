.PHONY: help venv run test all docker clean

PY := .venv/bin/python

help:
	@echo "make venv     create .venv and install dependencies"
	@echo "make all      run every listing"
	@echo "make test     run the test suite"
	@echo "make docker   build and start the Atlas service"
	@echo "make clean    remove generated files"

venv:
	python3 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r requirements-dev.txt

all:
	$(PY) run.py --all

test:
	$(PY) -m pytest tests/ -q
	$(PY) listings/ch21/validate_21_1.py
	diff Dockerfile listings/ch44/Dockerfile
	diff docker-compose.yml listings/ch44/docker-compose.yml

docker:
	docker compose build
	docker compose up

clean:
	rm -rf __pycache__ .pytest_cache instructions .replay
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
