# CI/CD

Three GitHub Actions workflows run automatically.

## ci.yml

Runs on every push to `main` and every pull request.

```
build ──┬──→ lint ──┐
        │           ├──→ release (main, approval required) ──→ docker: build → smoke → Trivy → SARIF → push → sign
        └──→ test ──┘
dependency-review (PRs only)
```

### Jobs

| Job | Tool | Needs | Runs on |
|---|---|---|---|
| `build` | pip install (cached venv), pip-audit, import check | — | all events |
| `dependency-review` | actions/dependency-review-action | — | PRs only |
| `lint` | black → ruff (auto-fix) → pylint → bandit → mypy | `build` | all events |
| `test` | pytest matrix (Python 3.11, 3.12, 3.13) + Codecov | `build` | all events |
| `release` | python-semantic-release | `lint`, `test` | push to `main` only |
| `docker` | multi-stage build, smoke test, Trivy, SARIF, SBOM, Cosign, GHCR push | `lint`, `test`, `release` | all events |

### Build

1. Creates a `.venv` and installs `requirements.txt` + `requirements-dev.txt` into it.
2. Saves the venv to `actions/cache` under key `venv-{os}-py3.12-{hash(requirements files)}`.
3. Runs `pip check` (dependency consistency), `pip-audit` (CVE scan), and `python -c "import app"`.

Downstream jobs restore the cache and skip `pip install` entirely on a cache hit. The Python 3.12 `test` matrix entry always hits the same cache. Python 3.11 and 3.13 build their own caches on first run and hit on subsequent runs.

### Dependency Review (PRs only)

`actions/dependency-review-action` compares the dependency graph before and after the PR. Blocks merge if any newly introduced package has a known vulnerability.

### Lint

Restores the venv from cache, then runs in sequence:

1. **black** — enforces consistent formatting
2. **ruff check --fix** + **ruff format** — lints and formats; changes are committed back to the branch automatically (skipped for fork PRs)
3. **pylint** — static analysis
4. **bandit** — security-focused static analysis
5. **mypy** — type checking

### Test

Runs in parallel with `lint`. Matrix across **Python 3.11, 3.12, and 3.13** (`fail-fast: false`):

- Each matrix entry restores its own cached venv (key includes the Python version).
- `pytest --cov=app --cov-fail-under=80` — build fails if coverage drops below 80%.
- `pytest-github-actions-annotate-failures` is installed and auto-activates — failed tests appear as inline annotations on PR diffs.
- Coverage XML uploaded to **Codecov** from the 3.12 run only.

### Release

Protected by the **`production` GitHub Environment**. Before the job starts, GitHub pauses and waits for a required reviewer to approve. This gates both the version tag/release and (because `docker` depends on `release`) the GHCR push behind a human approval.

Configure reviewers at **Settings → Environments → production**.

Uses `python-semantic-release` with the Angular commit convention — see [Automatic versioning](#automatic-versioning) below.

### Docker

1. **Build test stage** — runs ruff, mypy, and pytest inside the container
2. **Build runtime image** — loaded locally for smoke testing and scanning
3. **Smoke test** — starts the container, hits key endpoints with `curl`
4. **Trivy scan (table)** — fails the build on unfixed `CRITICAL` or `HIGH` vulnerabilities
5. **Trivy SARIF upload** — sends findings to Security → Code scanning
6. **Generate SBOM** — Trivy produces an SPDX JSON file, uploaded as a workflow artifact (90-day retention)
7. **Push to GHCR** — only on `main`; re-uses GHA layer cache so it is near-instant
8. **Cosign sign** — keyless signature stored in the registry alongside the image
9. **Cosign attest** — SBOM attached as a verifiable attestation to the image digest

## codeql.yml

Runs on push to `main`, PRs, and weekly (Monday 08:00 UTC).

Performs source-level security analysis on `app.py` using the `security-and-quality`
query suite. Findings are uploaded to **Security → Code scanning** as SARIF.

Python does not require a build step for CodeQL — the action analyses the source directly.

## scorecard.yml

Runs on push to `main` and weekly (Monday 09:00 UTC).

Evaluates the repository against [OSSF Scorecard](https://securityscorecards.dev/)
best practices, including:

- Branch protection rules
- Required code review
- Dependency version pinning
- CI test coverage
- Signed releases

Results are uploaded to **Security → Code scanning** and published to the OpenSSF
REST API to power the public scorecard badge (`publish_results: true`).

## Automatic versioning

Versions are bumped automatically from commit messages using the
[Angular convention](https://www.conventionalcommits.org/):

| Commit prefix | Bump | Example |
|---|---|---|
| `fix:` | patch | `0.1.0 → 0.1.1` |
| `feat:` | minor | `0.1.0 → 0.2.0` |
| `feat!:` / `BREAKING CHANGE:` footer | major | `0.1.0 → 1.0.0` |

`chore:`, `docs:`, `style:` and similar prefixes do not trigger a release.

The version is stored in `pyproject.toml` under `[project] version` and tagged
as `v<version>` in git. Images are tagged `<version>`, `sha-<short-sha>`, and `latest`.

## Image registry

Images are published to:

```
ghcr.io/<owner>/python-zero-code-demo
```

| Tag | When |
|---|---|
| `1.2.3` | On a versioned release |
| `sha-abc1234` | Every push to `main` |
| `latest` | Every push to `main` |
