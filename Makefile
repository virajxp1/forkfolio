PYTHON_BIN := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
RUFF_BIN := $(shell if [ -x .venv/bin/ruff ]; then echo .venv/bin/ruff; else echo ruff; fi)

build:
	docker build -t myapp -f docker/Dockerfile .

up:
	docker compose -f docker/docker-compose.yml up --build

test:
	$(PYTHON_BIN) -m pytest -c pytest.ini app/tests/unit/ -q

lint:
	$(RUFF_BIN) check .
	$(RUFF_BIN) format --check .
