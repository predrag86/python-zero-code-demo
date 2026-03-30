# inventory-service

A Python Flask service that demonstrates **OpenTelemetry zero-code instrumentation**.
`app.py` contains **no OpenTelemetry imports** — all traces, metrics, and logs are
injected at runtime by the `opentelemetry-instrument` CLI wrapper via environment variables.

## How zero-code instrumentation works

The `Dockerfile` runs two extra steps after installing application dependencies:

```dockerfile
# Installs the opentelemetry-instrument CLI
RUN pip install opentelemetry-distro opentelemetry-exporter-otlp

# Auto-discovers installed libraries and installs their instrumentors
RUN opentelemetry-bootstrap -a install
```

The container then starts with `opentelemetry-instrument` wrapping gunicorn:

```
opentelemetry-instrument gunicorn --bind 0.0.0.0:5000 --workers 1 app:app
```

All OTel configuration is provided through `OTEL_*` environment variables — no code changes required.

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
