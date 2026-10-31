"""Tests REST API FastAPI."""
from __future__ import annotations
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from foundationcalc.api import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "endpoints" in body
    assert body["name"]


def test_api_isolated_footing(client):
    r = client.post("/api/footings/isolated", json={
        "L_x": 2.5, "L_y": 2.5, "thickness": 0.6,
        "N": 1500.0,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert "pressures" in body
    assert body["pressures"]["q_max"] > 0


def test_api_cantilever_wall(client):
    r = client.post("/api/walls/cantilever", json={
        "H": 4.0, "base_width": 2.5, "stem_thickness": 0.4,
        "toe_width": 0.8, "heel_width": 1.3,
        "gamma_soil": 18.0, "phi_soil": 30.0, "surcharge_kPa": 10.0,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sliding_FS"] > 0
    assert body["overturning_FS"] > 0


def test_api_pile_axial(client):
    r = client.post("/api/piles/axial", json={
        "D": 0.6, "L": 15.0,
        "layers_qu_kPa": [50.0, 100.0, 150.0],
        "layers_thickness": [5.0, 5.0, 5.0],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["Q_allowable_kN"] > 0


def test_api_bearing(client):
    r = client.post("/api/bearing/multilayer", json={
        "L_x": 2.5, "L_y": 2.5, "depth": 1.0,
        "layers": [
            {"thickness": 2.0, "gamma": 18.0, "phi": 30.0},
            {"thickness": 10.0, "gamma": 19.0, "phi": 33.0},
        ],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["qu_kPa"] > 0
    assert body["qa_kPa"] > 0


def test_api_mononobe_okabe(client):
    r = client.post("/api/seismic/mononobe_okabe", json={
        "H": 5.0, "gamma": 18.0, "phi": 30.0, "kh": 0.15,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["K_AE"] > 0.33
    assert body["P_AE_kN_per_m"] > 0


def test_api_jobs_tasks_list(client):
    r = client.get("/jobs/tasks")
    assert r.status_code == 200
    tasks = r.json()["tasks"]
    assert "design_footing" in tasks
