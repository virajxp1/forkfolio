# Audit Report

Date: 2026-02-10  
Scope: Full repository audit focused on code smell cleanup and code bloat reduction without changing external behavior.

## Repo Map

- Entry points:
  - `app/main.py` (FastAPI app + lifespan startup/shutdown)
  - `app/routers/api.py` (router composition)
  - `scripts/run.py` / `scripts/start_test_server.py` (local/test server launch)
- Core modules:
  - `app/core/` (settings, logging, dependency providers, prompts, exceptions)
  - `app/services/` (LLM cleanup/extraction/embedding + pipeline orchestration)
  - `app/services/data/` (psycopg2 connection pool and DB managers)
  - `app/api/v1/endpoints/` (health and recipes HTTP endpoints)
- Tooling and quality:
  - `config/pyproject.toml` (Ruff config)
  - `pytest.ini` (pytest config)
  - `config/.pre-commit-config.yaml` (hook config)
  - `.github/workflows/lint.yml`, `.github/workflows/test.yml`
- Tests:
  - `app/tests/unit/` (currently live API-dependent tests)
  - `app/tests/e2e/` (server + DB + LLM integrated workflow tests)

## Initial Audit Outline

1. Code smell hotspots (complexity, exception handling, noisy logging)  
2. Code bloat hotspots (duplication, oversized modules, redundant abstractions)  
3. Tooling correctness and enforceability  
4. Live/E2E testing workflow clarity and reliability (preserve current strategy)  
5. API contract consistency and error semantics  
6. Dependency hygiene and runtime/development separation

## Executive Summary (Top 10 Issues by Impact)

1. Guardrail configs were not being applied consistently by default commands (`ruff`/`pytest`) due config placement and pytest section format; this weakens debt prevention.  
2. The current test strategy is intentionally live/E2E-oriented, but lane naming and secret preconditions are not explicit enough, which creates confusion in local/CI execution.  
3. E2E tests require real Supabase + OpenRouter and currently fail hard in secretless environments (30s startup timeout) without fast preflight guidance.  
4. `health` endpoint unpacks DB context incorrectly and returns `"timestamp": "now()"` literal, indicating contract/implementation mismatch.  
5. Heavy use of `except Exception` across pipeline/data modules obscures root causes and prevents targeted recovery.  
6. `make_llm_call_text_generation` prints raw model output directly, risking noisy logs and accidental data leakage.  
7. `RecipeManager` is large and repetitive (300+ lines) with duplicated query assembly patterns and limited abstraction reuse.  
8. Test runner utilities hardcoded `python` and omitted config path, causing environment fragility and non-portable execution.  
9. Requirements file mixes runtime and dev tooling in one unconstrained list, increasing environment variance and install cost.  
10. Python 3.14 + `openai` warning surfaced (`pydantic.v1` compatibility warning), signaling forward-compatibility risk for CI/runtime images.

## Categorized Backlog

### Quick Wins

| Item | File paths | Why it matters | Risk | Suggested approach | Validation |
|---|---|---|---|---|---|
| Enforce one quality command set in CI/local | `.github/workflows/lint.yml`, `.github/workflows/test.yml`, `Makefile`, `README.md` | Prevents drift between local checks and CI checks | Low | Use the same direct Ruff/pytest commands across CI and local docs | Run documented commands locally and verify CI parity |
| Fix pytest config parsing and marker strictness | `pytest.ini` | Unknown markers were silently accepted; config not reliably enforced | Low | Use valid `[pytest]` section and strict markers | `pytest -c pytest.ini app/tests/unit -q` |
| Remove brittle pre-commit `.venv` path coupling | `config/.pre-commit-config.yaml` | Hooks failed outside exact local layout | Low | Use `ruff-pre-commit` hooks pinned by revision | `pre-commit run --all-files` |
| Make test runner interpreter-portable | `app/tests/utils/test_runners.py`, `app/tests/test_runner.py` | `python` binary may not exist; wrong config path | Low | Use `sys.executable` + explicit `-c pytest.ini` | `python3 app/tests/test_runner.py unit` |
| Clarify live vs E2E test lanes and prerequisites | `README.md`, `.github/workflows/test.yml`, `app/tests/*` | Preserves your testing strategy while reducing execution confusion | Low | Document lane purpose and required secrets; add fail-fast checks | Run each lane with/without secrets and verify expected behavior |
| Remove debug stdout in runtime LLM path | `app/services/llm_generation_service.py` | Unstructured output and possible sensitive payload leaks | Low | Replace `print` with structured logger | Add unit test for no-stdout side effect |

### Medium

| Item | File paths | Why it matters | Risk | Suggested approach | Validation |
|---|---|---|---|---|---|
| Expand bite-sized live smoke coverage for core flows | `app/tests/unit/`, `app/tests/e2e/` | Keeps your live-testing approach while improving signal on key contracts | Medium | Add a few focused live tests for high-value contracts and failure modes | CI smoke lane pass + explicit skips when secrets unavailable |
| Correct health endpoint DB context usage + real timestamp | `app/api/v1/endpoints/health.py`, `app/services/data/supabase_client.py` | Potential runtime exception + misleading health payload | Medium | Use proper connection/cursor context and ISO UTC timestamp | Add endpoint test with mocked DB context |
| Tighten exception taxonomy and logging | `app/services/recipe_processing_service.py`, `app/services/data/managers/recipe_manager.py`, `app/services/data/supabase_client.py` | Broad catches hide failure class and remediation path | Medium | Catch expected exceptions; preserve causal chain and context | Regression tests for error mapping and logs |
| Split runtime vs dev dependencies | `requirements.txt` (or split into `requirements-dev.txt`) | Smaller runtime surface, fewer supply-chain/compatibility surprises | Medium | Separate lint/test tooling from app runtime deps | Build image + run lint/test in dev env |
| Add static type-check gate | `pyproject.toml`/CI config (new mypy config) | Catches interface/contract drift early | Medium | Introduce mypy for core modules first, then expand | CI job with incremental strictness |

### Deep Refactors

| Item | File paths | Why it matters | Risk | Suggested approach | Validation |
|---|---|---|---|---|---|
| Decompose `RecipeManager` by aggregate responsibilities | `app/services/data/managers/recipe_manager.py` | Large multi-purpose class limits maintainability and reviewability | High | Split CRUD, composition fetches, and embeddings into focused managers/repositories | Snapshot integration tests for SQL behavior |
| Introduce resilient LLM gateway (timeouts/retries/circuit limits) | `app/services/llm_generation_service.py`, callers in `app/services/*` | External API instability currently bubbles unpredictably | High | Centralize retry/backoff/timeout policy and error envelopes | Unit tests with mocked transient/permanent failures |
| Separate asynchronous/background pipeline from request path | `app/api/v1/endpoints/recipes.py`, `app/services/recipe_processing_service.py` | Long synchronous request path (cleanup + extraction + embedding + DB) limits throughput | High | Add task queue/async workflow while preserving endpoint contract via job status mode | Load test + contract tests |

## Readjusted Strategy (Single PR)

One consolidated PR will contain all audit-related code and code improvements, organized as one reviewable change set with clear commit groupings:

1. **Guardrails and tooling reliability**  
   Keep the existing lint + live/E2E testing approach, but make command paths/config loading reliable and portable.
2. **Code smell cleanup**  
   Reduce broad exception handling, remove noisy runtime stdout, and tighten error/logging consistency where behavior is unchanged.
3. **Code bloat reduction**  
   Target duplication and oversized modules (especially `RecipeManager`) with incremental mechanical refactors that preserve API and DB contracts.
4. **Live/E2E testing clarity improvements**  
   Keep live and end-to-end testing as the primary validation model; improve lane naming, docs, and preflight checks for required secrets.
5. **Validation and rollback safety**  
   Re-run lint + live-smoke + E2E (where secrets exist), and document exact rollback points by commit grouping.

User feedback incorporated:

- Primary testing model remains live smoke tests + end-to-end tests.
- Refactor priorities are code smell cleanup and code bloat reduction.
- Delivery model is one consolidated audit/improvement PR.

## Implementation Status (This Branch)

Implemented:

- Added `pytest.ini` with valid `[pytest]` format and strict markers.
- Replaced fragile local pre-commit entries with pinned `ruff-pre-commit` hooks.
- Updated `.github/workflows/lint.yml` and `.github/workflows/test.yml` to use direct Ruff/pytest commands.
- Updated `Makefile` to expose direct `lint` and `test` targets.
- Updated `README.md` local quality/test commands.
- Updated test runner utilities to use `sys.executable` and explicit pytest config.
- Fixed health endpoint DB context handling and switched timestamps to real UTC ISO-8601 strings.
- Removed direct stdout printing from LLM text-generation calls.
- Refactored `RecipeManager` to extract reusable SQL helpers and reduce duplication without changing API/DB contracts.
- Added E2E live-test environment preflight checks (skip locally when secrets are missing; fail in CI when missing).
- Added E2E health endpoint smoke contract tests.

Verification evidence collected during audit:

- `.venv/bin/ruff check .` passed.
- `.venv/bin/ruff format --check .` passed.
- `.venv/bin/pytest app/tests/unit -q` resulted in 3 skipped tests as expected in a no-secret local environment (live-test design).
- `.venv/bin/python -m pytest -c pytest.ini app/tests/e2e -q` now skips cleanly in no-secret local environments by design.
