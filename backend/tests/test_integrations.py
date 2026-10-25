import os
os.environ['SENTINEL_DB']=':memory:'
import pytest
import httpx
from fastapi.testclient import TestClient
from sentinel.api import app
from sentinel import weather
from sentinel.notifications import NotificationAdapter,Registration
import sqlite3


def test_weather_cache_and_stale_fallback(monkeypatch):
    weather.cache.clear()
    calls=[]
    async def provider(location):
        calls.append(location)
        return {'current':{'temperature_2m':27,'time':'2026-10-25T12:00'},'hourly':{'time':[]}}
    monkeypatch.setattr(weather,'fetch_weather',provider)
    with TestClient(app) as client:
        first=client.get('/api/weather?location=nagpur').json()
        second=client.get('/api/weather?location=nagpur').json()
        assert first['cache_status']=='fresh'
        assert second['cache_status']=='cached' and len(calls)==1
        weather.cache['nagpur']['timestamp']-=601
        async def failing(location):raise httpx.ConnectError('offline')
        monkeypatch.setattr(weather,'fetch_weather',failing)
        response=client.get('/api/weather?location=nagpur')
        assert response.status_code==200
        assert response.json()['cache_status']=='stale'
        assert response.json()['data']['current']['temperature_2m']==27
        weather.cache.clear()
        assert client.get('/api/weather?location=nagpur').status_code==503
        assert client.get('/api/weather?location=unsupported').status_code==422


def test_weather_never_enters_simulation(monkeypatch):
    weather.cache.clear()
    async def provider(location):return {'current':{'temperature_2m':80},'hourly':{'time':[]}}
    monkeypatch.setattr(weather,'fetch_weather',provider)
    with TestClient(app) as client:
        client.post('/api/reset',json={})
        before=client.get('/api/state').json()
        client.get('/api/weather?location=nagpur')
        after=client.get('/api/state').json()
        assert before['current']['hash']==after['current']['hash']
        assert before['events']==after['events']


def test_twin_controls_and_hidden_outcomes():
    with TestClient(app) as client:
        data=client.post('/api/twin-lab/reset',json={'seed':104729,'pair':'standard'}).json()
        assert data['minute']==0 and data['outcomes'] is None
        assert 'scenario' not in data['a']
        assert client.post('/api/twin-lab/reveal').status_code==409
        for minute in range(1,8):
            data=client.post('/api/twin-lab/step').json()
            assert data['prefix_consistent']
            assert data['a']['current']['probabilities']==data['b']['current']['probabilities']
        assert data['prefix_complete']
        data=client.post('/api/twin-lab/step').json()
        assert data['different_evidence']
        assert data['outcomes'] is None
        data=client.post('/api/twin-lab/reveal').json()
        assert data['outcomes']['a']=='CASCADING_CRISIS'
        assert data['outcomes']['b']=='SENSOR_FAILURE'
        assert client.post('/api/twin-lab/start').json()['running']
        assert not client.post('/api/twin-lab/pause').json()['running']
        assert client.post('/api/twin-lab/reset',json={'pair':'unknown'}).status_code==422


def test_registration_is_opt_out_capable_and_tokens_are_never_returned(monkeypatch):
    monkeypatch.delenv('GOOGLE_APPLICATION_CREDENTIALS',raising=False)
    with TestClient(app) as client:
        identity='local-test-browser-0000001'
        data={'client_id':identity,'token':'private-token-for-this-browser-0000001','zone_id':'river'}
        assert client.post('/api/notifications/register',json=data).status_code==201
        status=client.get('/api/notifications/status',params={'client_id':identity})
        assert status.json()['registered']
        assert 'private-token' not in status.text
        assert not status.json()['server_credentials_configured']
        assert client.post('/api/notifications/test',json={'client_id':identity}).status_code==503
        assert client.post('/api/notifications/unsubscribe',json={'client_id':identity}).status_code==200
        assert not client.get('/api/notifications/status',params={'client_id':identity}).json()['registered']
        assert client.post('/api/notifications/test',json={'client_id':identity}).status_code==409


def test_observation_requests_are_private_to_browser_and_work_without_push():
    with TestClient(app) as client:
        identity='in-app-browser-0000000001'
        response=client.post('/api/notifications/observation-request',json={'client_id':identity,'zone_id':'river'})
        assert response.status_code==201 and response.json()['simulated']
        assert not response.json()['push']['sent']
        rows=client.get('/api/notifications/requests',params={'client_id':identity}).json()
        assert any(row['id']==response.json()['id'] for row in rows)
        other=client.get('/api/notifications/requests',params={'client_id':'different-browser-0000001'}).json()
        assert all(row['id']!=response.json()['id'] for row in other)


def test_main_outcome_is_gated_until_end():
    with TestClient(app) as client:
        client.post('/api/reset',json={})
        assert client.post('/api/outcome/reveal').status_code==409
        for _ in range(18):client.post('/api/step')
        response=client.post('/api/outcome/reveal')
        assert response.status_code==200
        assert response.json()['outcome']=='CASCADING_CRISIS'


def test_calibration_bins_are_calculated():
    from sentinel.evaluation import calibration_bins
    data=calibration_bins([(.1,0),(.15,1),(.9,1),(1.,1)])
    assert sum(b['count'] for b in data)==4
    assert data[0]['mean_predicted']==pytest.approx(.125)
    assert data[0]['observed_frequency']==.5
    assert data[-1]['count']==2
