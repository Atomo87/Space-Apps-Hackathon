from fastapi.testclient import TestClient
from app import main
from app.schemas import AnalysisRequest
import pytest


def test_no_demo_endpoint_or_control():
    with TestClient(main.app) as client:
        assert client.get('/v1/demo-profile').status_code == 404
        html = client.get('/test').text
        assert 'load-demo' not in html and 'demo-notice' not in html
    assert '/v1/demo-profile' not in main.app.openapi()['paths']


def test_old_demo_profiles_are_rejected():
    with pytest.raises(ValueError, match='demonstrativos'):
        AnalysisRequest(climate={'source': {'demo': True}}, field={'latitude': -18, 'longitude': -48})
