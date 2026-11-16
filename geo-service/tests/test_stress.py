import asyncio
import json
from datetime import date, timedelta

import httpx
import pytest

from app.climate.indicators import build_climate_profile
from app.config import Settings
from app.engine.engine import run
from app.schemas import AnalysisRequest
from app.stress.client import StressClient, StressError
from app.stress.indicators import lst_c, summarize_et, summarize_lst
from tests.synthetic import synthetic_series

TODAY = date(2026, 11, 1)
# Superfície quente na seca (ago–out), amena no verão chuvoso.
SURFACE_C = {1: 28, 2: 27, 3: 27, 4: 28, 5: 29, 6: 30, 7: 33, 8: 41, 9: 44, 10: 38, 11: 31, 12: 28}


def k_raw(c: float) -> int:
    return round((c + 273.15) / 0.02)


def lst_obs(years: int = 3) -> list[dict]:
    obs, d = [], date(TODAY.year - years, 1, 5)
    while d <= TODAY:
        obs.append({"date": d.isoformat(), "lst_raw": k_raw(SURFACE_C[d.month]), "qc": 0})
        d += timedelta(days=8)
    return obs


def test_lst_conversion_and_quality():
    assert lst_c(k_raw(30), 0) == pytest.approx(30, abs=0.05)
    assert lst_c(k_raw(30), 2) is None  # sem LST produzida
    assert lst_c(None, 0) is None


def test_lst_summary_flags_hot_dry_season():
    s = summarize_lst(lst_obs(), TODAY)
    assert s["hot_months"] == [8, 9, 10]
    assert s["hottest"]["month"] == 9
    assert [m["level"] for m in s["monthly"]][7:10] == [2, 2, 1]


def test_et_summary_ratio_and_fill_values():
    s = summarize_et([
        {"year": 2023, "et_raw": 7000, "pet_raw": 20000},
        {"year": 2024, "et_raw": 5000, "pet_raw": 25000},
        {"year": 2025, "et_raw": 32767, "pet_raw": 32767},  # preenchimento
    ])
    assert [y["year"] for y in s["yearly"]] == [2023, 2024]
    assert s["et_mm"] == 600 and s["pet_mm"] == 2250
    assert s["stress"] == "moderado" and s["driest_year"]["year"] == 2024
    with pytest.raises(ValueError):
        summarize_et([{"year": 2025, "et_raw": 32767, "pet_raw": 32767}])


def _client(tmp_path, handler) -> StressClient:
    cfg = Settings(cache_dir=tmp_path, pc_stac_url="https://stac.test", pc_data_url="https://data.test", lst_years=3, et_years=5)
    return StressClient(cfg, transport=httpx.MockTransport(handler))


def test_client_returns_lst_and_et(tmp_path):
    lst = lst_obs()
    lst_feats = [{"id": f"MOD11A2.{i:04d}", "properties": {"platform": "terra", "start_datetime": f"{o['date']}T00:00:00Z",
                                                           "end_datetime": f"{o['date']}T23:59:59Z"}} for i, o in enumerate(lst)]
    by_id = {f["id"]: o for f, o in zip(lst_feats, lst)}
    et_feats = [{"id": f"MOD16A3GF.A{y}", "properties": {"platform": "terra", "start_datetime": f"{y}-01-01T00:00:00Z",
                                                         "end_datetime": f"{y}-12-31T23:59:59Z"}} for y in range(2021, 2026)]

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.host == "stac.test":
            col = json.loads(req.content)["collections"][0]
            return httpx.Response(200, json={"features": lst_feats if col.startswith("modis-11") else et_feats, "links": []})
        item = req.url.params["item"]
        if item.startswith("MOD16"):
            return httpx.Response(200, json={"values": [6500, 23000]})
        return httpx.Response(200, json={"values": [by_id[item]["lst_raw"], 0]})

    out = asyncio.run(_client(tmp_path, handler).fetch(-18.9, -48.55, TODAY))
    assert out["lst"]["hot_months"] == [8, 9, 10]
    assert out["et"]["et_mm"] == 650 and len(out["et"]["yearly"]) == 5
    assert out["notes"] == []


def test_client_fails_only_when_both_fail(tmp_path):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"features": [], "links": []}) if req.url.host == "stac.test" else httpx.Response(404)

    with pytest.raises(StressError):
        asyncio.run(_client(tmp_path, handler).fetch(-18.9, -48.55, TODAY))


@pytest.fixture(scope="module")
def profile():
    return build_climate_profile(synthetic_series())


def test_engine_uses_stress_in_diagnosis_calendar_and_evidence(profile):
    stress = {
        "lst": {"citation": "LST", **summarize_lst(lst_obs(), TODAY)},
        "et": {"citation": "ET", **summarize_et([{"year": y, "et_raw": 6000, "pet_raw": 24000} for y in range(2021, 2026)])},
    }
    out = run(AnalysisRequest(climate=profile, field={"latitude": -18.9, "longitude": -48.3}, stress=stress,
                              history=[{"crop": "soja", "sown_at": "2025-10-20", "harvested_at": "2026-02-15"}]))
    d = out["diagnosis"]
    keys = {h["key"] for h in d["highlights"]}
    assert {"lst", "et_ratio"} <= keys
    assert [c["hot_surface"] for c in d["calendar"]][7:9] == [2, 2]
    assert {"MODIS LST", "MODIS ET"} <= {s["code"] for s in out["sources"]}
    assert "MODIS ET" in json.dumps(out["strategies"][0]["evidences"])


def test_engine_without_stress_reports_gap(profile):
    out = run(AnalysisRequest(climate=profile, field={"latitude": -18.9, "longitude": -48.3}))
    assert "hot_surface" not in out["diagnosis"]["calendar"][0]
    assert any("MODIS LST e ET) indisponível" in g for g in out["strategies"][0]["information_gaps"])
