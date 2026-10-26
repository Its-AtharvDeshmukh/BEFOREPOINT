import numpy as np
from .settings import CONFIG as C
from .reliability import effective_reliability

OBSERVATIONS={'rain_high':'rainfall','water_high':'drainage','road_closed':'underpass',
    'power_loss':'substation','gateway_down':'gateway','traffic_slow':'junction',
    'hospital_surge':'hospital','dispatch_delay':'dispatch'}


def observed_seeds(events,minute,p,scores=None):
    local={}
    for e in sorted(events,key=lambda e:(e.arrival_time,e.id)):
        if e.kind in OBSERVATIONS and minute-e.event_time<=8:
            node=OBSERVATIONS[e.kind]
            confidence=min(.98,effective_reliability(e,scores or {})*(.4+.6*(p[2]+p[3])))
            local[(e.zone_id,node)]=(confidence,[max(minute,e.event_time)]*2,[e.id])
        if e.kind=='water_normal':local.pop((e.zone_id,'drainage'),None)
        if e.kind=='gateway_up':local.pop((e.zone_id,'gateway'),None)
    seeds={}
    for (_,node),value in local.items():
        if node not in seeds or value[0]>seeds[node][0]:seeds[node]=value
    return seeds


def forecast(events,minute,p,scores=None):
    seeds=observed_seeds(events,minute,p,scores)
    projected={k:(v[0],v[1]) for k,v in seeds.items()}
    paths={k:[k] for k in seeds};support={k:v[2] for k,v in seeds.items()}
    for _ in range(len(C['nodes'])):
        changed=False
        for edge in C['edges']:
            a,b=edge['from'],edge['to']
            if a not in projected or b in seeds or b in paths[a]:continue
            prob,window=projected[a];q=prob*edge['probability']
            if b not in projected or q>projected[b][0]+1e-12:
                projected[b]=(q,[window[0]+edge['delay'][0],window[1]+edge['delay'][1]])
                paths[b]=paths[a]+[b];support[b]=support[a];changed=True
        if not changed:break
    result=[{'component':k,'event_type':f'{k}_disruption','probability':float(v[0]),'window':v[1],
        'path':paths[k],'supporting_observations':support[k],
        'basis':'Configured strongest dependency path; simulated assumptions',
        'uncertainty':'Illustrative conditional propagation and delay intervals; no field calibration',
        'assumptions':['Manually specified directed dependencies','Strongest path, not sum of correlated paths','Recent reported condition seeds the current forecast horizon']}
        for k,v in projected.items() if k not in seeds]
    result.sort(key=lambda x:(-x['probability'],x['window'][0],x['component']))
    return result[:3]


def deadlines(forecasts,minute):
    if not forecasts:return []
    target=next((f for f in forecasts if f['component'] in ('underpass','junction','hospital')),forecasts[0])
    failure=np.linspace(*target['window'],81)
    output=[]
    for prep in C['preparations']:
        response=np.linspace(*prep['response_minutes'],81)
        slack=(failure[:,None]-response[None,:]).ravel()
        latest=float(np.quantile(slack,1-prep['target_probability'],method='lower'))
        output.append({**prep,'failure':target['component'],'latest_start':round(latest,2),
            'minutes_remaining':round(latest-minute,2),'conditional_on_failure':True,
            'event_probability':target['probability'],'failure_window':target['window'],'decision_minute':minute,
            'effectiveness_if_started_now':float(np.mean(minute+response[None,:]<=failure[:,None])),
            'description':'Model-estimated action deadline; independent uniform failure/response delay assumptions. Event probability separately weights expected loss.'})
    return output
