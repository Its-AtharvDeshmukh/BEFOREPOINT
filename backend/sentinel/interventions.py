"""Small paired Monte Carlo laboratory on the existing configured DAG.
No episode, future events or withheld labels are inputs. Harm weights are assumptions.
"""
from itertools import combinations
import numpy as np
from .settings import CONFIG as C
from .models import Event
from .graph import observed_seeds

HARM={'rainfall':0,'drainage':4,'underpass':10,'junction':8,'substation':15,'gateway':7,'hospital':45,'dispatch':30,'alternate_road':12}
INTERVENTIONS=[
 {'id':'pump','label':'Stage backup drainage pump','target':'drainage','edge':['drainage','underpass'],'crews':1,'pumps':1,'cost':5,'preparation':[2,4],'reduction':.65,'side_effect':'Consumes the only pump; does not repair a road already disrupted.','assumption':'Reduces conditional drainage-to-underpass transmission by 65% after preparation.'},
 {'id':'access','label':'Prepare emergency access','target':'junction','edge':['junction','hospital'],'crews':1,'pumps':0,'cost':3,'preparation':[1,3],'reduction':.6,'side_effect':'Adds a 15% conditional chance of alternate-road congestion if junction disruption occurs after preparation.','assumption':'Reduces junction-to-hospital transmission by 60%; does not remove other paths.'},
 {'id':'backup','label':'Stage backup communications','target':'substation','edge':['substation','gateway'],'crews':1,'pumps':0,'cost':4,'preparation':[2,5],'reduction':.7,'side_effect':'Occupies one crew for preparation; no protection of the power supply itself.','assumption':'Reduces substation-to-gateway transmission by 70% after preparation.'},
 {'id':'inspect','label':'Inspect pump equipment','target':'drainage','edge':None,'crews':1,'pumps':0,'cost':1,'preparation':[1,2],'reduction':0,'side_effect':'Costs time and one crew. Inspection alone has no modeled preventive effect.','assumption':'No automatic repair or unmodeled causal benefit.'}]

def evaluate_interventions(snapshot,seed=26,crews=2,pumps=1,budget=9,start_delay=0,samples=512,dependency_scale=1):
    if not 0<=crews<=4 or not 0<=pumps<=2 or not 0<=budget<=50 or not 0<=start_delay<=24 or not 64<=samples<=2048 or not .5<=dependency_scale<=1.5:raise ValueError('Experiment parameters outside allowed limits')
    p=[snapshot['probabilities'][h] for h in C['hypotheses']]
    events=[Event.model_validate(e) for e in snapshot['supporting_evidence']]
    scores={s['source']:s['reliability'] for s in snapshot['sources']}
    seeds=observed_seeds(events,snapshot['minute'],p,scores)
    rng=np.random.default_rng(seed);nodes=C['nodes'];edges=C['edges'];n=samples;horizon=24
    initial={node:np.where(rng.random(n)<seeds[node][0],0.,np.inf) if node in seeds else np.full(n,np.inf) for node in nodes}
    draws=rng.random((len(edges),n));delays=np.array([rng.uniform(*e['delay'],n) for e in edges])
    preparations={i['id']:start_delay+rng.uniform(*i['preparation'],n) for i in INTERVENTIONS}
    side=rng.random(n)
    def simulate(plan):
        times={k:v.copy() for k,v in initial.items()}
        for _ in nodes:
            changed=False
            for j,e in enumerate(edges):
                proposed=times[e['from']]+delays[j];prob=np.full(n,min(1,e['probability']*dependency_scale))
                for intervention in plan:
                    if intervention['edge']==[e['from'],e['to']]:
                        ready=preparations[intervention['id']]<=proposed
                        prob=np.where(ready,prob*(1-intervention['reduction']),prob)
                candidate=np.where((draws[j]<prob)&(proposed<=horizon),proposed,np.inf)
                updated=np.minimum(times[e['to']],candidate)
                if np.any(updated<times[e['to']]):changed=True
                times[e['to']]=updated
            if any(i['id']=='access' for i in plan):
                extra=np.where((side<.15)&(preparations['access']<=times['junction'])&(times['junction']+1<=horizon),times['junction']+1,np.inf)
                updated=np.minimum(times['alternate_road'],extra)
                if np.any(updated<times['alternate_road']):changed=True
                times['alternate_road']=updated
            if not changed:break
        harm=sum(np.isfinite(times[node])*HARM[node] for node in nodes)
        return times,harm
    baseline_times,baseline=simulate([])
    catalog=[]
    for i in INTERVENTIONS:
        reason='Eligible under declared synthetic capability'
        available=True
        destination=i['edge'][1] if i['edge'] else None
        if destination in seeds:available=False;reason='Downstream disruption is already reported; prevention cannot undo it'
        catalog.append({**i,'eligible':available,'eligibility_reason':reason})
    plans=[()]+[(i,) for i in catalog]+list(combinations(catalog,2));results=[]
    for plan in plans:
        required={'crews':sum(i['crews'] for i in plan),'pumps':sum(i['pumps'] for i in plan),'cost':sum(i['cost'] for i in plan)}
        feasible=required['crews']<=crews and required['pumps']<=pumps and required['cost']<=budget and all(i['eligible'] for i in plan)
        row={'id':'+'.join(i['id'] for i in plan) or 'monitor','label':' + '.join(i['label'] for i in plan) or 'Continue monitoring','interventions':[i['id'] for i in plan],'resources':required,'feasible':feasible}
        if not feasible:
            row['reason']='Requires more resources than available or prevention target is already reported disrupted';results.append(row);continue
        times,harm=simulate(plan) if plan else (baseline_times,baseline)
        benefit=baseline-harm-required['cost'];se=float(np.std(benefit,ddof=1)/np.sqrt(n))
        row.update(expected_harm=float(np.mean(harm)),total_expected_loss=float(np.mean(harm)+required['cost']),net_benefit=float(np.mean(benefit)),benefit_interval=[float(np.mean(benefit)-1.96*se),float(np.mean(benefit)+1.96*se)],node_probabilities={node:float(np.mean(np.isfinite(times[node]))) for node in nodes})
        results.append(row)
    results.sort(key=lambda r:(not r['feasible'],r.get('total_expected_loss',float('inf')),r['id']))
    windows=[]
    for i in catalog:
        edge=i['edge']
        if edge:
            j=next(j for j,e in enumerate(edges) if [e['from'],e['to']]==edge)
            proposed=baseline_times[edge[0]]+delays[j]
            mask=(draws[j]<min(1,edges[j]['probability']*dependency_scale))&(proposed<=horizon)
            slacks=proposed[mask]-(preparations[i['id']][mask]-start_delay)
        else:slacks=np.array([])
        stable=len(slacks)>=20
        windows.append({'intervention':i['id'],'conditional_samples':len(slacks),'latest_start_delay':round(float(np.quantile(slacks,.2)),2) if stable else None,'latest_start_minute':round(snapshot['minute']+float(np.quantile(slacks,.2)),2) if stable else None,'basis':'20th percentile of baseline transmission time minus preparation time, conditional on this path transmitting. Illustrative 80% readiness target; not a calibrated deadline.' if stable else 'Timing uncertain: too few relevant simulated paths, or inspection has no prevention model.'})
    best=next(r for r in results if r['feasible'])
    return {'module':'cascade','minute':snapshot['minute'],'snapshot_hash':snapshot['hash'],'seed':seed,'samples':samples,'horizon_minutes':horizon,'parameters':{'crews':crews,'pumps':pumps,'budget':budget,'start_delay':start_delay,'dependency_scale':dependency_scale},'catalog':catalog,'plans':results,'selected_plan':best['id'],'windows':windows,'harm_weights':HARM,'observed_seed_nodes':list(seeds),'assumptions':['Manually configured dependency DAG; not learned causal discovery.','Independent edge and preparation draws; all plans reuse identical random arrays.','Effects apply only if preparation finishes before a simulated transmission.','Harm weights, costs and effect sizes are illustrative; intervals reflect Monte Carlo sampling only.','24-minute prospective laboratory; not calibrated 72-hour forecasting.','No evidence means no seeded cascade; no-benefit does not establish safety.']}
