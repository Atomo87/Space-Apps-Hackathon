import asyncio
import json
from datetime import date, timedelta

import httpx
import pytest

from app.climate.indicators import build_climate_profile
from app.config import Settings
from app.engine.engine import run
from app.schemas import AnalysisRequest
from app.vegetation.client import NdviClient, VegetationError, hls_ndvi
from app.vegetation.ndvi import green_level, summarize
from tests.synthetic import synthetic_series

TODAY = date(2026, 11, 1)
# Soja de out a fev (verde), entressafra seca de jun a set (pouco verde).
SEASONAL = {1: 0.80, 2: 0.75, 3: 0.55, 4: 0.45, 5: 0.38, 6: 0.28, 7: 0.22, 8: 0.20, 9: 0.24, 10: 0.40, 11: 0.65, 12: 0.78}


def seasonal_obs(years: int = 5, cloudy_every: int = 7) -> list[dict]:
    obs, d, i = [], date(TODAY.year - years, 1, 8), 0
    while d <= TODAY:
        rel = 3 if i % cloudy_every == 0 else 0
        obs.append({"date": d.isoformat(), "ndvi_raw": int(SEASONAL[d.month] * 10000), "reliability": rel})
        d += timedelta(days=16)
        i += 1
    return obs


def test_summary_finds_low_green_months_and_skips_clouds():
    s = summarize(seasonal_obs(), TODAY)
    assert s["low_green_months"] == [5, 6, 7, 8, 9]
    assert s["peak"]["month"] == 1 and s["trough"]["month"] == 8
    assert s["coverage"]["valid"] < s["coverage"]["observations"]  # nuvens descartadas
    assert all(p["ndvi"] != pytest.approx(0) for p in s["series"])
    assert s["recent"]["below_p10"] is False


def test_recent_drop_is_flagged():
    obs = seasonal_obs()
    for o in obs[-3:]:
        o["ndvi_raw"] = 1500
    assert summarize(obs, TODAY)["recent"]["below_p10"] is True


def test_green_levels_and_too_few_points():
    assert [green_level(x) for x in (0.2, 0.35, 0.6, None)] == [2, 1, 0, 0]
    with pytest.raises(ValueError):
        summarize(seasonal_obs()[:5], TODAY)


def _client(tmp_path, handler) -> NdviClient:
    cfg = Settings(cache_dir=tmp_path, pc_stac_url="https://stac.test", pc_data_url="https://data.test", ndvi_years=5, hls_years=0)
    return NdviClient(cfg, transport=httpx.MockTransport(handler))


def _stac_feature(o: dict, n: int) -> dict:
    d = date.fromisoformat(o["date"])
    return {"id": f"MOD13Q1.{n:04d}", "properties": {"platform": "terra", "start_datetime": f"{(d - timedelta(days=7)).isoformat()}T00:00:00Z",
                                                     "end_datetime": f"{(d + timedelta(days=8)).isoformat()}T23:59:59Z"}}


def test_client_searches_queries_and_caches(tmp_path):
    obs = seasonal_obs(cloudy_every=1000)
    feats = [_stac_feature(o, i) for i, o in enumerate(obs)]
    by_id = {f["id"]: o for f, o in zip(feats, obs)}
    calls = {"stac": 0, "point": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "stac.test":
            calls["stac"] += 1
            return httpx.Response(200, json={"features": feats, "links": []})
        calls["point"] += 1
        o = by_id[req.url.params["item"]]
        return httpx.Response(200, json={"values": [o["ndvi_raw"], 0]})

    c = _client(tmp_path, handler)
    v = asyncio.run(c.fetch(-18.9186, -48.2772, TODAY))
    assert v["citation"] and v["resolution_m"] == 250
    assert v["low_green_months"] == [5, 6, 7, 8, 9]
    first = calls["point"]
    asyncio.run(c.fetch(-18.9186, -48.2772, TODAY))
    assert calls["point"] == first  # segunda vez: tudo do cache


def test_client_fails_when_most_points_fail(tmp_path):
    obs = seasonal_obs()
    feats = [_stac_feature(o, i) for i, o in enumerate(obs)]

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "stac.test":
            return httpx.Response(200, json={"features": feats, "links": []})
        return httpx.Response(404, json={"detail": "not found"})

    with pytest.raises(VegetationError):
        asyncio.run(_client(tmp_path, handler).fetch(-18.9, -48.3, TODAY))


@pytest.fixture(scope="module")
def profile():
    return build_climate_profile(synthetic_series())


def test_engine_uses_ndvi_in_diagnosis_evidence_and_sources(profile):
    veg = {"citation": "MODIS", **summarize(seasonal_obs(), TODAY)}
    out = run(AnalysisRequest(climate=profile, field={"latitude": -18.9, "longitude": -48.3}, vegetation=veg,
                              history=[{"crop": "soja", "sown_at": "2025-10-20", "harvested_at": "2026-02-15"}]))
    d = out["diagnosis"]
    assert any(h["key"] == "ndvi_low" and h["datasets"] == ["MODIS"] for h in d["highlights"])
    assert [c["low_green"] for c in d["calendar"]][4:10] == [1, 2, 2, 2, 2, 0]
    assert any(s["code"] == "MODIS" for s in out["sources"])
    assert "MODIS" in json.dumps(out["strategies"][0]["evidences"])
    assert any("250 m" in g for g in out["strategies"][0]["information_gaps"])


def test_hls_ndvi_masks_clouds_and_computes_index():
    assert hls_ndvi(1000, 3000, 64) == 5000  # limpo (só bit de aerossol)
    assert hls_ndvi(1000, 3000, 2) is None  # nuvem
    assert hls_ndvi(1000, 3000, 8) is None  # sombra
    assert hls_ndvi(None, 3000, 0) is None


def test_engine_prefers_hls_when_it_covers_the_year(profile):
    modis = summarize(seasonal_obs(), TODAY)
    hls_obs = [dict(o, ndvi_raw=int(0.85 * 10000), reliability=0) for o in seasonal_obs(2, cloudy_every=1000)]
    veg = {"citation": "MODIS", **modis, "hls": {"citation": "HLS", **summarize(hls_obs, TODAY)}}
    out = run(AnalysisRequest(climate=profile, field={"latitude": -18.9, "longitude": -48.3}, vegetation=veg))
    h = next(x for x in out["diagnosis"]["highlights"] if x["key"] == "ndvi_low")
    assert h["datasets"] == ["HLS"] and "o ano todo" in h["text"]
    assert all(c["low_green"] == 0 for c in out["diagnosis"]["calendar"])
    assert any(s["code"] == "HLS" for s in out["sources"])


def test_engine_without_ndvi_reports_gap(profile):
    out = run(AnalysisRequest(climate=profile, field={"latitude": -18.9, "longitude": -48.3}))
    assert "low_green" not in out["diagnosis"]["calendar"][0]
    assert any("NDVI MODIS) indisponível" in g for g in out["strategies"][0]["information_gaps"])
