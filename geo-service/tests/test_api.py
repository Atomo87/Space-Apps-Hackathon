from fastapi.testclient import TestClient

from app.climate.indicators import build_climate_profile
from app.main import app
from tests.synthetic import synthetic_series

client = TestClient(app)


def test_health_and_catalog():
    assert client.get("/health").json()["status"] == "ok"
    cat = client.get("/v1/catalog").json()
    assert {c["slug"] for c in cat["crops"]} >= {"soja", "milho", "crotalaria"}


def test_analysis_endpoint():
    profile = build_climate_profile(synthetic_series(2015, 2025))
    r = client.post("/v1/analysis", json={
        "climate": profile,
        "field": {"latitude": -18.9, "longitude": -48.3},
        "history": [{"crop": "soja", "sown_at": "2024-10-20", "harvested_at": "2025-02-15"}],
        "priorities": {"erosion_control": 5},
        "scenario": {"rain_delta_pct": -20, "temp_delta_c": 1},
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["disclaimer"] and body["strategies"] and body["diagnosis"]["calendar"]


def test_validation_errors():
    assert client.post("/v1/analysis", json={"climate": {}, "field": {"latitude": 0, "longitude": 0}}).status_code == 422
    r = client.post("/v1/analysis", json={"climate": {"monthly": [1]}, "field": {"latitude": 0, "longitude": 0},
                                          "history": [{"crop": "mandioca", "sown_at": "2025-01-01", "harvested_at": "2025-05-01"}]})
    assert r.status_code == 422
