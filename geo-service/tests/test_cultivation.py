"""Rastreio historico: casos controlados, sem servicos externos."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from app import main
from app.climate.indicators import build_climate_profile
from app.engine.cultivation import CultivationRequest, assess
from tests.synthetic import synthetic_series


@pytest.fixture
def body():
    profile = build_climate_profile(synthetic_series(2015, 2023))
    for m in profile['monthly']:
        m['rain_by_year'] = {y: 300. for y in m['rain_by_year']}
        m['eto_by_year'] = {y: 100. for y in m['eto_by_year']}
        m['tmean_c'] = 25.
        m['frost_prob'] = {k: 0. for k in m['frost_prob']}
        m['heat_days'] = {k: 0. for k in m['heat_days']}
    return dict(climate=profile, field={'latitude': -18.9, 'longitude': -48.3},
                crop='soja', sowing_date='2026-10-20', harvest_date='2027-02-15',
                soil={'source': 'lab_analysis', 'ph_water': 6.})


def test_favorable_requires_all_factors(body):
    result = assess(CultivationRequest(**body))
    assert result['status'] == 'favoravel_no_historico'
    assert all(f['status'] == 'compativel' for f in result['factors'])
    water = result['factors'][0]['evidence']
    assert '2023' not in water['per_year']  # janeiro/2024 nao existe
    assert all(f['rule'] and f['source'] and f['evidence'] for f in result['factors'])


def test_unknown_soil_is_not_full_favorable(body):
    body.pop('soil')
    result = assess(CultivationRequest(**body))
    assert result['status'] == 'parcialmente_favoravel'
    assert result['factors'][2]['status'] == 'sem_dados'


def test_dry_cycle_is_limitant(body):
    for m in body['climate']['monthly']:
        m['rain_by_year'] = {y: 0. for y in m['rain_by_year']}
        m['eto_by_year'] = {y: 250. for y in m['eto_by_year']}
    result = assess(CultivationRequest(**body))
    assert result['status'] == 'limitacoes_relevantes'
    assert result['factors'][0]['status'] == 'limitante'


def test_short_history_cannot_conclude_water(body):
    for m in body['climate']['monthly']:
        for key in ('rain_by_year', 'eto_by_year'):
            m[key] = {y: v for y, v in m[key].items() if str(y) in ('2022', '2023')}
    result = assess(CultivationRequest(**body))
    assert result['status'] == 'dados_insuficientes'


@pytest.mark.parametrize('change', [dict(crop='inexistente'), dict(harvest_date='2026-01-01'),
                                     dict(harvest_date='2028-01-01')])
def test_invalid_input_422(body, change):
    with TestClient(main.app) as client:
        response = client.post('/v1/cultivation-assessment', json={**body, **change})
    assert response.status_code == 422


def test_http_contract_and_swagger(body):
    with TestClient(main.app) as client:
        response = client.post('/v1/cultivation-assessment', json=body)
    assert response.status_code == 200, response.text
    assert response.json()['rules_version'] == 'cultivation-screening-v1'
    operation = main.app.openapi()['paths']['/v1/cultivation-assessment']['post']
    assert operation['security'] and operation['responses']['200']
