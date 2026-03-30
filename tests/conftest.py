import logging

import pytest

# Override the OTel log format BEFORE importing app.
# otelTraceID / otelSpanID are only injected by opentelemetry-instrumentation-logging
# at runtime; they don't exist on plain LogRecord objects, causing KeyError in tests.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    force=True,
)

from app import app as flask_app  # noqa: E402


@pytest.fixture()
def app():
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()
