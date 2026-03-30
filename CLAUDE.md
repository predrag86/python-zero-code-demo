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

## Architecture constraints

- **Do not add OpenTelemetry imports to `app.py`** — the entire point of the demo is zero-code instrumentation. The instrumentation packages in `requirements.txt` exist only for the `opentelemetry-instrument` CLI; `app.py` must remain import-free of OTel.
- The logging format in `app.py` uses `%(otelTraceID)s` and `%(otelSpanID)s` — these fields are injected by `opentelemetry-instrumentation-logging` at runtime (requires `OTEL_PYTHON_LOG_CORRELATION=true`).
- `/chain` and `/burst` use `SELF_URL` env var to call back to themselves; in Docker Compose this is `http://app:5000`.
