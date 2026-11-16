import pytest

from app.climate.indicators import build_climate_profile
from app.engine.engine import run
from app.engine.scenario import apply_scenario
from app.i18n import analysis_locale, localize_metadata
from app.schemas import AnalysisRequest
from tests.synthetic import synthetic_series

HISTORY = [
    {"crop": "soja", "sown_at": "2024-10-20", "harvested_at": "2025-02-15"},
    {"crop": "milho", "sown_at": "2025-02-25", "harvested_at": "2025-06-30"},
]


@pytest.fixture(scope="module")
def profile():
    return build_climate_profile(synthetic_series())


def _req(profile, **kw):
    base = {"climate": profile, "field": {"latitude": -18.9, "longitude": -48.3}, "history": HISTORY}
    base.update(kw)
    return AnalysisRequest(**base)


def test_profile_has_12_months_and_sources(profile):
    assert len(profile["monthly"]) == 12
    assert profile["source"]["dataset"] == "NASA POWER"
    assert profile["source"]["citation"]
    assert all(m["eto_mm"] for m in profile["monthly"])


def test_three_alternatives_plus_current_with_full_explanation(profile):
    out = run(_req(profile))
    labels = [s["label"] for s in out["strategies"]]
    assert labels[0] == "A" and out["strategies"][0]["is_current"]
    assert len(out["strategies"]) >= 3
    for s in out["strategies"]:
        assert s["rationale"] and s["evidences"] and s["information_gaps"]
        assert s["benefits"] and s["local_review_risks"]
        assert len(s["criteria"]) == 10
    assert len({tuple(sorted(sum((st["crops"] for st in s["steps"]), []))) for s in out["strategies"]}) == len(out["strategies"])


def test_english_uses_same_scores_and_reuses_portuguese_source_snapshot(profile):
    req = _req(profile)
    with analysis_locale("en-US"):
        english = localize_metadata(run(req))
    portuguese = run(req)
    assert english["strategies"][0]["title"].startswith("Current: Soybean")
    assert english["strategies"][0]["rationale"].startswith("This is your current rotation")
    assert english["diagnosis"]["calendar"][1]["name"] == "Feb"
    assert english["diagnosis"]["source"]["grid_note"].startswith("Gridded data")
    assert portuguese["strategies"][0]["title"].startswith("Atual: Soja")
    assert req.climate["monthly"][1]["name"] == "fev"
    assert [(s["key"], s["score"]) for s in english["strategies"]] == [
        (s["key"], s["score"]) for s in portuguese["strategies"]
    ]


def test_same_family_disease_filter(profile):
    out = run(_req(profile))
    disc = {d["key"]: d for d in out["discarded"]}
    assert "soja_feijao" in disc
    assert "mofo-branco" in " ".join(disc["soja_feijao"]["reasons"])


def test_excluded_crop_is_never_suggested(profile):
    out = run(_req(profile, constraints={"excluded_crops": ["braquiaria", "sorgo"]}))
    crops = {c for s in out["strategies"][1:] for st in s["steps"] for c in st["crops"]}
    assert not crops & {"braquiaria", "sorgo"}


def test_priorities_change_ranking_traceably(profile):
    a = run(_req(profile, priorities={k: 0 for k in ("save_water", "soil_structure", "n_fixation", "erosion_control", "organic_matter", "pest_break", "forage", "extra_income", "market_fit")} | {"n_fixation": 5}))
    b = run(_req(profile, priorities={k: 0 for k in ("save_water", "soil_structure", "n_fixation", "erosion_control", "organic_matter", "pest_break", "forage", "extra_income", "market_fit")} | {"forage": 5}))
    assert a["strategies"][1]["key"] != b["strategies"][1]["key"]
    wa = {w["key"]: w["weight"] for w in a["weights"]}
    assert wa["n_fixation"] == 5 and wa["climate_risk"] == 3


def test_scenario_drier_and_hotter_lowers_water_score(profile):
    base = run(_req(profile))
    dry = run(_req(profile, scenario={"rain_delta_pct": -40, "temp_delta_c": 3}))
    w = lambda o: next(c["score"] for c in o["strategies"][0]["criteria"] if c["key"] == "save_water")
    assert w(dry) < w(base)
    assert dry["diagnosis"]["scenario"]["rain_delta_pct"] == -40


def test_scenario_shifts_heat_threshold(profile):
    p = apply_scenario(profile, 0, 2)
    for a, b in zip(profile["monthly"], p["monthly"]):
        assert (b["heat_days"]["34"] or 0) >= (a["heat_days"]["34"] or 0)


def test_local_data_raises_confidence(profile):
    low = run(_req(profile))
    high = run(_req(profile, soil={"source": "lab_analysis", "texture": "argilosa", "ph_water": 5.8}, constraints={"buyer_crops": ["soja", "milho"]}))
    assert high["strategies"][0]["confidence"]["value"] > low["strategies"][0]["confidence"]["value"]


def test_no_history_still_returns_alternatives(profile):
    out = run(_req(profile, history=[]))
    assert out["strategies"] and not out["strategies"][0]["is_current"]
    assert any("Sem histórico" in w for w in out["warnings"])
