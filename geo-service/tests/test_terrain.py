import asyncio
import json
import math

import httpx
import pytest

from app.climate.indicators import build_climate_profile
from app.config import Settings
from app.engine.engine import run
from app.schemas import AnalysisRequest
from app.terrain.client import TerrainClient, TerrainError
from app.terrain.slope import LS_REFERENCE, ls_factor, relief_class, sample_grid, summarize
from tests.synthetic import synthetic_series


def plane(n: int, dx: float, slope_pct: float) -> list[list[float]]:
    """Plano inclinado para o leste com a declividade dada."""
    return [[500.0 + slope_pct / 100 * dx * j for j in range(n)] for _ in range(n)]


def test_slope_of_tilted_plane_is_exact():
    s = summarize(plane(5, 50.0, 6.0), 50.0, 50.0)
    assert s["slope_pct"]["mean"] == pytest.approx(6.0, abs=0.05)
    assert s["relief_class"] == "suave ondulado"


def test_ls_factor_grows_with_slope_and_reference_is_one():
    assert ls_factor(1) < ls_factor(3) < ls_factor(8) < ls_factor(20)
    assert ls_factor(3) / LS_REFERENCE == pytest.approx(1.0)


def test_relief_classes_follow_embrapa():
    assert [relief_class(x) for x in (1, 5, 12, 30, 60, 90)] == [
        "plano", "suave ondulado", "ondulado", "forte ondulado", "montanhoso", "escarpado"]


def test_grid_covers_polygon_bbox():
    poly = {"type": "Polygon", "coordinates": [[[-48.2812, -18.9156], [-48.2732, -18.9156], [-48.2732, -18.9216],
                                                [-48.2812, -18.9216], [-48.2812, -18.9156]]]}
    g = sample_grid(-18.9186, -48.2772, poly)
    pts = [p for row in g["points"] for p in row]
    assert len(pts) == 25
    assert min(p[0] for p in pts) == pytest.approx(-18.9216, abs=1e-4)
    assert max(p[1] for p in pts) == pytest.approx(-48.2732, abs=1e-4)
    assert g["dx_m"] > 150  # ~840 m / 4


def _client(tmp_path, handler) -> TerrainClient:
    cfg = Settings(cache_dir=tmp_path, terrain_base_url="https://topo.test/v1/srtm30m")
    return TerrainClient(cfg, transport=httpx.MockTransport(handler))


def test_client_fetches_and_caches(tmp_path):
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        locs = req.url.params["locations"].split("|")
        lons = [float(l.split(",")[1]) for l in locs]
        lon0 = min(lons)
        m_per_deg = 111_320 * math.cos(math.radians(-18.9186))
        # 10 % de declividade para o leste
        return httpx.Response(200, json={"status": "OK", "results": [{"elevation": 800 + 0.10 * (lo - lon0) * m_per_deg} for lo in lons]})

    c = _client(tmp_path, handler)
    t = asyncio.run(c.fetch(-18.9186, -48.2772))
    assert t["dataset"] == "SRTM GL1" and t["citation"]
    assert t["slope_pct"]["mean"] == pytest.approx(10.0, abs=0.3)
    assert t["relief_class"] == "ondulado"
    asyncio.run(c.fetch(-18.9186, -48.2772))
    assert len(calls) == 1  # segunda chamada veio do cache


def test_client_reports_error(tmp_path):
    c = _client(tmp_path, lambda req: httpx.Response(400, json={"status": "INVALID_REQUEST"}))
    with pytest.raises(TerrainError):
        asyncio.run(c.fetch(-18.9, -48.3))


@pytest.fixture(scope="module")
def profile():
    return build_climate_profile(synthetic_series())


def _terrain(slope: float) -> dict:
    s = summarize(plane(5, 50.0, slope), 50.0, 50.0)
    return {"dataset": "SRTM GL1", "citation": "SRTM", **s}


def _erosion(out: dict) -> int:
    return next(c["score"] for c in out["strategies"][0]["criteria"] if c["key"] == "erosion_control")


def test_steeper_terrain_lowers_erosion_score_and_is_explained(profile):
    base = {"climate": profile, "field": {"latitude": -18.9, "longitude": -48.3},
            "history": [{"crop": "soja", "sown_at": "2024-10-20", "harvested_at": "2025-02-15"}]}
    flat = run(AnalysisRequest(**base, terrain=_terrain(1.0)))
    steep = run(AnalysisRequest(**base, terrain=_terrain(15.0)))
    none = run(AnalysisRequest(**base))

    assert _erosion(flat) > _erosion(none) > _erosion(steep)
    assert any(h["key"] == "slope" and h["datasets"] == ["SRTM"] for h in steep["diagnosis"]["highlights"])
    assert steep["diagnosis"]["terrain"]["relief_class"] == "ondulado"
    assert any(s["code"] == "SRTM" for s in steep["sources"])
    assert any("SRTM" in g for g in steep["strategies"][0]["information_gaps"])
    assert "SRTM" in json.dumps(steep["strategies"][0]["evidences"])


def test_very_steep_terrain_warns(profile):
    out = run(AnalysisRequest(climate=profile, field={"latitude": -18.9, "longitude": -48.3}, terrain=_terrain(25.0)))
    assert any("Relevo forte ondulado" in w for w in out["warnings"])
