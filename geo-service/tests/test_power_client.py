import asyncio
import json

import httpx
import pytest

from app.config import Settings
from app.power.client import PowerClient, PowerError, normalize_year_payload
from tests.synthetic import synthetic_payload


def test_fill_value_becomes_none_not_zero():
    payload = synthetic_payload(2020, fill_every=10)
    n = normalize_year_payload(payload, 2020)
    rain = n["values"]["PRECTOTCORR"]
    assert rain[0] is None and rain[10] is None
    assert all(v is None or v >= 0 for v in rain)
    assert len(n["dates"]) == 366  # bissexto


def _client(tmp_path, handler):
    cfg = Settings(cache_dir=tmp_path, power_concurrency=2, start_year=2020, end_year=2021)
    return PowerClient(cfg, transport=httpx.MockTransport(handler))


def test_fetch_uses_cache_and_drops_optional_on_422(tmp_path):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.params["parameters"])
        if "GWETROOT" in request.url.params["parameters"]:
            return httpx.Response(422, json={"messages": ["bad parameter"]})
        year = int(request.url.params["start"][:4])
        payload = synthetic_payload(year)
        for k in ("GWETROOT", "GWETTOP"):
            payload["properties"]["parameter"].pop(k)
        return httpx.Response(200, json=payload)

    s = asyncio.run(_client(tmp_path, handler).fetch(-18.9, -48.3))
    assert s.missing_optional == ["GWETROOT", "GWETTOP"]
    assert len(s.dates) == 366 + 365
    first = len(calls)
    s2 = asyncio.run(_client(tmp_path, handler).fetch(-18.9, -48.3))
    assert s2.cache_hits >= 2 and len(calls) == first + 1  # só a tentativa recusada se repete


def test_http_error_is_reported(tmp_path):
    def handler(request):
        return httpx.Response(400, text="nope")

    with pytest.raises(PowerError):
        asyncio.run(_client(tmp_path, handler).fetch(-18.9, -48.3))
