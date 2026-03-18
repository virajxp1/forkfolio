VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_RUFF := $(VENV_DIR)/bin/ruff
VENV_DEPS_STAMP := $(VENV_DIR)/.deps-ready
PYTHON_BIN := $(shell if [ -x $(VENV_PYTHON) ]; then echo $(VENV_PYTHON); else echo python3; fi)
RUFF_BIN := $(shell if [ -x $(VENV_RUFF) ]; then echo $(VENV_RUFF); else echo ruff; fi)

setup-python:
	uv python install 3.11
	@if [ -d $(VENV_DIR) ]; then mv $(VENV_DIR) $(VENV_DIR)_backup_$$(date +%Y%m%d_%H%M%S); fi
	uv venv --python 3.11 $(VENV_DIR)
	uv pip install --python $(VENV_PYTHON) -r requirements.txt
	@touch $(VENV_DEPS_STAMP)

ensure-python:
	@if [ ! -x $(VENV_PYTHON) ]; then \
		echo "No local virtual environment found. Bootstrapping with 'make setup-python'..."; \
		$(MAKE) setup-python; \
	elif [ ! -f $(VENV_DEPS_STAMP) ] || [ requirements.txt -nt $(VENV_DEPS_STAMP) ]; then \
		echo "Installing/updating Python dependencies from requirements.txt..."; \
		uv pip install --python $(VENV_PYTHON) -r requirements.txt && \
		touch $(VENV_DEPS_STAMP); \
	fi

sync-requirements:
	uv pip compile requirements.in -o requirements.txt

run: ensure-python
	$(VENV_PYTHON) scripts/run.py --reload

run-fe:
	bash scripts/run_fe.sh

start: ensure-python
	$(VENV_PYTHON) scripts/run.py

test:
	$(PYTHON_BIN) -m pytest -c pytest.ini app/tests/unit/ -q

test-e2e:
	$(PYTHON_BIN) -m pytest -c pytest.ini app/tests/e2e/ -v

test-all:
	$(PYTHON_BIN) -m pytest -c pytest.ini app/tests/ -v

lint:
	$(RUFF_BIN) check .
	$(RUFF_BIN) format --check .
	$(PYTHON_BIN) -m scripts.validate_openapi

validate-openapi:
	$(PYTHON_BIN) -m scripts.validate_openapi

format:
	$(RUFF_BIN) check --fix .
	$(RUFF_BIN) format .

# Optional Docker flows.
docker-build:
	docker build -t forkfolio -f docker/Dockerfile .

docker-up:
	docker compose -f docker/docker-compose.yml up --build
