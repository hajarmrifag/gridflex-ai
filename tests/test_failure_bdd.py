"""Inject solver outcomes at the SciPy boundary; keep API/engine orchestration real."""

import json
from threading import BoundedSemaphore

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from scipy.optimize import OptimizeResult

from api import main as api_main
from api import service
from src import optimizer

pytestmark = pytest.mark.bdd
scenarios("features/optimizer_recovery.feature")


@pytest.fixture
def compute_slots(monkeypatch):
    # A release regression must fail this scenario without exhausting the shared
    # application semaphore for every subsequent test in the process.
    slots = BoundedSemaphore(2)
    monkeypatch.setattr(api_main, "compute_slots", slots)
    return slots


@pytest.fixture
def client(compute_slots):
    with TestClient(api_main.app) as client:
        yield client


@given("a valid synthetic optimization request", target_fixture="request_body")
def request_body():
    # A previous successful request must not bypass the injected solver failure.
    service.optimized.cache_clear()
    yield {"profile": "synthetic", "days": 7}
    service.optimized.cache_clear()


@when(
    parsers.parse("the solver reports {failure} during the {stage} solve"),
    target_fixture="failed_response",
)
def fail_solver(client, request_body, monkeypatch, failure, stage):
    real_solve = optimizer.linprog
    calls = 0
    fail_at = {"peak": 1, "throughput": 2}[stage]

    def injected_solve(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == fail_at:
            return OptimizeResult(
                success=False,
                status={"time limit": 1, "infeasible": 2}[failure],
                message=f"INTERNAL_SOLVER_DETAIL: {failure}",
            )
        return real_solve(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(optimizer, "linprog", injected_solve)
        response = client.post("/api/optimize", json=request_body)
    assert calls == fail_at
    return response


@then("the API returns an actionable 422 without internal solver details")
def error_contract(failed_response):
    assert failed_response.status_code == 422
    assert set(failed_response.json()) == {"detail"}
    assert (
        "Try disabling terminal charge restoration or reducing the horizon"
        in failed_response.json()["detail"]
    )
    assert "INTERNAL_SOLVER_DETAIL" not in failed_response.text


@then("both compute slots remain available")
def capacity_restored(compute_slots):
    acquired = 0
    try:
        for _ in range(2):
            assert compute_slots.acquire(blocking=False), "Solver failure leaked a compute slot"
            acquired += 1
    finally:
        for _ in range(acquired):
            compute_slots.release()


@then("retrying the same request with the real solver succeeds")
def retry_succeeds(client, request_body):
    response = client.post("/api/optimize", json=request_body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["series"]["timestamps"]) == 168
    assert data["peak_mw"] >= 0
    json.dumps(data, allow_nan=False)
