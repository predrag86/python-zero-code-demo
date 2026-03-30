import random

import pytest


def test_health(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "inventory-service"


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_list_items(client):
    resp = client.get("/items")
    assert resp.status_code == 200
    items = resp.get_json()
    assert isinstance(items, list)
    assert len(items) > 0


def test_get_item_found(client):
    resp = client.get("/items/1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == 1
    assert "name" in data and "quantity" in data


def test_get_item_not_found(client):
    resp = client.get("/items/9999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_create_item_missing_name(client):
    resp = client.post("/items", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_create_item_success(client, monkeypatch):
    # Force random.random() > 0.20 so the simulated failure never fires
    monkeypatch.setattr(random, "random", lambda: 0.5)
    resp = client.post("/items", json={"name": "Test Widget", "quantity": 5})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Test Widget"
    assert data["quantity"] == 5


def test_create_item_simulated_failure(client, monkeypatch):
    # Force random.random() < 0.20 to trigger the downstream write failure
    monkeypatch.setattr(random, "random", lambda: 0.1)
    with pytest.raises(RuntimeError, match="Downstream write failure"):
        client.post("/items", json={"name": "Bad Widget", "quantity": 1})


def test_process_endpoint(client):
    resp = client.get("/process")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "n" in data
    assert "result" in data
    assert "elapsed_ms" in data
    assert 30 <= data["n"] <= 35
