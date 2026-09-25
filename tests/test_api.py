import json

import pytest
from fastapi.testclient import TestClient

from api import service
from api.main import app, compute_slots
from api.models import Profile, ScenarioRequest

client = TestClient(app)


def test_simulation_is_reproducible_and_returns_provenance():
    first = client.post("/api/simulate", json={"profile": "synthetic", "days": 7})
    assert first.status_code == 200
    data = first.json()
    assert data == client.post("/api/simulate", json={"profile": "synthetic", "days": 7}).json()
    assert data["settings"]["profile"] == "synthetic"
    assert len(data["series"]["timestamps"]) == 168
    assert data["engine_version"] == "0.2.0"
    assert "Server-Timing" in first.headers
    assert first.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.parametrize(
    "body",
    [
        {"days": 365},
        {"profile": "../../etc/passwd"},
        {"duration_h": -1},
        {"power_pct": 10000},
        {"unrecognized": 1},
        {"penetration_pct": "NaN"},
    ],
)
def test_api_rejects_invalid_or_unbounded_requests(body):
    assert client.post("/api/simulate", json=body).status_code == 422


def test_api_bounds_body_size():
    response = client.post("/api/simulate", content="x" * 17000, headers={"Content-Type": "application/json"})
    assert response.status_code == 413


def test_compute_saturation_is_explicit_and_recovers():
    compute_slots.acquire()
    compute_slots.acquire()
    try:
        response = client.post("/api/simulate", json={})
        assert response.status_code == 503
        assert response.headers["Retry-After"] == "2"
    finally:
        compute_slots.release()
        compute_slots.release()
    assert client.post("/api/simulate", json={"days": 7}).status_code == 200


def test_all_labs_return_finite_serializable_outputs():
    for endpoint in ["compare", "forecast", "stress", "optimize"]:
        response = client.post(f"/api/{endpoint}", json={"profile": "synthetic", "days": 14})
        assert response.status_code == 200, response.text
        json.dumps(response.json(), allow_nan=False)


def test_short_forecast_and_infeasible_optimization_return_clear_errors():
    response = client.post("/api/forecast", json={"days": 7})
    assert response.status_code == 422
    assert "9 days" in response.json()["detail"]


def test_cached_input_is_not_mutated_by_services():
    before = service.profile_data(Profile.synthetic, 7).copy(deep=True)
    service.simulation(ScenarioRequest(profile="synthetic", days=7))
    assert service.profile_data(Profile.synthetic, 7).equals(before)


def test_german_missing_day_is_disclosed_only_when_in_horizon():
    short = client.post("/api/simulate", json={"profile": "germany", "days": 30}).json()
    long = client.post("/api/simulate", json={"profile": "germany", "days": 60}).json()
    assert short["data_quality"]["imputed_hours"] == 0
    assert long["data_quality"]["imputed_hours"] == 24
    assert len(long["series"]["timestamps"]) == 1440
