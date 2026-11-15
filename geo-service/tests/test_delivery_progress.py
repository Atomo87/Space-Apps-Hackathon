from fastapi.testclient import TestClient
from app import main
from app.delivery import progress, RUBRIC
from tests.test_insights_http import setup


def test_percentages_are_reproducible_and_not_certification():
    result = progress()
    assert sum(o.weight for o in result.objectives) == 100
    assert len({o.key for o in result.objectives}) == len(result.objectives)
    for objective in result.objectives:
        assert objective.percent == round(100 * sum(c.complete for c in objective.criteria) / len(objective.criteria), 1)
    assert result.overall_percent == round(sum(o.weight * o.percent for o in result.objectives) / 100, 1)
    assert result.ready_for_delivery is False
    assert 'Nao e porcentagem oficial' in result.interpretation


def test_progress_http_and_soil_metadata_snapshot(setup):
    client, previous, cfg = setup
    from app.climate.indicators import build_climate_profile
    from tests.synthetic import synthetic_series
    progress_response = client.get('/v1/delivery-progress')
    assert progress_response.status_code == 200
    response = client.post('/v1/analysis', json={
        'climate': build_climate_profile(synthetic_series(2020, 2023)),
        'field': {'latitude': -18.9, 'longitude': -48.3},
        'soil': {'source': 'lab_analysis', 'ph_water': 6., 'sampled_at': '2025-10-15',
                 'analysis_provider': 'Laboratorio de teste', 'report_reference': 'TEST-001'}})
    assert response.status_code == 200, response.text
    from app.insights.store import SnapshotStore
    snapshot = SnapshotStore(cfg.cache_dir).get(response.json()['analysis_id'])
    assert snapshot['inputs']['soil']['sampled_at'] == '2025-10-15'
    from app.insights.service import build_facts
    assert next(f for f in build_facts(snapshot) if f.id == 'soil-ph').period == '2025-10-15'
