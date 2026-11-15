import asyncio
import json
from datetime import date, timedelta

import pytest

from app.climate.indicators import build_climate_profile
from app.config import Settings
from app.earthdata.client import EarthdataClient, EarthdataError, ease2_rowcol, friendly
from app.earthdata.indicators import summarize_ecostress, summarize_gpm, summarize_grace, summarize_smap
from app.engine.engine import run
from app.schemas import AnalysisRequest
from tests.synthetic import synthetic_series

TODAY = date(2026, 11, 1)
SM = {1: 0.30, 2: 0.31, 3: 0.28, 4: 0.24, 5: 0.18, 6: 0.14, 7: 0.11, 8: 0.10, 9: 0.12, 10: 0.20, 11: 0.26, 12: 0.29}


def smap_obs():
    out, d = [], TODAY - timedelta(days=730)
    while d <= TODAY:
        out.append({"date": d.isoformat(), "sm": SM[d.month]})
        d += timedelta(days=5)
    return out


def test_ease2_grid_matches_proj():
    assert ease2_rowcol(-18.9, -48.55) == (1074, 1407)  # conferido com PROJ (EPSG:6933)


def test_smap_summary_flags_driest_months_relative_to_the_soil():
    s = summarize_smap(smap_obs(), TODAY)
    assert s["dry_months"] == [6, 7, 8, 9]
    assert s["driest"] == "ago" and s["wettest"] == "fev"


def test_gpm_summary_and_power_comparison():
    obs = [{"month": f"{y}-{m:02d}", "mm": 100.0} for y in range(2016, 2026) for m in range(1, 13)]
    s = summarize_gpm(obs, {m: 110.0 for m in range(1, 13)})
    assert s["annual_mm"] == 1200 and s["vs_power_pct"] == -9
    assert len(s["yearly"]) == 10
    with pytest.raises(ValueError):
        summarize_gpm(obs[:10])


def test_ecostress_summary():
    obs = [{"datetime": f"2026-0{m}-10T15:00", "esi": v} for m, v in [(1, 0.8), (3, 0.5), (5, 0.25), (7, 0.2), (9, None)]]
    s = summarize_ecostress(obs)
    assert s["median_esi"] == pytest.approx(0.375) and s["stress"] == "moderado"
    assert s["high_stress_pct"] == 50 and s["latest"]["esi"] == 0.2


def test_grace_summary_detects_drying_trend():
    obs, d = [], date(2004, 1, 16)
    while d.year < 2026:
        obs.append({"date": d.isoformat(), "cm": 10 - 2.0 * (d.year - 2004)})
        d = (d.replace(day=1) + timedelta(days=32)).replace(day=16)
    s = summarize_grace(obs)
    assert s["trend_cm_per_decade"] == pytest.approx(-20.0)
    assert s["trend_p_value"] < 0.01


def test_client_requires_token(tmp_path):
    with pytest.raises(EarthdataError):
        asyncio.run(EarthdataClient(Settings(cache_dir=tmp_path, earthdata_token="")).fetch(-18.9, -48.55))


def test_friendly_eula_message():
    assert "Authorized Apps" in friendly(EarthdataError('{"error_description":"EULA Acceptance Failure"}'))


@pytest.fixture(scope="module")
def profile():
    return build_climate_profile(synthetic_series())


def test_engine_uses_earthdata(profile):
    gpm_obs = [{"month": f"{y}-{m:02d}", "mm": 100.0} for y in range(2016, 2026) for m in range(1, 13)]
    grace_obs = [{"date": f"{y}-{m:02d}-16", "cm": 5 - 1.5 * (y - 2004)} for y in range(2004, 2026) for m in range(1, 13)]
    ed = {
        "smap": {"citation": "SMAP", **summarize_smap(smap_obs(), TODAY)},
        "gpm": {"citation": "GPM", **summarize_gpm(gpm_obs)},
        "ecostress": {"citation": "ECO", **summarize_ecostress([{"datetime": "2026-07-01T15:00", "esi": 0.2}] * 4)},
        "grace": {"citation": "GRACE", **summarize_grace(grace_obs)},
        "notes": [],
    }
    out = run(AnalysisRequest(climate=profile, field={"latitude": -18.9, "longitude": -48.3}, earthdata=ed))
    d = out["diagnosis"]
    assert {"smap", "gpm", "ecostress", "grace"} <= {h["key"] for h in d["highlights"]}
    assert [c["soil_dry"] for c in d["calendar"]][6:9] == [2, 2, 2]
    assert d["earthdata"]["gpm"]["vs_power_pct"] is not None
    assert {"SMAP", "GPM", "ECOSTRESS", "GRACE-FO"} <= {s["code"] for s in out["sources"]}
    ev = json.dumps(out["strategies"][0]["evidences"])
    assert "ECOSTRESS" in ev and "GRACE-FO" in ev
    assert "Aquíferos" in next(h["text"] for h in d["highlights"] if h["key"] == "grace")


def test_engine_without_earthdata_declares_gap(profile):
    out = run(AnalysisRequest(climate=profile, field={"latitude": -18.9, "longitude": -48.3}))
    assert any("NASA Earthdata" in g for g in out["strategies"][0]["information_gaps"])
