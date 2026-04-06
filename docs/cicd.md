# CI/CD

The pipeline runs on every push to `main` and every pull request.

```
build ──┬──→ lint ──┐
        │           ├──→ release (main only) ──→ docker: build → smoke test → Trivy → SARIF → push → sign
        └──→ test ──┘
dependency-review (PRs only, parallel)
```

## Jobs

| Job | Tool | Needs | Runs on |
|---|---|---|---|
| `build` | pip install, pip-audit, import check | — | all events |
| `dependency-review` | actions/dependency-review-action | — | PRs only |
| `lint` | black → ruff (auto-fix) → pylint → bandit → mypy | `build` | all events |
| `test` | pytest (Python 3.11, 3.12, 3.13 matrix) + Codecov | `build` | all events |
| `release` | python-semantic-release | `lint`, `test` | push to `main` only |
| `docker` | multi-stage build, smoke test, Trivy, SARIF, SBOM, Cosign, GHCR push | `lint`, `test`, `release` | all events |

### Build

Installs all dependencies, runs `pip check` to verify consistency, runs `pip-audit`
to flag known CVEs in `requirements.txt`, and verifies `app.py` is importable.
Acts as the gate for `lint` and `test`.

### Dependency Review (PRs only)

Runs `actions/dependency-review-action` on every pull request. Blocks merge if any
newly introduced dependency has a known vulnerability. Runs independently of `build`
so it does not add to the critical path.

### Lint

Runs in parallel with `test` (both gate only on `build`):

1. **black** — enforces consistent formatting
2. **ruff check --fix** + **ruff format** — lints and formats; any changes are committed back to the branch automatically (skipped for fork PRs)
3. **pylint** — static analysis
4. **bandit** — security-focused static analysis
5. **mypy** — type checking

### Test

Runs in parallel with `lint`. Uses a matrix across **Python 3.11, 3.12, and 3.13**
(`fail-fast: false` so all three variants always complete):

- `pytest` with `--cov=app --cov-fail-under=80` — build fails if coverage drops below 80%
- Coverage XML uploaded to **Codecov** from the Python 3.12 run only (avoids triple uploads)

### Docker job steps

1. **Build test stage** — runs ruff, mypy, and pytest inside the container
2. **Build runtime image** — loaded locally for smoke testing and scanning
3. **Smoke test** — starts the container, hits key endpoints with `curl`
4. **Trivy scan (table)** — fails the build on unfixed `CRITICAL` or `HIGH` vulnerabilities
5. **Trivy SARIF upload** — sends findings to the repo's Security → Code scanning tab
6. **Generate SBOM** — Trivy produces an SPDX JSON file, uploaded as a workflow artifact (90-day retention)
7. **Push to GHCR** — only on `main`; re-uses the GHA layer cache so it is near-instant
8. **Cosign sign** — keyless signature stored in the registry alongside the image
9. **Cosign attest** — SBOM attached as a verifiable attestation to the image digest

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
