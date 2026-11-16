from dataclasses import replace
from copy import deepcopy
import time

import pytest
from fastapi.testclient import TestClient
from app import main
from app.provenance import register, verify, store_for, digest
from app.schemas import AnalysisRequest
from app.climate.indicators import build_climate_profile
from tests.synthetic import synthetic_series


@pytest.fixture
def case(tmp_path):
    cfg = replace(main.settings, cache_dir=tmp_path, require_verified_profiles=True)
    profile = build_climate_profile(synthetic_series(2020, 2023))
    return cfg, profile


def request(profile, latitude=-18.9):
    return AnalysisRequest(climate=profile, field={'latitude': latitude, 'longitude': -48.3})


def test_receipt_point_integrity_and_expiration(case):
    cfg, profile = case
    with pytest.raises(ValueError):
        verify(request(profile), cfg)
    signed = register(profile, 'climate', -18.9, -48.3, cfg)
    assert verify(request(signed), cfg)['profiles']['climate'] == 'server_receipt_verified'
    with pytest.raises(ValueError):
        verify(request(signed, -19), cfg)
    altered = deepcopy(signed)
    altered['monthly'][0]['rain_by_year']['2020'] = 999
    with pytest.raises(ValueError):
        verify(request(altered), cfg)
    with store_for(cfg).connect() as db:
        db.execute('UPDATE source_receipts SET expires=0')
    with pytest.raises(ValueError):
        verify(request(signed), cfg)


def test_strict_http_accepts_registered_profile_and_rejects_invented(case, monkeypatch):
    cfg, profile = case
    monkeypatch.setattr(main, 'settings', cfg)
    body = {'climate': profile, 'field': {'latitude': -18.9, 'longitude': -48.3}}
    with TestClient(main.app) as client:
        assert client.post('/v1/analysis', json=body).status_code == 422
        body['climate'] = register(profile, 'climate', -18.9, -48.3, cfg)
        response = client.post('/v1/analysis', json=body)
        assert response.status_code == 200, response.text
        assert response.json()['source_verification']['profiles']['climate'] == 'server_receipt_verified'
        assessment = client.post('/v1/cultivation-assessment', json={**body, 'crop': 'soja',
            'sowing_date': '2026-10-20', 'harvest_date': '2027-02-15'})
        assert assessment.status_code == 200
        assert assessment.json()['source_verification']['profiles']['climate'] == 'server_receipt_verified'


def test_receipt_cannot_be_reused_as_another_source(case):
    cfg, profile = case
    registered = register(profile, 'terrain', -18.9, -48.3, cfg)
    with pytest.raises(ValueError):
        verify(request(registered), cfg)


def test_browser_numeric_serialization_preserves_hash():
    assert digest({'monthly': [{'rain': 1.0, 'zero': -0.0}]}) == digest({'monthly': [{'zero': 0, 'rain': 1}]})
    assert digest({'rain': 1}) != digest({'rain': 2})
