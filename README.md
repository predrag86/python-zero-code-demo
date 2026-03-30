# python-zero-code-demo

Demonstrates **OpenTelemetry zero-code instrumentation** for a Python Flask service.
`app.py` contains **no OpenTelemetry imports** — all traces, metrics, and logs are
injected at runtime by the `opentelemetry-instrument` CLI wrapper via environment variables.

## How zero-code instrumentation works

The `Dockerfile` runs two extra steps after `pip install`:

```dockerfile
# Installs opentelemetry-instrument CLI
RUN pip install opentelemetry-distro opentelemetry-exporter-otlp

# Auto-discovers installed libraries and installs their instrumentors
RUN opentelemetry-bootstrap -a install
```

The container starts with:
```
opentelemetry-instrument gunicorn --bind 0.0.0.0:5000 --workers 1 app:app
```

All OTel configuration is via environment variables — no code changes required.

## Quick start

Set the OTel gateway endpoint and start the app:

```bash
OTEL_GATEWAY_ENDPOINT=http://<your-gateway>:4318 docker compose up --build
```

If `OTEL_GATEWAY_ENDPOINT` is not set it defaults to `http://localhost:4318`.

## Key environment variables

| Variable | Default | Purpose |
|---|---|---|
| `OTEL_SERVICE_NAME` | `inventory-service` | Service identity in all signals |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `$OTEL_GATEWAY_ENDPOINT` | OTel gateway address |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` | Transport format |
| `OTEL_TRACES_EXPORTER` | `otlp` | Enable trace export |
| `OTEL_METRICS_EXPORTER` | `otlp` | Enable metrics export |
| `OTEL_LOGS_EXPORTER` | `otlp` | Enable log export |
| `OTEL_PYTHON_LOG_CORRELATION` | `true` | Inject `trace_id`/`span_id` into log records |
| `OTEL_METRIC_EXPORT_INTERVAL` | `5000` | Export metrics every 5 s |
| `OTEL_TRACES_SAMPLER` | `always_on` | Sample 100% of traces |

## Deploying to AWS ECS (Fargate)

### 1. Build and push to ECR, register the task definition

```bash
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=eu-west-1
export OTEL_GATEWAY_HOST=otel-gateway.internal   # hostname reachable from ECS tasks

./deploy.sh
```

`deploy.sh` does three things:
1. Builds the image for `linux/amd64` and pushes it to ECR
2. Substitutes `<ACCOUNT_ID>`, `<REGION>`, and `<OTEL_GATEWAY_HOST>` in `ecs-task-definition.json`
3. Registers a new task definition revision via the AWS CLI

### 2. Deploy the task definition to your service

```bash
aws ecs update-service \
  --cluster <your-cluster> \
  --service <your-service> \
  --task-definition inventory-service \
  --region "${AWS_REGION}"
```

### Prerequisites

- `ecsTaskExecutionRole` — standard ECS execution role with `AmazonECSTaskExecutionRolePolicy`
- `ecsTaskRole` — can be empty for this app (no AWS API calls)
- The OTel gateway (`OTEL_GATEWAY_HOST`) must be reachable on port `4318` from the ECS task's VPC/security group
- Tasks run in `awsvpc` network mode; the security group must allow outbound TCP to the gateway

---

## Local development

```bash
OTEL_GATEWAY_ENDPOINT=http://<your-gateway>:4318 docker compose up --build
```

---

## Generate traffic

```bash
while true; do
  curl -s http://localhost:5000/items > /dev/null
  curl -s http://localhost:5000/items/1 > /dev/null
  curl -s http://localhost:5000/items/9999 > /dev/null   # 404
  curl -s -X POST http://localhost:5000/items \
    -H 'Content-Type: application/json' \
    -d '{"name":"widget","quantity":10}' > /dev/null     # ~20% error rate
  curl -s http://localhost:5000/chain > /dev/null         # distributed trace
  curl -s http://localhost:5000/process > /dev/null       # CPU-bound work
  sleep 0.5
done
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/items` | List all items (0–150 ms simulated latency) |
| GET | `/items/<id>` | Get single item (0–300 ms, 404 for id > 1000) |
| POST | `/items` | Create item (~20% error rate to demo error spans) |
| GET | `/process` | CPU-bound Fibonacci (demonstrates non-I/O latency) |
| GET | `/chain` | Calls `/items` on itself — shows W3C trace context propagation |
| GET | `/burst` | Calls `/items` 5× — useful for metrics rate graphs |
