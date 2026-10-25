import copy
import inspect
import numpy as np
import pytest
from pydantic import ValidationError
from sentinel.models import Event
from sentinel.inference import BayesianFilter
from sentinel.replay import Replay
from sentinel.receipts import ReceiptStore
from sentinel.simulator import generate,SCENARIOS
from sentinel.settings import CONFIG as C
from sentinel.decision import decide,risks
from sentinel.graph import forecast,deadlines
from sentinel.voi import value_of_information
from sentinel.reliability import source_scores
from sentinel.evaluation import twin_test


def event(id='e',kind='water_high',t=1,arrival=None,source='water',gateway=None,zone='river',**kwargs):
    return Event(id=id,source_id=source,kind=kind,zone_id=zone,event_time=t,
                 arrival_time=t if arrival is None else arrival,gateway=gateway,**kwargs)

@pytest.mark.parametrize('scenario',list(SCENARIOS))
def test_all_scenarios_normalize_and_receipts(scenario):
    r=Replay(scenario)
    for _ in range(18):
        s=r.step()['current']
        p=list(s['probabilities'].values())
        assert sum(p)==pytest.approx(1,abs=1e-12)
        assert all(0<=v<=1 for v in p)
        assert s['decision']['action'] in C['actions']
        assert all(e.arrival_time<=r.minute and e.event_time<=r.minute for e in r.events.values())
    assert r.store.verify(r.run_id)
    assert len(r.history)==19

@pytest.mark.parametrize('seed',[1,26,104729])
def test_twins_no_leak_and_revision(seed):
    result=twin_test(seed)
    assert result['prefix_equal'] and result['diverges_after_evidence']
    assert result['a'][-1]['probabilities']['CASCADING_CRISIS']>result['b'][-1]['probabilities']['CASCADING_CRISIS']
    a,b=generate('twin_crisis',seed),generate('twin_benign',seed)
    assert [e for e in a.events if e.arrival_time<=7]==[e for e in b.events if e.arrival_time<=7]


def test_inference_has_no_truth_or_scenario_input():
    assert list(inspect.signature(BayesianFilter.estimate).parameters)==['self','events','minute']
    events=list(generate().events)
    prefix=[e for e in events if e.arrival_time<=7]
    np.testing.assert_array_equal(BayesianFilter().estimate(prefix,7)[0],BayesianFilter().estimate(events,7)[0])


def test_duplicates_are_idempotent_conflicts_rejected():
    r=Replay();r.step()
    e=event(id='manual')
    assert r.ingest(e)
    assert not r.ingest(e)
    with pytest.raises(ValueError):r.ingest(e.model_copy(update={'kind':'water_normal'}))


def test_shared_gateway_one_effective_observation():
    one=[event(kind='stream_missing',gateway='g')]
    many=[event(id=f'e{i}',kind='stream_missing',gateway='g',source=f's{i}') for i in range(100)]
    np.testing.assert_allclose(BayesianFilter().estimate(one,1)[0],BayesianFilter().estimate(many,1)[0],atol=1e-12)
    assert BayesianFilter().estimate(many,1)[0][1]>.15


def test_repeated_citizen_reports_across_minutes_capped():
    one=[event(kind='citizen_yes',source='citizen:one')]
    many=[*one,*[event(id=str(i),kind='citizen_yes',source=f'citizen:{i}',t=i+2) for i in range(15)]]
    np.testing.assert_allclose(BayesianFilter().estimate(one,18)[0],BayesianFilter().estimate(many,18)[0])


def test_delayed_and_future_event_isolation():
    e=event(t=1,arrival=5)
    engine=BayesianFilter()
    np.testing.assert_array_equal(engine.estimate([e],4)[0],engine.estimate([],4)[0])
    assert engine.estimate([e],5)[0][3]>engine.estimate([],5)[0][3]
    with pytest.raises(ValueError):Replay().ingest(e)


def test_retraction_removes_evidence_without_rewriting_old_receipt():
    engine=BayesianFilter()
    report=event(t=1)
    retract=event(id='r',kind='retraction',t=3,source='operator',retracts='e')
    np.testing.assert_array_equal(engine.estimate([report,retract],3)[0],engine.estimate([],3)[0])
    assert engine.estimate([report,retract],2)[0][3]>engine.estimate([],2)[0][3]
    r=Replay('normal_rain');r.step();old=copy.deepcopy(r.history[-1])
    r.queue(event(id='ret',kind='retraction',t=2,source='operator',retracts=r.history[-1]['visible_event_ids'][0]))
    r.step()
    assert r.history[1]==old
    assert r.store.verify(r.run_id)


def test_reliability_updates_only_adjudicated_source():
    report=event()
    assert source_scores([report])=={}
    adjudication=event(id='v',kind='verification',source='operator',t=2,retracts='e',payload={'correct':False})
    scores=source_scores([report,adjudication])
    assert scores['water']==pytest.approx(8/11)
    repeat=adjudication.model_copy(update={'id':'v2'})
    assert source_scores([report,adjudication,repeat])==scores


def test_cost_matrix_and_hysteresis():
    for index in range(4):
        p=np.eye(4)[index]
        assert decide(p)['action']==C['actions'][int(np.argmin(np.array(C['costs'])[:,index]))]
    assert decide([1,0,0,0],'ALERT',0)['held_by_hysteresis']
    assert decide([1,0,0,0],'ALERT',2)['action']=='WATCH'


def test_forecasts_specific_graph_events_and_deadlines():
    forecasts=forecast([event()],1,[.1,.1,.2,.6])
    assert len(forecasts)==3
    assert all(f['component'] in C['nodes'] and f['component'] not in C['hypotheses'] for f in forecasts)
    assert all(f['window'][0]>=1 and f['window'][1]>=f['window'][0] for f in forecasts)
    for d in deadlines(forecasts,1):
        f=next(f for f in forecasts if f['component']==d['failure'])
        failure=np.linspace(*f['window'],81)
        response=np.linspace(*d['response_minutes'],81)
        efficacy=np.mean(d['latest_start']+response[None,:]<=failure[:,None]+.01)
        assert efficacy>=d['target_probability']-.015


def test_voi_bayes_expectation_and_no_free_information():
    p=np.array([.35,.25,.25,.15])
    v=value_of_information(p,[])
    for c in v['checks']:
        assert sum(o['probability'] for o in c['outcomes'])==pytest.approx(1)
        expected=sum(o['probability']*min(risks(o['posterior'])) for o in c['outcomes'])
        assert c['evsi']==pytest.approx(v['baseline_risk']-expected)
        assert c['net_value']==pytest.approx(c['evsi']-c['cost']-c['delay_harm']-c['deadline_penalty'])
        assert c['net_value']<=c['evsi']
    assert value_of_information([1,0,0,0],[])['selected_check'] is None


def test_zone_not_safe_when_silent():
    r=Replay('silent_zone')
    for _ in range(5):r.step()
    river=next(z for z in r.history[-1]['zones'] if z['id']=='river')
    assert river['evidence_status']=='missing'
    assert river['consequence_score']>.8


def test_receipt_tamper_detected_and_persisted(tmp_path):
    path=str(tmp_path/'audit.sqlite3');store=ReceiptStore(path);r=Replay(store=store)
    assert ReceiptStore(path).verify(r.run_id)
    store.db.execute('UPDATE receipts SET body=replace(body,\'WATCH\',\'BOGUS\') WHERE run=?',(r.run_id,));store.db.commit()
    assert not store.verify(r.run_id)


def test_seeded_replay_reproducible():
    a,b=Replay('flood',73),Replay('flood',73)
    for _ in range(18):a.step();b.step()
    assert [r['hash'] for r in a.history]==[r['hash'] for r in b.history]
    assert generate('flood',73).events!=generate('flood',74).events

@pytest.mark.parametrize('change',[{'arrival_time':0},{'reliability':1.1},{'kind':'invented'},{'zone_id':'unknown'}])
def test_event_validation(change):
    with pytest.raises(ValidationError):Event(**{**event().model_dump(),**change})


def test_check_outcome_updates_without_hidden_state():
    from sentinel.voi import counterfactual_check
    p=np.array([.4,.2,.2,.2])
    check=C['checks'][0]
    posterior=counterfactual_check(p,check,'positive')
    assert posterior.sum()==pytest.approx(1)
    assert posterior[3]>p[3]
    np.testing.assert_allclose(counterfactual_check(p,check,'inconclusive'),p)


def test_counterfactual_policy_is_repeatable_and_scores_costs():
    from sentinel.evaluation import score_check_policy
    r=Replay('twin_crisis')
    for _ in range(7):r.step()
    result=score_check_policy(r,26,'twin_crisis',False)
    assert result==score_check_policy(r,26,'twin_crisis',False)
    assert result['policy_loss']>=0
    from sentinel.decision import cost_matrix
    matrix=cost_matrix(r.history[7]['deadlines'])
    p=np.array([r.history[7]['probabilities'][h] for h in C['hypotheses']])
    assert result['no_check_loss']==pytest.approx(matrix[int(np.argmin(matrix@p)),3])


def test_config_hash_is_recorded():
    from sentinel.receipts import digest
    assert Replay().history[0]['configuration_hash']==digest(C)
