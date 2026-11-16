"""Casos adversariais da auditoria: nao confundir ausencia com seguranca."""
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import main
from app.catalog.loader import load_catalog
from app.climate.indicators import build_climate_profile
from app.engine.criteria import Ctx, step_water
from app.engine.rotation import Step
from app.insights import service
from app.insights.contracts import Fact
from app.insights.store import SnapshotStore
from app.schemas import AnalysisRequest, Constraints, FieldInfo
from tests.synthetic import synthetic_series
from tests.test_insights_http import setup


@pytest.fixture
def profile():
    return build_climate_profile(synthetic_series(2020, 2023))


@pytest.mark.parametrize('monthly', [[1], 'invalid', [{}]])
def test_bad_monthly_is_422(monthly):
    with TestClient(main.app) as client:
        response = client.post('/v1/analysis', json={'climate': {'monthly': monthly},
            'field': {'latitude': -18, 'longitude': -48}})
    assert response.status_code == 422
    assert response.headers['content-type'].startswith('application/problem+json')


def test_missing_rain_never_becomes_perfect_score(profile):
    for month in profile['monthly']:
        month['rain_by_year'] = {y: None for y in month['rain_by_year']}
    with pytest.raises(ValidationError, match='dois anos'):
        AnalysisRequest(climate=profile, field={'latitude': -18, 'longitude': -48})


def test_cross_year_requires_next_year(profile):
    # Mesmo com janeiro no ano inicial, ele nao pertence a safra outubro-fevereiro.
    for month in profile['monthly']:
        for name in ('rain_by_year', 'eto_by_year'):
            month[name] = {'2023': month[name].get('2023')}
    ctx = Ctx(profile, load_catalog(), FieldInfo(latitude=-18, longitude=-48),
              None, Constraints(), None)
    step = Step(crops=['soja'], sow_month=10, end_month=2, purpose='cash')
    water = step_water(ctx, step)
    assert water['per_year'] == {}
    assert water['deficit_p50'] is None


@pytest.mark.parametrize('value,text', [(6., 'O pH nao foi informado.'),
                                       (None, 'Esta cultura dispensa irrigacao.')])
def test_semantic_contradiction_rejected(value, text):
    fact = Fact(id='soil-ph', label='pH', path='/soil/ph', value=value,
                unit=None, source='Produtor', period='desconhecido', limitations=[])
    output = {'insights': [{'kind': 'observation', 'title': 'Solo pendente',
        'explanation': text, 'fact_ids': ['soil-ph'], 'reference_ids': [],
        'limitations': ['Exige revisao local.'], 'questions_for_farmer': []}]}
    with pytest.raises(ValueError):
        service.validate_generated(output, [fact], [])


def test_fallback_survives_missing_prompt_and_bad_corpus(setup, monkeypatch):
    client, analysis, cfg = setup
    cfg.rag_knowledge_dir.mkdir()
    (cfg.rag_knowledge_dir / 'broken.json').write_text('{', encoding='utf-8')
    monkeypatch.setattr(service, 'PROMPT', cfg.cache_dir / 'missing-prompt.txt')
    response = client.post('/v1/insights', json={'analysis_id': analysis['analysis_id']})
    assert response.status_code == 200
    assert response.json()['status'] == 'fallback'


def test_global_budget_cannot_be_bypassed_with_new_ids(tmp_path):
    store = SnapshotStore(tmp_path)
    identifiers = [store.create({}, {})['analysis_id'] for _ in range(21)]
    assert all(store.claim_generation(i) for i in identifiers[:20])
    assert not store.claim_generation(identifiers[-1])


def test_swagger_error_media_matches_http():
    schema = main.app.openapi()
    response = schema['paths']['/v1/analysis']['post']['responses']['422']
    assert 'application/problem+json' in response['content']


def test_complementary_facts_keep_their_own_period():
    snapshot = {'inputs': {}, 'result': {'diagnosis': {
        'source': {'period': {'start': '2000', 'end': '2020'}},
        'earthdata': {'smap': {'recent': {'sm': .21},
                              'coverage': {'start': '2025-01-01', 'end': '2025-12-31'}}}}}}
    facts = service.build_facts(snapshot)
    soil = next(f for f in facts if f.id == 'soil-ph')
    smap = next(f for f in facts if f.id == 'sensor-smap')
    assert soil.period == 'Data de coleta nao informada'
    assert smap.value == .21 and smap.unit == 'm3/m3'
    assert smap.period == '2025-01-01 a 2025-12-31'
    assert any('sensor-smap' in i.fact_ids for i in service.deterministic(facts))
