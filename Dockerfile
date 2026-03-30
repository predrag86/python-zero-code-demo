# ── Stage 1: shared venv base ──────────────────────────────────────────────
FROM python:3.12-slim AS base
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN python -m venv $VIRTUAL_ENV

# ── Stage 2: runtime dependencies ──────────────────────────────────────────
# Installing into a venv lets us copy just the venv to the runtime stage,
# leaving pip and the rest of the system Python out of the final image.
FROM base AS deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    opentelemetry-bootstrap -a install

# ── Stage 3: test gate (CI only — not a parent of the runtime stage) ───────
# Built explicitly with --target test. Running `docker build .` skips this.
FROM deps AS test
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY pyproject.toml .
COPY app.py .
COPY tests/ tests/
RUN ruff check . && \
    ruff format --check . && \
    mypy app.py && \
    pytest --tb=short -q

# ── Stage 4: lean runtime image ────────────────────────────────────────────
# Copies only the pre-built venv from the deps stage — no pip, no dev tools,
# no test code. The base image is a fresh python:3.12-slim (no venv leftovers).
FROM python:3.12-slim AS runtime
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

RUN adduser --disabled-password --no-create-home --uid 1001 appuser

COPY --from=deps --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser app.py .

USER appuser
EXPOSE 5000

CMD ["opentelemetry-instrument", \
     "gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "1", \
     "--access-logfile", "-", \
     "app:app"]
