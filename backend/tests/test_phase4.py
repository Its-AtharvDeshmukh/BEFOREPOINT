import copy
from dataclasses import replace
import numpy as np
import pytest
from pydantic import ValidationError
from sentinel.replay import Replay
from sentinel.prove import rank,request_check,reveal_check,sample_outcome
from sentinel.voi import value_of_information,counterfactual_check
from sentinel.verification_catalog import CATALOG,effective_check,outcome_likelihood
from sentinel.models import Event
from sentinel.settings import CONFIG as C

def test_prove_reuses_voi_and_ranks_by_net_loss():
    r=Replay();r.step();r.step();s=r.history[-1];result=rank(s)
    baseline=value_of_information(list(s['probabilities'].values()),s['deadlines'],[effective_check(c) for c in CATALOG])
    for c in result['checks']:
        previous=next(x for x in baseline['checks'] if x['id']==c['id'])
        assert c['net_value']==pytest.approx(previous['net_value'])
        assert sum(o['probability'] for o in c['outcomes'])==pytest.approx(1)
        assert all(sum(o['posterior'])==pytest.approx(1) for o in c['outcomes'])
    feasible=[c for c in result['checks'] if c['available']]
    assert feasible[0]['best_net_value']==max(c['best_net_value'] for c in feasible)

def test_delay_cost_and_decision_sensitivity():
    p=[.5,.1,.2,.2];base=effective_check(CATALOG[0]);options=value_of_information(p,[],[base,{**base,'id':'expensive','cost':1000},{**base,'id':'slow','delay':50}])['checks']
    assert options[1]['net_value']<0 and options[1]['net_value']<options[0]['net_value']
    assert options[2]['delay_harm']>options[0]['delay_harm']
    assert len({o['optimal_action'] for o in options[0]['outcomes']})>1
    # Uninformative evidence changes neither probabilities nor the optimal action.
    x=value_of_information(p,[],[{**base,'positive':[.5]*4}])['checks'][0]
    assert x['evsi']==pytest.approx(0)
    assert all(o['posterior']==pytest.approx(p) for o in x['outcomes'])

def test_request_reveal_due_duplicate_and_filter_ingestion():
    r=Replay();r.step();r.step();h=r.history[-1]['hash'];t=request_check(r,'observer',h)
    assert request_check(r,'observer',h)==t
    with pytest.raises(ValueError,match='not available'):reveal_check(r,'observer')
    r.step();answer=reveal_check(r,'observer');m=r.minute
    assert answer['ticket']['status']=='applied' and 'check-result:observer' in r.events
    assert reveal_check(r,'observer')['ticket']==answer['ticket'] and r.minute==m
    assert r.store.verify(r.run_id)
    assert any('check-result:observer' in trace['events'] for trace in r.history[-1]['evidence_trace'])

def test_shared_gateway_availability_and_late_checks():
    r=Replay();[r.step() for _ in range(4)]
    pump=next(c for c in rank(r.history[-1])['checks'] if c['id']=='pump')
    assert not pump['available']
    with pytest.raises(ValueError,match='gateway'):request_check(r,'pump',r.history[-1]['hash'])
    while r.minute<18:r.step()
    assert not any(c['available'] for c in rank(r.history[-1])['checks'])

def test_verification_future_isolation_and_twin_prefix():
    a=Replay('twin_crisis',9);b=Replay('twin_benign',9)
    for _ in range(4):a.step();b.step()
    assert rank(a.history[-1])==rank(b.history[-1])
    poison=replace(a.episode,truth='NOISE',failures=tuple((node,t+100) for node,t in a.episode.failures))
    for c in CATALOG:
        assert sample_outcome(a.episode,9,c['id'],3,5)==sample_outcome(poison,9,c['id'],3,5)
        assert sample_outcome(a.episode,9,c['id'],3,5)==sample_outcome(b.episode,9,c['id'],3,5)

def test_contradictory_check_and_categorical_normalization():
    p=[.1,.1,.2,.6];c=effective_check(CATALOG[0]);negative=counterfactual_check(p,c,'negative')
    assert negative[3]<p[3]
    assert np.allclose(sum(outcome_likelihood('water',o,.8) for o in ('positive','negative','inconclusive')),np.ones(4))
    with pytest.raises(ValidationError):Event(id='bad',source_id='fake',kind='verification_result',zone_id='river',event_time=1,arrival_time=1,payload={'candidate_id':'water','outcome':'always_crisis'})

def test_stale_snapshot_rejected():
    r=Replay();h=r.history[-1]['hash'];r.step()
    with pytest.raises(ValueError,match='Snapshot changed'):request_check(r,'water',h)

from sentinel.interventions import evaluate_interventions
from sentinel.lifelines import inspect_lifelines,apply_blackout,structural_score,STREAMS

def test_cascade_paired_deterministic_resources_and_no_benefit():
    r=Replay('flood');[r.step() for _ in range(3)];s=r.history[-1]
    a=evaluate_interventions(s,samples=1024);b=evaluate_interventions(s,samples=1024)
    assert a==b
    for plan in a['plans']:
        if plan['feasible']:assert plan['resources']['crews']<=2 and plan['resources']['pumps']<=1 and plan['resources']['cost']<=9
    inspect=next(p for p in a['plans'] if p['id']=='inspect');monitor=next(p for p in a['plans'] if p['id']=='monitor')
    assert inspect['expected_harm']==monitor['expected_harm'] and inspect['net_benefit']==-1
    assert any(p.get('net_benefit',0)>0 for p in a['plans'])
    no_resources=evaluate_interventions(s,crews=0,pumps=0,budget=0)
    assert [p['id'] for p in no_resources['plans'] if p['feasible']]==['monitor']

def test_cascade_late_preparation_side_effects_and_assumptions():
    r=Replay('flood');[r.step() for _ in range(3)];s=r.history[-1]
    late=evaluate_interventions(s,start_delay=24)
    monitor=next(p for p in late['plans'] if p['id']=='monitor')
    for plan in late['plans']:
        if plan['feasible']:assert plan['expected_harm']==monitor['expected_harm']
    a=evaluate_interventions(s,samples=2048);access=next(p for p in a['plans'] if p['id']=='access');monitor=next(p for p in a['plans'] if p['id']=='monitor')
    assert access['node_probabilities']['alternate_road']>=monitor['node_probabilities']['alternate_road']
    assert a['plans']!=evaluate_interventions(s,dependency_scale=.5,samples=2048)['plans']
    assert all(w['latest_start_delay'] is None or np.isfinite(w['latest_start_delay']) for w in a['windows'])

def test_cascade_missing_input_and_future_isolation():
    a=Replay('twin_crisis');b=Replay('twin_benign')
    assert evaluate_interventions(a.history[-1])['selected_plan']=='monitor'
    for _ in range(5):a.step();b.step()
    assert evaluate_interventions(a.history[-1])==evaluate_interventions(b.history[-1])
    a.episode=replace(a.episode,truth='NOISE',failures=())
    assert evaluate_interventions(a.history[-1])==evaluate_interventions(b.history[-1])

def test_structure_redundancy_and_backup_are_independent_of_streams():
    assert structural_score(0,False,18)>structural_score(3,False,18)>structural_score(3,True,18)
    r=Replay();before=inspect_lifelines(r)
    result=apply_blackout(r,26,r.history[-1]['hash'])['result']
    assert result['disconnected_count']==6 and result['eligible_count']==10
    assert [z['structural_score'] for z in before['zones']]==[z['structural_score'] for z in result['zones']]
    assert sum(s['status']=='disconnected' for s in result['streams'])==6
    assert set(result['blackout']['selected_streams'])<=set(s['source'] for s in STREAMS)
    assert all(z['hazard_status']=='unknown' for z in result['zones'])
    assert len([t for t in r.history[-1]['evidence_trace'] if t['group']=='group:blackout:network'])==1

def test_blackout_reproducible_idempotent_and_suppresses_future():
    a=Replay('flood');b=Replay('flood');h=a.history[-1]['hash']
    first=apply_blackout(a,26,h);apply_blackout(b,26,b.history[-1]['hash']);minute=a.minute
    assert a.disabled_streams==b.disabled_streams
    apply_blackout(a,26,h);assert a.minute==minute
    for _ in range(8):a.step()
    assert not any(e.source_id in a.disabled_streams and e.kind!='stream_missing' and e.arrival_time>minute for e in a.events.values())
    assert a.store.verify(a.run_id)
    assert all('identity' not in s and 'latitude' not in s for s in inspect_lifelines(a)['streams'])

def test_lifelines_contradiction_and_unknown_separate():
    r=Replay();n=r.minute+1
    for kind in ('water_high','water_normal'):
        r.queue(Event(id=kind,source_id=kind,kind=kind,zone_id='river',event_time=n,arrival_time=n))
    r.step();z=next(z for z in inspect_lifelines(r)['zones'] if z['id']=='river')
    assert z['hazard_status']=='conflicting reports' and z['observation_quality']==0

def test_discrete_response_delay_matches_model_and_stale_evidence_time():
    r=Replay();s=r.history[-1];gateway=next(c for c in rank(s)['checks'] if c['id']=='gateway')
    assert gateway['delay']==1 and gateway['nominal_delay']==.5
    request_check(r,'gateway',s['hash']);reveal_check(r,'gateway')
    assert r.minute==1 and r.events['check-result:gateway'].event_time==1
    r=Replay();request_check(r,'water',r.history[-1]['hash'])
    for _ in range(3):r.step()
    reveal_check(r,'water');event=r.events['check-result:water']
    assert event.event_time==1 and event.arrival_time==4

def test_flagship_api_snapshot_contract_and_receipt_export():
    from fastapi.testclient import TestClient
    from sentinel.api import app
    with TestClient(app) as client:
        s=client.post('/api/reset',json={}).json();h=s['current']['hash']
        ranking=client.get('/api/lab/prove').json();assert len(ranking['checks'])==6
        assert client.post('/api/lab/prove/request',json={'candidate_id':'unknown','snapshot_hash':h}).status_code==409
        assert client.post('/api/lab/cascade',json={'snapshot_hash':h,'crews':-1}).status_code==422
        assert client.post('/api/lab/cascade',json={'snapshot_hash':h,'crews':0,'pumps':0,'budget':0}).json()['selected_plan']=='monitor'
        ticket=client.post('/api/lab/prove/request',json={'candidate_id':'water','snapshot_hash':h}).json()
        after=client.post('/api/lab/prove/reveal',json={'candidate_id':'water'}).json()
        assert after['state']['current']['minute']==1
        blackout=client.post('/api/lab/lifelines/blackout',json={'seed':26,'snapshot_hash':after['state']['current']['hash']}).json()
        assert blackout['result']['disconnected_count']==6 and blackout['state']['current']['minute']==2
        export=client.get('/api/receipts').json()
        assert export['valid'] and {a['module'] for a in export['analyses']}=={'prove','cascade','lifelines'}
        assert client.post('/api/lab/cascade',json={'snapshot_hash':h}).status_code==409

def test_weather_optional_extensions_validate_without_fabrication():
    from sentinel.weather import validate_weather
    # Minimal original contract remains accepted; optional new fields stay unavailable.
    data={'timezone':'Asia/Kolkata','current_units':{},'hourly_units':{},'current':{'time':'2026-10-26T12:00','temperature_2m':27,'relative_humidity_2m':70,'precipitation':0,'rain':0,'weather_code':0,'wind_speed_10m':10},'hourly':{'time':['2026-10-26T12:00'],**{key:[0] for key in ('temperature_2m','relative_humidity_2m','precipitation_probability','precipitation','rain','wind_speed_10m')}}}
    result=validate_weather(data);assert result['current']['surface_pressure'] is None and result['daily'] is None
    data['daily']={'time':['2026-10-26'],'temperature_2m_max':[30],'temperature_2m_min':[20],'precipitation_sum':[0],'wind_gusts_10m_max':[]}
    with pytest.raises(ValidationError):validate_weather(data)

def test_informative_evidence_can_leave_action_unchanged_and_parallel_can_win():
    c={'id':'strong','label':'Strong independent instrument','positive':[.01,.01,.01,.99],'delay':1,'cost':.1,'inconclusive':0}
    assert value_of_information([.6,.05,.05,.3],[],[c])['recommendation']=='Verify while preparing'
    p=[.005,.005,.01,.98]
    result=value_of_information(p,[],[{**c,'positive':[.4,.4,.5,.6]}])['checks'][0]
    assert len({o['optimal_action'] for o in result['outcomes']})==1
    assert not np.allclose(result['outcomes'][0]['posterior'],p)
    costly=value_of_information([.6,.05,.05,.3],[],[{**c,'cost':10000}])
    assert costly['recommendation']=='Prepare now' and costly['selected_check'] is None

def test_complete_shared_scenario_with_check_blackout_and_receipt_integrity():
    r=Replay('flood',26)
    for _ in range(3):r.step()
    request_check(r,'water',r.history[-1]['hash']);reveal_check(r,'water')
    result=apply_blackout(r,26,r.history[-1]['hash']);assert result['state']['current']['minute']==5
    while r.minute<18:r.step()
    assert r.store.verify(r.run_id) and len(r.history)==19
    assert all(sum(s['probabilities'].values())==pytest.approx(1) for s in r.history)
    assert r.events['check-result:water'].payload['outcome'] in ('positive','negative','inconclusive')
    assert len(r.disabled_streams)==6

def test_blackout_blocks_manual_reports_from_disconnected_streams():
    r=Replay();apply_blackout(r,26,r.history[-1]['hash']);n=r.minute+1
    with pytest.raises(ValueError,match='disconnected'):
        r.queue(Event(id='forged-normal',source_id=sorted(r.disabled_streams)[0],kind='water_normal',zone_id='river',event_time=n,arrival_time=n))

def test_no_value_recommendation_preserves_current_response_and_feasible_strategies():
    r=Replay();s=copy.deepcopy(r.history[-1]);s['probabilities']=dict(zip(C['hypotheses'],[.001,.001,.001,.997]));s['decision']['action']='ESCALATE'
    result=rank(s,used=[c['id'] for c in CATALOG])
    assert result['recommendation']=='ESCALATE NOW' and result['selected_check'] is None
    assert next(strategy for strategy in result['strategies'] if strategy['id']=='verify_first')['expected_cost'] is None
