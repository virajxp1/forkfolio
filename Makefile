PYTHON_BIN := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
RUFF_BIN := $(shell if [ -x .venv/bin/ruff ]; then echo .venv/bin/ruff; else echo ruff; fi)

run:
	$(PYTHON_BIN) scripts/run.py --reload

start:
	$(PYTHON_BIN) scripts/run.py

test:
	$(PYTHON_BIN) -m pytest -c pytest.ini app/tests/unit/ -q

test-e2e:
	$(PYTHON_BIN) -m pytest -c pytest.ini app/tests/e2e/ -v

test-all:
	$(PYTHON_BIN) -m pytest -c pytest.ini app/tests/ -v

lint:
	$(RUFF_BIN) check .
	$(RUFF_BIN) format --check .

format:
	$(RUFF_BIN) check --fix .
	$(RUFF_BIN) format .

# Optional Docker flows (not required for Render deploys).
docker-build:
	docker build -t forkfolio -f docker/Dockerfile .

docker-up:
	docker compose -f docker/docker-compose.yml up --build
