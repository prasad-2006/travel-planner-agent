"""
Unit tests for Travel Planner Agent
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


@pytest.fixture
def client():
    app = create_app("development")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert "Granite" in data["model"]


# ── Session ───────────────────────────────────────────────────────────────────

def test_create_session(client):
    r = client.post("/api/session", json={})
    assert r.status_code == 200
    data = r.get_json()
    assert "session_id" in data


def test_get_session(client):
    r1 = client.post("/api/session", json={})
    sid = r1.get_json()["session_id"]
    r2 = client.get(f"/api/session/{sid}")
    assert r2.status_code == 200


def test_get_session_404(client):
    r = client.get("/api/session/nonexistent-session-id")
    assert r.status_code == 404


# ── Destinations ──────────────────────────────────────────────────────────────

def test_suggest_destinations(client):
    r = client.post("/api/destinations/suggest", json={
        "interests": ["culture", "food"],
        "budget": 2000,
        "currency": "USD",
        "duration": 7,
        "travel_style": "balanced",
    })
    assert r.status_code == 200
    data = r.get_json()
    assert "suggestions" in data


# ── Itinerary ─────────────────────────────────────────────────────────────────

def test_build_itinerary(client):
    r = client.post("/api/itinerary/build", json={
        "destination": "Paris",
        "duration": 3,
        "daily_budget": 150,
        "currency": "USD",
    })
    assert r.status_code == 200
    data = r.get_json()
    assert "itinerary" in data
    assert data["destination"] == "Paris"


# ── Accommodation ─────────────────────────────────────────────────────────────

def test_recommend_accommodation(client):
    r = client.post("/api/accommodation/recommend", json={
        "destination": "Barcelona",
        "budget_per_night": 100,
        "currency": "USD",
        "travellers": 2,
    })
    assert r.status_code == 200
    assert "recommendations" in r.get_json()


# ── Transport ─────────────────────────────────────────────────────────────────

def test_recommend_transport(client):
    r = client.post("/api/transport/recommend", json={
        "origin": "New York",
        "destination": "Tokyo",
        "budget": 800,
        "currency": "USD",
    })
    assert r.status_code == 200
    assert "recommendations" in r.get_json()


# ── Budget ────────────────────────────────────────────────────────────────────

def test_calculate_budget(client):
    r = client.post("/api/budget/calculate", json={
        "destination": "Bali",
        "duration": 10,
        "total_budget": 3000,
        "currency": "USD",
        "travellers": 1,
    })
    assert r.status_code == 200
    assert "analysis" in r.get_json()


# ── Weather ───────────────────────────────────────────────────────────────────

def test_weather(client):
    r = client.get("/api/weather/London")
    assert r.status_code == 200
    data = r.get_json()
    assert "temperature" in data


def test_forecast(client):
    r = client.get("/api/weather/Tokyo/forecast?days=3")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


# ── Chat ──────────────────────────────────────────────────────────────────────

def test_chat(client):
    r = client.post("/api/chat", json={"message": "What are the best beaches in Europe?"})
    assert r.status_code == 200
    data = r.get_json()
    assert "response" in data
    assert "session_id" in data


def test_chat_empty_message(client):
    r = client.post("/api/chat", json={"message": ""})
    assert r.status_code == 400


# ── Alerts ────────────────────────────────────────────────────────────────────

def test_travel_alerts(client):
    r = client.get("/api/alerts/Japan")
    assert r.status_code == 200
    assert "alerts" in r.get_json()


# ── Currency ──────────────────────────────────────────────────────────────────

def test_currency_convert(client):
    r = client.get("/api/currency/convert?amount=100&from=USD&to=EUR")
    assert r.status_code == 200
    data = r.get_json()
    assert "converted" in data
    assert data["converted"] > 0
