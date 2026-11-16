import runpy
from pathlib import Path

import httpx


def test_verifier_reports_connection_failure_without_leaking_details(monkeypatch):
    verify = runpy.run_path(str(Path(__file__).parents[1] / 'verify-delivery.py'))['verify']
    original = httpx.Client
    def unavailable(request):
        raise httpx.ConnectError('private-secret-must-not-appear', request=request)
    monkeypatch.setattr(httpx, 'Client', lambda **kw: original(**kw, transport=httpx.MockTransport(unavailable)))
    report = verify(8010, True)
    assert report['status'] == 'blocked'
    assert 'private-secret' not in str(report)


def test_wrong_server_never_triggers_live_consultation(monkeypatch):
    verify = runpy.run_path(str(Path(__file__).parents[1] / 'verify-delivery.py'))['verify']
    original = httpx.Client
    calls = []
    def wrong_server(request):
        calls.append(request.url.path)
        if request.url.path == '/health':
            return httpx.Response(200, json={'status': 'ok'})
        if request.url.path == '/openapi.json':
            return httpx.Response(200, json={'paths': {}})
        return httpx.Response(404, json={'detail': 'Not Found'})
    monkeypatch.setattr(httpx, 'Client', lambda **kw: original(**kw, transport=httpx.MockTransport(wrong_server)))
    report = verify(8010, True)
    assert report['status'] == 'blocked'
    assert '/v1/climate-profile' not in calls
    assert any(c['check'] == 'version_routes' and not c['passed'] for c in report['checks'])
