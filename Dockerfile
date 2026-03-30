FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Step 1: install app deps + OTel core
RUN pip install --no-cache-dir -r requirements.txt

# Step 2: auto-discover and install instrumentors for all installed libraries.
# This is the idiomatic zero-code setup — no manual imports needed in app.py.
RUN opentelemetry-bootstrap -a install

COPY app.py .

EXPOSE 5000

# Zero-code entry point: opentelemetry-instrument wraps gunicorn.
# All OTel configuration is provided via OTEL_* env vars in docker-compose.yml.
CMD ["opentelemetry-instrument", \
     "gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "1", \
     "--access-logfile", "-", \
     "app:app"]
