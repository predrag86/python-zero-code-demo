# CI/CD

The pipeline runs on every push to `main` and every pull request.

```
lint ──┐
       ├──→ release (main only) ──→ docker: build → smoke test → Trivy → SBOM → push → sign
typecheck ─┤
test ──────┘
```

## Jobs

| Job | Tool | Runs on |
|---|---|---|
| `lint` | ruff (lint + format, auto-fix committed back) | all events |
| `typecheck` | mypy | all events |
| `test` | pytest | all events |
| `release` | python-semantic-release | push to `main` only |
| `docker` | multi-stage build, smoke test, Trivy, SBOM, Cosign, GHCR push | all events |

### Lint auto-fix

The `lint` job runs `ruff check --fix` and `ruff format`, then commits any changes
back to the branch automatically. For fork PRs the commit step is skipped (GitHub
restricts token permissions on forks).

### Docker job steps

1. **Build test stage** — runs ruff, mypy, and pytest inside the container
2. **Build runtime image** — loaded locally for smoke testing and scanning
3. **Smoke test** — starts the container, hits key endpoints with `curl`
4. **Trivy scan** — fails the build on unfixed `CRITICAL` or `HIGH` vulnerabilities
5. **Generate SBOM** — Trivy produces an SPDX JSON file, uploaded as a workflow artifact
6. **Push to GHCR** — only on `main`; re-uses the GHA layer cache so it is near-instant
7. **Cosign sign** — keyless signature stored in the registry alongside the image
8. **Cosign attest** — SBOM attached as a verifiable attestation to the image digest

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
