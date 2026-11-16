from dataclasses import replace

from fastapi.testclient import TestClient
from app import main


def test_testbench_and_assets_are_served():
    client = TestClient(main.app)
    page = client.get('/test')
    assert page.status_code == 200
    assert 'no-store' in page.headers['cache-control']
    assert 'id="dataset-cards"' in page.text
    assert 'id="analysis-form"' in page.text
    assert client.get('/test-assets/test.js').status_code == 200
    assert client.get('/test-assets/test.css').status_code == 200


def test_visible_cultivation_copy_preserves_portuguese():
    with TestClient(main.app) as client:
        html = client.get('/test').text
        script = client.get('/test-assets/test.js').text
    assert 'A cultura encontrará condições favoráveis?' in html
    assert 'Avaliação histórica exploratória por água, clima e pH. Não prevê a safra.' in html
    assert 'Tolerância de chuva (%)' in html
    assert 'Compatível no histórico' in script
    assert 'Limitações da avaliação' in script
    assert 'condi??es' not in html and 'conclu?do' not in script


def test_testbench_does_not_bypass_api_authentication(monkeypatch):
    monkeypatch.setattr(main, 'settings', replace(main.settings, api_token='dummy-test-only'))
    client = TestClient(main.app)
    assert client.get('/test').status_code == 200
    assert client.get('/v1/catalog').status_code == 401
    assert client.get('/v1/catalog', headers={'X-GeoSafra-Token': 'dummy-test-only'}).status_code == 200
