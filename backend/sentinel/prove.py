"""Decision-value ranking and executable, idempotent simulated checks."""
import math
import random
from hashlib import sha256
import numpy as np
from .settings import CONFIG as C
from .verification_catalog import CATALOG, BY_ID, effective_check
from .voi import value_of_information
from .decision import cost_matrix
from .models import Event


def rank(snapshot,duration=18,used=()):
    p=np.array([snapshot['probabilities'][h] for h in C['hypotheses']])
    scores={s['source']:s['reliability'] for s in snapshot['sources']}
    checks=[effective_check(c,scores.get(c['source'],.8)) for c in CATALOG]
    result=value_of_information(p,snapshot['deadlines'],checks)
    matrix=cost_matrix(snapshot['deadlines']); regret=matrix-matrix.min(axis=0)
    current=C['actions'].index(snapshot['decision']['action'])
    for c in result['checks']:
        unavailable=[]
        if c['id'] in used:unavailable.append('Already requested in this replay')
        if snapshot['minute']+math.ceil(c['delay'])>duration:unavailable.append('Not enough replay time to return and apply the observation')
        if c['gateway'] and any(g['gateway']==c['gateway'] and g['status'] in ('offline','unconfirmed loss') for g in snapshot['gateways']):
            unavailable.append('Dependent gateway is unavailable or has unconfirmed loss; use an independent instrument')
        if c['id']=='camera' and any(e['kind']=='power_loss' for e in snapshot['supporting_evidence']):unavailable.append('Camera power is unconfirmed after reported power loss')
        c['available']=not unavailable;c['availability_reason']='; '.join(unavailable) or c['authorization']
        c['decision_change_probability']=sum(o['probability'] for o in c['outcomes'] if o['optimal_action']!=C['actions'][current])
        c['expected_regret_now']=float(regret[current]@p)
        c['worst_case_regret_now']=float(regret[current].max())
        c['expected_regret_after']=sum(o['probability']*float(np.min(regret@np.array(o['posterior']))) for o in c['outcomes'])
        c['best_net_value']=max(c['net_value'],c['parallel_net_value'])
    result['checks'].sort(key=lambda c:(not c['available'],-c['best_net_value'],c['id']))
    feasible=[c for c in result['checks'] if c['available']]
    best=feasible[0] if feasible else None
    result['strategies']=value_of_information(p,snapshot['deadlines'],feasible)['strategies']
    result['selected_check']=best['id'] if best and best['best_net_value']>0 else None
    result['best_available']=best['id'] if best else None
    result['recommendation']=('PREPARE WHILE VERIFYING' if best['parallel_net_value']>best['net_value'] else 'VERIFY FIRST') if result['selected_check'] else ((C['actions'][current]+' NOW') if current>0 else 'NO ADDITIONAL CHECK')
    result['ranking_reason']=f"{best['label']} has the greatest modeled net decision value among feasible checks ({best['best_net_value']:.3f} loss units)." if best else 'No feasible checks at this snapshot.'
    if best and best['best_net_value']<=0:result['ranking_reason']+=' All feasible checks cost more than their expected decision benefit; running one remains an explicit experiment.'
    return {**result,'module_version':'phase4-1','outcome_assumptions':'Hypothetical outcomes condition on the current posterior, holding other evidence and state fixed. Actual replay application includes its state transition, freshness decay and other reports arriving that minute. Nominal sub-minute responses are rounded up to the one-minute replay grid.','minute':snapshot['minute'],'snapshot_hash':snapshot['hash'],'current_action':C['actions'][current],'probabilities':snapshot['probabilities']}


def sample_outcome(episode,seed,candidate_id,issued_minute,response_minute):
    """Sampler only: physical facts realized by response time, never eventual class.
    Ranking and filtering never receive this Episode. Identical physical prefixes yield identical samples.
    """
    realized=[node for node,t in episode.failures if t<=response_minute]
    events=[e for e in episode.events if e.event_time<=response_minute and e.arrival_time<=response_minute]
    gateway_down=False
    for e in sorted(events,key=lambda e:(e.arrival_time,e.id)):
        if e.kind in ('gateway_down','gateway_up'):gateway_down=e.kind=='gateway_down'
    state=3 if len(realized)>=2 else 2 if realized else 1 if gateway_down else 0
    check=effective_check(BY_ID[candidate_id])
    rng=random.Random(int(sha256(f'{seed}:{candidate_id}:{issued_minute}:{response_minute}'.encode()).hexdigest()[:16],16))
    x=rng.random();u=check['inconclusive'];positive=(1-u)*check['positive'][state]
    return 'inconclusive' if x<u else 'positive' if x<u+positive else 'negative'


def request_check(replay,candidate_id,snapshot_hash):
    with replay.lock:
        if replay.running:raise ValueError('Pause playback before requesting a check')
        snapshot=replay.history[-1]
        if snapshot['hash']!=snapshot_hash:raise ValueError('Snapshot changed; review the refreshed ranking')
        if candidate_id not in BY_ID:raise ValueError('Unknown candidate')
        existing=next((a for a in replay.store.analyses(replay.run_id) if a.get('module')=='prove' and a.get('candidate_id')==candidate_id),None)
        if existing:return existing
        ranking=rank(snapshot,replay.episode.duration)
        c=next(c for c in ranking['checks'] if c['id']==candidate_id)
        if not c['available']:raise ValueError(c['availability_reason'])
        return replay.store.save_analysis(replay.run_id,'check:'+candidate_id,{'module':'prove','candidate_id':candidate_id,'snapshot_hash':snapshot_hash,'minute':replay.minute,'due_minute':replay.minute+math.ceil(c['delay']),'status':'pending','ranking':ranking,'assumptions':'Synthetic instrument. Outcome sampled only from physical facts realized by response time; not eventual episode class.'})


def reveal_check(replay,candidate_id):
    with replay.lock:
        ticket=next((a for a in replay.store.analyses(replay.run_id) if a.get('module')=='prove' and a.get('candidate_id')==candidate_id),None)
        if not ticket:raise ValueError('Request this check first')
        if ticket['status']=='applied':return {'ticket':ticket,'state':replay.state()}
        if replay.running:raise ValueError('Pause playback before applying the check')
        if replay.minute+1<ticket['due_minute']:raise ValueError('Response is not available yet; advance the shared replay')
        if replay.minute>=replay.episode.duration:raise ValueError('Replay ended; reset to run another experiment')
        outcome=sample_outcome(replay.episode,replay.seed,candidate_id,ticket['minute'],ticket['due_minute'])
        c=BY_ID[candidate_id];n=replay.minute+1;before=replay.history[-1]
        event=Event(id='check-result:'+candidate_id,source_id=c['source'],kind='verification_result',zone_id='river',event_time=ticket['due_minute'],arrival_time=n,reliability=c['reliability'],payload={'candidate_id':candidate_id,'outcome':outcome,'response_minute':ticket['due_minute']})
        replay.queue(event);state=replay.step();after=state['current']
        record=replay.store.save_analysis(replay.run_id,'check:'+candidate_id,{**{k:v for k,v in ticket.items() if k!='analysis_hash'},'status':'applied','outcome':outcome,'event_id':event.id,'before':{'minute':before['minute'],'probabilities':before['probabilities'],'action':before['decision']['action'],'hash':before['hash']},'after':{'minute':after['minute'],'probabilities':after['probabilities'],'action':after['decision']['action'],'hash':after['hash']},'note':'Applied through the existing event queue and filter. Other observations arriving on this minute are included; the difference is not attributed solely to this check.'})
        return {'ticket':record,'state':state}
