# API Reference

The service listens on port `5000`.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Service info — returns name, version, status |
| `GET` | `/healthz` | Health check — used by Docker `HEALTHCHECK` and load balancers |
| `GET` | `/items` | List all items (0–150 ms simulated latency) |
| `GET` | `/items/<id>` | Get a single item (0–300 ms, 404 for id > 1000) |
| `POST` | `/items` | Create an item (~20% error rate to demo error spans) |
| `GET` | `/process` | CPU-bound Fibonacci — demonstrates non-I/O latency |
| `GET` | `/chain` | Calls `/items` on itself — shows W3C trace context propagation |
| `GET` | `/burst` | Calls `/items` 5× — useful for metrics rate graphs |

## Examples

**Health check**
```bash
curl http://localhost:5000/healthz
# {"status": "ok"}
```

**List items**
```bash
curl http://localhost:5000/items
# [{"id": 1, "name": "Widget A", "quantity": 100}, ...]
```

**Get single item**
```bash
curl http://localhost:5000/items/1
# {"id": 1, "name": "Widget A", "quantity": 100}

curl http://localhost:5000/items/9999
# 404 — {"error": "Item 9999 not found"}
```

**Create item**
```bash
curl -X POST http://localhost:5000/items \
  -H 'Content-Type: application/json' \
  -d '{"name": "Widget D", "quantity": 25}'
# 201 — {"id": 4, "name": "Widget D", "quantity": 25}
# ~20% chance of 500 to demonstrate error spans
```

**Distributed trace (chain)**
```bash
curl http://localhost:5000/chain
# {"chained": true, "item_count": 3}
# Produces a parent-child span in Jaeger / your tracing backend
```
