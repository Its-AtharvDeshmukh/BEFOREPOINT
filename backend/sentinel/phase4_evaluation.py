"""Held-out synthetic experiments; metrics are not field validation."""
import numpy as np
from .evaluation import HELD_OUT_SEEDS
from .simulator import SCENARIOS
from .replay import Replay
from .settings import CONFIG as C
from .prove import rank,request_check,reveal_check
from .interventions import evaluate_interventions
from .lifelines import inspect_lifelines,apply_blackout

def trajectory_metrics(r,fee=0):
    truth=C['hypotheses'].index(r.episode.truth);y=int(truth==3)
    actions=[C['actions'].index(s['decision']['action']) for s in r.history]
    alerted=[s['minute'] for s in r.history if C['actions'].index(s['decision']['action'])>=2]
    return {'brier':float(np.mean([(s['probabilities']['CASCADING_CRISIS']-y)**2 for s in r.history])),
        'episode_loss':float(sum(C['costs'][a][truth] for a in actions)+fee),'acquisition_cost':fee,
        'false_alarm':int(not y and bool(alerted)),'negative':int(not y),'missed':int(y and not alerted),'positive':y,
        'detection_delay':max(0,min(alerted)-r.episode.crisis_onset) if y and alerted else None,
        'detection_lead_time':r.episode.crisis_onset-min(alerted) if y and alerted else None,
        'action_changes':sum(a!=b for a,b in zip(actions,actions[1:]))}

def evaluate_phase4():
    rows={name:[] for name in ('unchanged_engine','original_check_policy','prove_me_wrong','blackout_60_percent')};cascade=[];spatial=[];checks={name:0 for name in rows};details=[]
    for shifted in (False,True):
      for seed in HELD_OUT_SEEDS:
       for scenario in SCENARIOS:
        runs={name:Replay(scenario,seed,shifted=shifted) for name in rows};fees={name:0 for name in rows};unchanged_fees={name:0 for name in rows}
        for r in runs.values():
            for _ in range(4):r.step()
        for name in ('original_check_policy','prove_me_wrong'):
            r=runs[name];ranking=rank(r.history[-1]);original=r.history[-1]['voi']
            candidate=original['selected_check'] if name=='original_check_policy' else ranking['selected_check']
            feasible=next((c for c in ranking['checks'] if c['id']==candidate and c['available']),None)
            if feasible:
                action_before=r.history[-1]['decision']['action'];t=request_check(r,candidate,r.history[-1]['hash'])
                while r.minute+1<t['due_minute']:r.step()
                reveal_check(r,candidate);fees[name]=feasible['cost'];checks[name]+=1
                if r.history[-1]['decision']['action']==action_before:unchanged_fees[name]=feasible['cost']
        b=runs['blackout_60_percent'];before=inspect_lifelines(b);after=apply_blackout(b,seed,b.history[-1]['hash'])['result']
        # A deliberately small, independently declared synthetic fragility truth: single access,
        # no backup power, and >=15-minute essential service travel. Three aggregate cells only.
        truth={z['id'] for z in before['zones'] if z['routes']==0 and not z['backup_power'] and z['facility_minutes']>=15}
        predicted={z['id'] for z in after['zones'] if z['structural_score']>=.6}
        spatial.append(len(truth&predicted)/len(truth|predicted) if truth|predicted else 1.)
        snap=runs['unchanged_engine'].history[-1]
        planning=evaluate_interventions(snap,seed=seed,samples=256)
        testing=evaluate_interventions(snap,seed=seed+99991,samples=512)
        chosen=next(p for p in testing['plans'] if p['id']==planning['selected_plan'])
        cascade.append({'scenario':scenario,'seed':seed,'shifted':shifted,'plan':chosen['id'],'feasible':chosen['feasible'],'heldout_net_benefit':chosen.get('net_benefit',0),'interval':chosen.get('benefit_interval')})
        for name,r in runs.items():
            while r.minute<r.episode.duration:r.step()
            rows[name].append({**trajectory_metrics(r,fees[name]),'check_fee_when_action_unchanged':unchanged_fees[name]})
    summary={}
    for name,values in rows.items():
        delays=[v['detection_delay'] for v in values if v['detection_delay'] is not None]
        leads=[v['detection_lead_time'] for v in values if v['detection_lead_time'] is not None]
        summary[name]={'episodes':len(values),'checks_requested':checks[name],**{k:float(np.mean([v[k] for v in values])) for k in ('brier','episode_loss','acquisition_cost','check_fee_when_action_unchanged','action_changes')},'false_alarm_rate':sum(v['false_alarm'] for v in values)/sum(v['negative'] for v in values),'missed_crisis_rate':sum(v['missed'] for v in values)/sum(v['positive'] for v in values),'mean_detection_delay':float(np.mean(delays)) if delays else None,'mean_detection_lead_time':float(np.mean(leads)) if leads else None}
    return {'seeds':list(HELD_OUT_SEEDS),'decision_minute':4,'policies':summary,'paired_prove_loss_reduction':float(np.mean([a['episode_loss']-b['episode_loss'] for a,b in zip(rows['original_check_policy'],rows['prove_me_wrong'])])),
        'cascade':{'trials':len(cascade),'resource_feasibility_rate':float(np.mean([c['feasible'] for c in cascade])),'heldout_mean_net_benefit':float(np.mean([c['heldout_net_benefit'] for c in cascade])),'positive_benefit_fraction':float(np.mean([c['heldout_net_benefit']>0 for c in cascade])),'details':cascade},
        'spatial':{'cells':3,'mean_structural_iou_after_blackout':float(np.mean(spatial)),'scope':'Toy aggregate-zone agreement with a manually declared fragility truth; not a learned or geographically representative spatial benchmark.'},
        'notes':['72 held-out scenario/seed/regime combinations per policy. Exactly one optional check chosen at minute 4; response applied through the same replay filter.','Original policy uses existing three-check VOI choice when currently feasible; new policy ranks six reliability-adjusted catalog checks. Both use the same physical-prefix sampler and event application.','Episode loss sums base action/hypothesis costs over 19 replay snapshots plus one acquisition fee; it does not double-count modeled delay penalties.','The verification sampler uses physical facts realized by response time, never eventual outcome labels. Evaluation labels classify the whole episode, so early benign readings can be misleading about eventual crises.','Cascade plans are selected with one random seed and evaluated with an independent seed under the same declared assumptions. This tests Monte Carlo selection, not real intervention effectiveness.','IoU is a three-cell structural sanity check. Blackout preserves declared structure by design; perfect structural agreement is not proof of hazard detection or privacy guarantees.','Check fee when action stays unchanged is reported as a descriptive cost, not proof the check was unnecessary; future value and hysteresis can matter.','No parameter tuning on these held-out seeds. No automatic claim of accuracy improvement.']}
