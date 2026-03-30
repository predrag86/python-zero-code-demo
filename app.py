"""
Inventory Service — zero-code OpenTelemetry demo.

This file contains NO opentelemetry imports.
All instrumentation is injected at runtime by the
`opentelemetry-instrument` CLI wrapper via env vars.
"""

import logging
import os
import random
import time
from flask import Flask, jsonify, request
import requests as http_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] "
           "[trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] %(message)s",
)
logger = logging.getLogger("inventory-service")

app = Flask(__name__)

# In-memory store — simple enough for a demo
_inventory: dict[int, dict] = {
    1: {"id": 1, "name": "Widget A", "quantity": 100},
    2: {"id": 2, "name": "Gadget B", "quantity": 50},
    3: {"id": 3, "name": "Doohickey C", "quantity": 200},
}
_next_id = 4


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    logger.info("Health check")
    return jsonify({"service": "inventory-service", "version": "1.0.0", "status": "ok"})


@app.get("/items")
def list_items():
    """Simulates a DB read with variable latency (0–150 ms)."""
    delay = random.uniform(0, 0.15)
    time.sleep(delay)
    logger.info("Listed %d items (latency=%.0fms)", len(_inventory), delay * 1000)
    return jsonify(list(_inventory.values()))


@app.get("/items/<int:item_id>")
def get_item(item_id: int):
    """Simulates a heavier per-item lookup (0–300 ms). Returns 404 for id > 1000."""
    delay = random.uniform(0, 0.3)
    time.sleep(delay)

    if item_id > 1000:
        logger.warning("Item %d not found", item_id)
        return jsonify({"error": f"Item {item_id} not found"}), 404

    item = _inventory.get(item_id)
    if item is None:
        logger.warning("Item %d not found", item_id)
        return jsonify({"error": f"Item {item_id} not found"}), 404

    logger.info("Fetched item %d (latency=%.0fms)", item_id, delay * 1000)
    return jsonify(item)


@app.post("/items")
def create_item():
    """Creates an item. Fails ~20% of the time to demonstrate error spans."""
    global _next_id

    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    quantity = body.get("quantity", 0)

    if not name:
        logger.warning("Create item rejected — missing name")
        return jsonify({"error": "name is required"}), 400

    # Simulated intermittent downstream write failure
    if random.random() < 0.20:
        logger.error("Simulated write failure creating item '%s'", name)
        raise RuntimeError(f"Downstream write failure for item '{name}'")

    item = {"id": _next_id, "name": name, "quantity": quantity}
    _inventory[_next_id] = item
    _next_id += 1
    logger.info("Created item %d: %s", item["id"], name)
    return jsonify(item), 201


@app.get("/process")
def process():
    """CPU-bound work: computes Fibonacci to demonstrate non-I/O latency."""
    n = random.randint(30, 35)
    start = time.perf_counter()
    result = _fib(n)
    elapsed = time.perf_counter() - start
    logger.info("Computed fib(%d)=%d in %.0fms", n, result, elapsed * 1000)
    return jsonify({"n": n, "result": result, "elapsed_ms": round(elapsed * 1000)})


@app.get("/chain")
def chain():
    """
    Calls /items on itself to demonstrate distributed trace context propagation.
    The outgoing request gets a W3C traceparent header injected automatically
    by opentelemetry-instrumentation-requests, and the receiving handler picks
    it up, so Jaeger shows a parent-child span relationship.
    """
    base = os.getenv("SELF_URL", "http://localhost:5000")
    logger.info("Chaining call to %s/items", base)
    resp = http_client.get(f"{base}/items", timeout=5)
    items = resp.json()
    logger.info("Chain received %d items", len(items))
    return jsonify({"chained": True, "item_count": len(items)})


@app.get("/burst")
def burst():
    """Calls /items five times to produce a traffic burst for metrics demos."""
    base = os.getenv("SELF_URL", "http://localhost:5000")
    results = []
    for _ in range(5):
        resp = http_client.get(f"{base}/items", timeout=5)
        results.append(resp.status_code)
    logger.info("Burst completed: %s", results)
    return jsonify({"burst": True, "statuses": results})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fib(n: int) -> int:
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
