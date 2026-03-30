# Getting Started

## Quick start

Set the OTel gateway endpoint and start the app:

```bash
OTEL_GATEWAY_ENDPOINT=http://<your-gateway>:4318 docker compose up --build
```

If `OTEL_GATEWAY_ENDPOINT` is not set it defaults to `http://localhost:4318`.

## Local development

Install dependencies and run the dev tooling directly:

```bash
pip install -r requirements.txt -r requirements-dev.txt

ruff check .              # lint
ruff format --check .     # format check  (ruff format . to auto-fix)
mypy app.py               # type check
pytest --tb=short -v      # run tests
```

Build the Docker image:

```bash
# Runtime image only
docker build .

# Run the full test gate inside Docker (ruff + mypy + pytest)
docker build --target test .
```

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
