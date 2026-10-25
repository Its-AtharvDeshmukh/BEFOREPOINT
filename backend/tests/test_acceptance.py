"""Problem 2.1 acceptance: temporal isolation, adaptation, lead time and API coverage."""
import copy
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sentinel.api import app
from sentinel.models import Event
from sentinel.replay import Replay
from sentinel.receipts import ReceiptStore
from sentinel.inference import BayesianFilter
from sentinel.decision import decide,cost_matrix,deadline_miss_mass
from sentinel.graph import forecast,deadlines
from sentinel.voi import value_of_information
from sentinel.settings import CONFIG as C


def event(id,kind,t=1,source='independent',zone='river',gateway=None,**kwargs):
    return Event(id=id,kind=kind,event_time=t,arrival_time=t,source_id=source,zone_id=zone,gateway=gateway,**kwargs)


def test_reliability_carries_across_episodes_without_retroactive_learning(tmp_path):
    store=ReceiptStore(str(tmp_path/'learning.sqlite3'))
    a=Replay('normal_rain',store=store)
    a.queue(event('bad','water_high',source='known-bad'))
    a.step()
    a.queue(event('judgment','verification',t=2,source='operator',retracts='bad',payload={'correct':False}))
    a.step()
    assert store.source_priors()['known-bad']==[8.,3.]
    original=copy.deepcopy(a.history[-1])
    b=Replay('normal_rain',store=store)
    assert b.initial_source_betas['known-bad']==[8.,3.]
    observations=[event('new','water_high',source='known-bad')]
    learned=b.engine.estimate(observations,1)[0]
    fresh=BayesianFilter().estimate(observations,1)[0]
    assert learned[3]<fresh[3]
    # A duplicate adjudication cannot increment the shared ledger again.
    a.queue(event('duplicate-judgment','verification',t=3,source='operator',retracts='bad',payload={'correct':False}))
    a.step()
    assert store.source_priors()['known-bad']==[8.,3.]
    assert a.history[2]==original
    assert a.initial_source_betas=={}
    assert ReceiptStore(str(tmp_path/'learning.sqlite3')).source_priors()['known-bad']==[8.,3.]


@pytest.mark.parametrize('context',[
    [event('normal','water_normal',source='independent-level')],
    [event('high','water_high',source='independent-level'),event('calls','calls_surge',source='dispatch')],
    [event('high','water_high',source='independent-level'),event('contradiction','water_normal',source='other-level')]
])
def test_gateway_cutouts_remain_one_common_cause_in_different_contexts(context):
    one=[event('loss','stream_missing',source='sensor',gateway='shared')]
    many=[event(str(i),'stream_missing',source=f'sensor-{i}',gateway='shared') for i in range(100)]
    engine=BayesianFilter()
    np.testing.assert_allclose(engine.estimate(context+one,1)[0],engine.estimate(context+many,1)[0],atol=1e-12)


def test_independent_contradiction_revises_belief():
    engine=BayesianFilter()
    high=event('h','water_high')
    before=engine.estimate([high],2)[0]
    after=engine.estimate([high,event('normal','water_normal',t=2,source='independent-normal')],2)[0]
    assert after[3]<before[3]


def test_camera_and_multiple_stream_losses_do_not_mean_safe():
    events=[event(str(i),'stream_missing',source=f'camera-{i}',gateway='camera-gateway') for i in range(15)]
    events+=[event('hospital','hospital_surge',source='hospital'),event('dispatch','dispatch_delay',source='dispatch')]
    p=BayesianFilter().estimate(events,2)[0]
    assert np.isfinite(p).all() and p.sum()==pytest.approx(1)
    assert p[1]>0 and p[3]>0


def test_prior_shift_only_applies_when_available():
    signal=event('monsoon','baseline_shift',t=4,source='weather-operator')
    engine=BayesianFilter()
    np.testing.assert_array_equal(engine.estimate([signal],3)[0],engine.estimate([],3)[0])
    assert engine.estimate([signal],6)[0][3]>engine.estimate([],6)[0][3]


def test_stability_margin_rejects_tiny_switch_and_accepts_material_change():
    assert decide([.955,0,0,.045],'WATCH',10)['action']=='WATCH'
    assert decide([.92,0,0,.08],'WATCH',10)['action']=='PREPARE'


def test_healthy_reading_in_another_zone_does_not_clear_river_forecast():
    predictions=forecast([event('river-high','water_high'),event('north-normal','water_normal',zone='north',source='north')],2,[.1,.1,.2,.6])
    underpass=next(f for f in predictions if f['component']=='underpass')
    assert underpass['supporting_observations']==['river-high']
    assert underpass['event_type']=='underpass_disruption'
    assert underpass['assumptions'] and underpass['uncertainty']


def test_forecasts_respect_learned_source_reliability():
    events=[event('water','water_high',source='bad')]
    high=forecast(events,2,[.1,.1,.2,.6],{'bad':.8})
    low=forecast(events,2,[.1,.1,.2,.6],{'bad':.2})
    assert low[0]['probability']<high[0]['probability']


def test_operational_lead_time_and_event_probability_affect_expected_costs():
    prediction=[{'component':'underpass','probability':.9,'window':[2,3]}]
    rows=deadlines(prediction,1)
    p=[.1,.1,.2,.6]
    matrix=cost_matrix(rows)
    assert (matrix>=np.array(C['costs'])).all()
    later=cost_matrix(rows,3)
    assert (later>=matrix).all()
    zero=[{**r,'event_probability':0.} for r in rows]
    np.testing.assert_array_equal(cost_matrix(zero),C['costs'])
    decision=decide(p,deadlines=rows)
    for name in C['actions']:
        assert decision['costs'][name]==pytest.approx(decision['base_costs'][name]+decision['lead_time_costs'][name])


def test_voi_responds_to_quality_cost_and_delay():
    p=[.35,.25,.25,.15]
    good={'id':'good','label':'High quality','positive':[.05,.05,.8,.95],'delay':0.,'cost':0.,'inconclusive':.1}
    weak={**good,'id':'weak','positive':[.45,.45,.55,.55]}
    good_result=value_of_information(p,[],[good])
    weak_result=value_of_information(p,[],[weak])
    assert good_result['checks'][0]['evsi']>weak_result['checks'][0]['evsi']
    assert good_result['selected_check']=='good'
    expensive=value_of_information(p,[],[{**good,'cost':1000.,'delay':30.}])
    assert expensive['selected_check'] is None
    neutral=value_of_information(p,[],[{**good,'positive':[.5]*4}])
    assert neutral['checks'][0]['evsi']==pytest.approx(0,abs=1e-10)


def test_voi_deadline_penalty_uses_forecast_probability():
    p=[.2,.1,.3,.4]
    rows=deadlines([{'component':'underpass','probability':.9,'window':[3,4]}],1)
    zero=[{**r,'event_probability':0.} for r in rows]
    check={'id':'check','label':'Check','positive':[.1,.2,.7,.9],'delay':3.,'cost':.1,'inconclusive':.1}
    high=value_of_information(p,rows,[check])['checks'][0]
    low=value_of_information(p,zero,[check])['checks'][0]
    assert high['deadline_penalty']>low['deadline_penalty']
    assert low['deadline_penalty']==pytest.approx(0)
    assert high['net_value']==pytest.approx(high['evsi']-high['cost']-high['delay_harm']-high['deadline_penalty'])


def test_analysis_diagnostics_and_decisions_api_contracts():
    with TestClient(app) as client:
        client.post('/api/reset',json={})
        response=client.post('/api/analysis/verify',json={'probabilities':[.4,.2,.2,.2]})
        assert response.status_code==200
        data=response.json()
        assert 'checks' in data['verification'] and data['mode'].startswith('explicit')
        for probabilities in ([.1]*4,[1.,0,0],[-.1,.2,.2,.7]):
            assert client.post('/api/analysis/verify',json={'probabilities':probabilities}).status_code==422
        diagnostics=client.get('/api/diagnostics').json()
        assert diagnostics['sqlite_integrity']=='ok'
        assert diagnostics['stored_records']['run_metadata']>=1
        assert not diagnostics['public_emergency_broadcasts_enabled']
        assert client.get('/api/decisions').json()['decision']['lead_time_costs']
        for _ in range(8):client.post('/api/step')
        assert client.get('/api/receipts').json()['valid']


def test_provider_contract_rejects_missing_variables_and_misaligned_arrays():
    from sentinel.weather import validate_weather
    with pytest.raises(ValueError):validate_weather({'current':{},'hourly':{}})
    current={'time':'2026-10-25T12:00','temperature_2m':27,'relative_humidity_2m':50,'precipitation':0,'rain':0,'weather_code':1,'wind_speed_10m':5}
    hourly={key:[0] for key in ('temperature_2m','relative_humidity_2m','precipitation_probability','precipitation','rain','wind_speed_10m')}
    hourly['time']=['2026-10-25T12:00']
    payload={'current':current,'hourly':hourly,'current_units':{},'hourly_units':{},'timezone':'Asia/Kolkata'}
    assert validate_weather(payload)['current']['temperature_2m']==27
    hourly['rain']=[]
    with pytest.raises(ValueError):validate_weather(payload)


def test_weather_rate_limit_does_not_hammer_provider(monkeypatch):
    from sentinel import weather
    weather.cache.clear();weather.backoff_until.clear()
    calls=[]
    async def limited(location):
        calls.append(location)
        raise weather.ProviderRateLimit(60)
    monkeypatch.setattr(weather,'fetch_weather',limited)
    with TestClient(app) as client:
        assert client.get('/api/weather?location=nagpur').status_code==503
        response=client.get('/api/weather?location=nagpur')
        assert response.status_code==503 and response.headers['retry-after']
        assert len(calls)==1
        # Core replay does not need any external provider.
        assert client.post('/api/reset',json={'scenario':'flood'}).status_code==200
        assert client.post('/api/step').json()['current']['minute']==1
    weather.backoff_until.clear()
