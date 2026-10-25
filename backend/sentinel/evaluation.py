"""Frozen synthetic benchmark. No training/tuning uses these test labels."""
import numpy as np
import random
from .voi import counterfactual_check
from .decision import risks, cost_matrix
from .replay import Replay
from .inference import BayesianFilter
from .settings import CONFIG as C
from .simulator import SCENARIOS

HELD_OUT_SEEDS=(104729,130363,155921)


def twin_test(seed=26):
    a,b=Replay('twin_crisis',seed),Replay('twin_benign',seed)
    for _ in range(18): a.step(); b.step()
    prefix_equal=all(x['probabilities']==y['probabilities'] and x['decision']==y['decision'] and x['forecasts']==y['forecasts'] for x,y in zip(a.history[:8],b.history[:8]))
    return {'identical_through_minute':7,'prefix_equal':prefix_equal,
            'diverges_after_evidence':a.history[8]['probabilities']!=b.history[8]['probabilities'],
            'a':a.state()['history'],'b':b.state()['history']}


def evaluate():
    names=['Bayesian','Fixed threshold','Event count','No gateway grouping','No reliability weights']
    accum={name:[] for name in names}
    policy_trials=[]
    # All scenarios, three held-out seeds, original and shifted weather regimes.
    for shifted in (False,True):
        for seed in HELD_OUT_SEEDS:
            for scenario in SCENARIOS:
                runs=[Replay(scenario,seed,shifted=shifted,engine=engine) for engine in
                      (BayesianFilter(),BayesianFilter(gateway_aware=False),BayesianFilter(weighting=False))]
                for run in runs:
                    for _ in range(18): run.step()
                main=runs[0]
                policy_trials.append(score_check_policy(main,seed,scenario,shifted))
                y=int(main.episode.truth=='CASCADING_CRISIS')
                truth_index=C['hypotheses'].index(main.episode.truth)
                for name in names:
                    trajectory=[]; forecast_scores=[]; voi_values=[]; requests=0
                    run=runs[0]
                    if name=='No gateway grouping': run=runs[1]
                    if name=='No reliability weights': run=runs[2]
                    for record in run.history:
                        if name in ('Fixed threshold','Event count'):
                            visible=record['supporting_evidence']
                            recent=[e for e in visible if e['arrival_time']>=record['minute']-3]
                            count=sum(e['kind'] in ('water_high','calls_surge','citizen_yes','power_loss','road_closed') for e in recent)
                            if name=='Fixed threshold':
                                signal=any(e['kind'] in ('water_high','power_loss','road_closed') for e in recent)
                                q=.8 if signal else .05
                            else: q=min(.98,.05+.12*count)
                            p=np.array([(1-q)*.6,(1-q)*.2,(1-q)*.2,q])
                            action=int(np.argmin(np.array(C['costs'])@p))
                        else:
                            q=record['probabilities']['CASCADING_CRISIS']
                            action=C['actions'].index(record['decision']['action'])
                        trajectory.append((record['minute'],q,action))
                        for f in record['forecasts']:
                            occurred=any(node==f['component'] and f['window'][0]<=t<=f['window'][1] for node,t in run.episode.failures)
                            forecast_scores.append((f['probability']-int(occurred))**2)
                        if record['voi']['selected_check']:
                            choice=next(c for c in record['voi']['checks'] if c['id']==record['voi']['selected_check'])
                            voi_values.append(max(choice['net_value'],choice['parallel_net_value'])); requests+=1
                    alerted=[t for t,q,a in trajectory if a>=2]
                    onset=run.episode.crisis_onset
                    delay=max(0,min(alerted)-onset) if y and alerted else (run.episode.duration-onset+1 if y else None)
                    accum[name].append({'pairs':[(q,y) for _,q,_ in trajectory], 'brier':float(np.mean([(q-y)**2 for _,q,_ in trajectory])),
                        'false_alarm':int(bool(alerted) and not y), 'negative':1-y,
                        'delay':delay,'cost':float(np.mean([C['costs'][a][truth_index] for _,_,a in trajectory])),
                        'changes':sum(trajectory[i][2]!=trajectory[i-1][2] for i in range(1,len(trajectory))),
                        'forecast_brier':float(np.mean(forecast_scores)) if forecast_scores and name not in ('Fixed threshold','Event count') else None,
                        'voi':float(np.mean(voi_values)) if voi_values else 0,'requests':requests,
                        'missing':scenario in ('missing_streams','silent_zone'), 'shifted':shifted})
    rows=[]
    for name,samples in accum.items():
        rows.append({'model':name,'episodes':len(samples),'brier_score':float(np.mean([s['brier'] for s in samples])),
            'false_alarm_rate':sum(s['false_alarm'] for s in samples)/sum(s['negative'] for s in samples),
            'mean_detection_delay':float(np.mean([s['delay'] for s in samples if s['delay'] is not None])),
            'mean_decision_cost':float(np.mean([s['cost'] for s in samples])),
            'mean_action_changes':float(np.mean([s['changes'] for s in samples])),
            'next_event_brier':float(np.mean([s['forecast_brier'] for s in samples if s['forecast_brier'] is not None])) if name not in ('Fixed threshold','Event count') else None,
            'model_expected_check_net_value':float(np.mean([s['voi'] for s in samples])) if name not in ('Fixed threshold','Event count') else None,
            'mean_evidence_requests':float(np.mean([s['requests'] for s in samples])) if name not in ('Fixed threshold','Event count') else None,
            'missing_stream_brier':float(np.mean([s['brier'] for s in samples if s['missing']])),
            'shifted_brier':float(np.mean([s['brier'] for s in samples if s['shifted']]))})
    return {'seeds':HELD_OUT_SEEDS,'rows':rows,'twin':twin_test()['prefix_equal'],
        'calibration':{name:calibration_bins([pair for sample in samples for pair in sample['pairs']]) for name,samples in accum.items()},
        'verification_policy': {'trials':len(policy_trials),
            'checks_requested':sum(t['requested'] for t in policy_trials),
            'mean_no_check_loss':float(np.mean([t['no_check_loss'] for t in policy_trials])),
            'mean_policy_loss':float(np.mean([t['policy_loss'] for t in policy_trials])),
            'realized_mean_benefit':float(np.mean([t['no_check_loss']-t['policy_loss'] for t in policy_trials])),
            'scope':'One-shot paired synthetic check at minute 7. Uses withheld labels only to sample outcomes and score realized loss; no intervention changes infrastructure.'},
        'notes':['Synthetic benchmark, not field validation. Frozen illustrative parameters.',
                 'Crisis Brier target is eventual episode label; early uncertainty is expected.',
                 'False alarms: any ALERT/ESCALATE in a non-cascade episode, including isolated incidents.',
                 'Detection delay measured from onset at minute 10; missed cases penalized through end+1.',
                 'Forecast Brier is conditional on emitted candidates, not all-node calibration.',
                 'Per-minute VOI values are model expectations. Separate verification_policy reports one-shot sampled counterfactual check costs and realized decision losses.',
                 'Baselines do not emit infrastructure forecasts; their forecast scores are null.']}


def score_check_policy(run, seed, scenario, shifted):
    """Evaluator alone samples withheld truth. Policy sees p and the sampled outcome."""
    record=run.history[7]
    p=np.array([record['probabilities'][h] for h in C['hypotheses']])
    truth=C['hypotheses'].index(run.episode.truth)
    base_matrix=cost_matrix(record['deadlines'])
    base_action=int(np.argmin(base_matrix @ p))
    base_loss=float(base_matrix[base_action,truth])
    selected=record['voi']['selected_check']
    if not selected:
        return {'requested':False,'no_check_loss':base_loss,'policy_loss':base_loss}
    check=next(c for c in record['voi']['checks'] if c['id']==selected)
    # Stable seed mixing independent of Python hash randomization.
    rng=random.Random(seed*1000+list(SCENARIOS).index(scenario)*10+int(shifted)+7919)
    roll=rng.random()
    u=check['inconclusive']
    positive=(1-u)*check['positive'][truth]
    outcome='positive' if roll<positive else ('negative' if roll<1-u else 'inconclusive')
    posterior=counterfactual_check(p,check,outcome)
    action=int(np.argmin(risks(posterior,record['deadlines'],check['delay']*(.5 if record['voi']['recommendation']=='Verify while preparing' else 1.))))
    parallel=record['voi']['recommendation']=='Verify while preparing'
    factor=.5 if parallel else 1.
    delayed_matrix=cost_matrix(record['deadlines'],check['delay']*factor)
    actual_delay=check['delay']*C['delay_harm_per_minute'][truth]
    total=float(delayed_matrix[action,truth])+check['cost']+factor*actual_delay+(.6 if parallel else 0.)
    return {'requested':True,'outcome':outcome,'no_check_loss':base_loss,'policy_loss':total}


def calibration_bins(pairs):
    bins=[]
    for i in range(10):
        chosen=[(p,y) for p,y in pairs if i/10<=p and (p<(i+1)/10 or (i==9 and p<=1))]
        if chosen:
            bins.append({'bin_start':i/10,'count':len(chosen),
                'mean_predicted':float(np.mean([p for p,y in chosen])),
                'observed_frequency':float(np.mean([y for p,y in chosen]))})
    return bins
