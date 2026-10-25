import os
os.environ['SENTINEL_DB']=':memory:'
from fastapi.testclient import TestClient
from sentinel.api import app


def test_end_to_end_and_citizen():
    with TestClient(app) as client:
        assert client.get('/api/health').json()['mode']=='simulation'
        assert client.post('/api/reset',json={'scenario':'twin_crisis','seed':26}).status_code==200
        before=client.get('/api/state').json()
        r=client.post('/api/citizen',json={'zone_id':'river','answer':'yes','token':'test-observer'})
        assert r.status_code==202
        assert client.post('/api/citizen',json={'zone_id':'river','answer':'yes','token':'test-observer'}).status_code==409
        after=client.post('/api/step').json()
        assert after['current']['minute']==before['current']['minute']+1
        assert any(e['kind']=='citizen_yes' for e in after['events'])
        for _ in range(10): assert client.post('/api/step').status_code==200
        receipts=client.get('/api/receipts').json()
        assert receipts['valid']
        assert len(after['current']['probabilities'])==4
        assert client.post('/api/reset',json={'scenario':'not-real'}).status_code==422
        assert client.post('/api/start').json()['running']
        assert not client.post('/api/pause').json()['running']
        assert client.get('/api/twins').json()['prefix_equal']
        assert client.get('/api/runs').status_code==200


def test_fault_injection_reference_and_temporal_validation():
    with TestClient(app) as client:
        client.post('/api/reset',json={})
        data={'id':'injected','source_id':'judge','kind':'water_high','zone_id':'river','event_time':1,'arrival_time':1}
        assert client.post('/api/events',json=data).status_code==202
        assert client.post('/api/events',json=data).json()['accepted'] is False
        assert client.post('/api/events',json={**data,'kind':'water_normal'}).status_code==409
        assert client.post('/api/events',json={**data,'id':'future','event_time':5,'arrival_time':5}).status_code==409
        assert client.post('/api/events',json={**data,'id':'ret','kind':'retraction','retracts':'nonexistent'}).status_code==409
        state=client.post('/api/step').json()
        assert 'injected' in state['current']['visible_event_ids']
