# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A demo of **OpenTelemetry zero-code instrumentation** for a Python Flask service. The key constraint: `app.py` contains **no OpenTelemetry imports**. All traces, metrics, and logs are injected at runtime by the `opentelemetry-instrument` CLI wrapper via environment variables.

## Running locally

```bash
OTEL_GATEWAY_ENDPOINT=http://<your-gateway>:4318 docker compose up --build
```

If `OTEL_GATEWAY_ENDPOINT` is unset it defaults to `http://localhost:4318`.

## How zero-code instrumentation works

The Dockerfile has two OTel-specific steps after `pip install -r requirements.txt`:

1. `opentelemetry-distro` + `opentelemetry-exporter-otlp` are installed as part of `requirements.txt`
2. `opentelemetry-bootstrap -a install` — auto-discovers installed libraries and installs their instrumentors
3. The container entrypoint wraps gunicorn: `opentelemetry-instrument gunicorn ... app:app`

All OTel config flows through `OTEL_*` environment variables set in `docker-compose.yml`.

## Deploying to AWS ECS (Fargate)

```bash
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=eu-west-1
export OTEL_GATEWAY_HOST=otel-gateway.internal

./deploy.sh
```

`deploy.sh` builds the image for `linux/amd64`, pushes to ECR, substitutes `<ACCOUNT_ID>`, `<REGION>`, and `<OTEL_GATEWAY_HOST>` in `ecs-task-definition.json`, then registers a new task definition revision.

After registration, deploy with:
```bash
aws ecs update-service --cluster <cluster> --service <service> --task-definition inventory-service --region $AWS_REGION
```

## CI/CD pipeline

Three workflows in `.github/workflows/`:

### ci.yml — runs on every push to `main` and every PR

| Job | Tool | Needs | Runs on |
|---|---|---|---|
| `build` | pip install (cached venv), pip-audit, import check | — | all events |
| `dependency-review` | `actions/dependency-review-action` | — | PRs only |
| `lint` | black → ruff (auto-fix) → pylint → bandit → mypy | `build` | all events |
| `test` | pytest matrix (Python 3.11, 3.12, 3.13) + Codecov | `build` | all events |
| `release` | `python-semantic-release` | `lint`, `test` | push to main only |
| `docker` | build → smoke test → Trivy → SARIF → SBOM → push | `lint`, `test`, `release` | all events (push to GHCR on main only) |

`lint` and `test` run in parallel after `build`. The virtualenv is built once in `build` and restored from `actions/cache` in `lint` and `test` — no redundant installs.

**Test matrix:** pytest runs against Python 3.11, 3.12, and 3.13 (`fail-fast: false`). `pytest-github-actions-annotate-failures` annotates PR diffs with failed test locations inline. Coverage uploaded to Codecov from the 3.12 run (80% minimum enforced).

**Release gate:** the `release` job is protected by the `production` GitHub Environment — a required reviewer must approve before the version is tagged and the image is pushed to GHCR. Configure at Settings → Environments → production.

**Security scanning:**
- `dependency-review` blocks PRs that introduce dependencies with known CVEs.
- Trivy scans the runtime image for unfixed CRITICAL/HIGH CVEs (fails the build) and uploads SARIF to Security → Code scanning.

### codeql.yml — push to main, PRs, weekly (Mon 08:00 UTC)

Source-level security analysis on `app.py` using the `security-and-quality` query suite. Findings go to Security → Code scanning.

### scorecard.yml — push to main, weekly (Mon 09:00 UTC)

OSSF Scorecard evaluation of repo security practices (branch protection, dependency pinning, signed releases, etc.). Results go to Security → Code scanning and power the public scorecard badge.

**Automatic versioning** uses [Angular commit convention](https://www.conventionalcommits.org/):
- `fix: ...` → patch bump (0.1.0 → 0.1.1)
- `feat: ...` → minor bump (0.1.0 → 0.2.0)
- `feat!:` or footer `BREAKING CHANGE:` → major bump

Version is stored in `pyproject.toml → [project] version` and tagged as `v<version>` in git. Images are pushed to `ghcr.io/<owner>/<repo>` tagged `<version>`, `sha-<sha>`, and `latest`.

## Docker image architecture

4-stage multi-stage build:
1. **`base`** — creates a virtualenv (`/app/.venv`)
2. **`deps`** — installs `requirements.txt` + runs `opentelemetry-bootstrap` into the venv
3. **`test`** (CI gate, not a parent of runtime) — installs `requirements-dev.txt`, runs ruff/mypy/pytest; built explicitly with `--target test`
4. **`runtime`** — fresh `python:3.12-slim`, copies only `/app/.venv` from `deps` + `app.py`; runs as non-root `appuser`

`docker build .` builds only `base → deps → runtime` (skips the test stage). The `.dockerignore` keeps `tests/`, `requirements-dev.txt`, and `pyproject.toml` in the build context so the test stage can use them.

## Dev tooling

```bash
pip install -r requirements.txt -r requirements-dev.txt

ruff check .          # lint
ruff format --check . # format check (ruff format . to auto-fix)
mypy app.py           # type check
pytest --tb=short -v  # run tests

docker build --target test .    # run full check suite inside Docker
docker build .                  # build optimised runtime image only
```

## Architecture constraints

- **Do not add OpenTelemetry imports to `app.py`** — the entire point of the demo is zero-code instrumentation. The instrumentation packages in `requirements.txt` exist only for the `opentelemetry-instrument` CLI; `app.py` must remain import-free of OTel.
- The logging format in `app.py` uses `%(otelTraceID)s` and `%(otelSpanID)s` — these fields are injected by `opentelemetry-instrumentation-logging` at runtime (requires `OTEL_PYTHON_LOG_CORRELATION=true`).
- `/chain` and `/burst` use `SELF_URL` env var to call back to themselves; in Docker Compose this is `http://app:5000`.
