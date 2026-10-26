"""Aggregate structural fragility and explicit synthetic stream availability."""
import random
import numpy as np
from .settings import CONFIG as C
from .models import Event
from .vulnerability import assess
from .receipts import digest

STREAMS=[{'source':source,'zone':zone,'gateway':'gw-river' if source in ('level-r1','level-r2','gateway-diagnostic') else None} for zone,sources in [('north',['level-n1','level-n2','traffic-n','camera-n']),('river',['level-r1','level-r2','traffic-1','gateway-diagnostic']),('east',['level-e1','camera-e'])] for source in sources]

def structural_score(routes,backup_power,facility_minutes):
    return round(min(1,.45/(1+routes)+(.2 if not backup_power else 0)+.35*min(1,facility_minutes/20)),3)

def inspect_lifelines(replay):
    snapshot=replay.history[-1];events=[Event.model_validate(e) for e in snapshot['supporting_evidence']]
    latest={}
    for e in sorted(events,key=lambda e:(e.arrival_time,e.id)):
        if e.kind not in ('retraction','verification','baseline_shift'):latest[e.source_id]=e
    streams=[]
    for s in STREAMS:
        e=latest.get(s['source']);age=replay.minute-e.event_time if e else None
        status='disconnected' if s['source'] in replay.disabled_streams else 'missing' if e and e.kind in ('stream_missing','gateway_down') else 'unknown' if not e else 'fresh' if age<=4 else 'stale'
        streams.append({**s,'status':status,'age_minutes':age,'last_observation':e.kind if e else None})
    zones=[]
    for z in assess(events,replay.minute):
        reports=[e for e in events if e.zone_id==z['id'] and e.kind in ('water_high','water_normal','road_closed','power_loss','traffic_slow','hospital_surge','dispatch_delay') and replay.minute-e.event_time<=4]
        positive=[e for e in reports if e.kind!='water_normal'];negative=[e for e in reports if e.kind=='water_normal']
        hazard='conflicting reports' if positive and negative else 'disruption reported' if positive else 'normal water reading reported' if negative else 'unknown'
        local=[s for s in streams if s['zone']==z['id']];fresh=sum(s['status']=='fresh' for s in local)
        zones.append({**z,'structural_score':structural_score(z['routes'],z['backup_power'],z['facility_minutes']),'hazard_status':hazard,'hazard_evidence_ids':[e.id for e in reports],'observation_quality':fresh/len(local),'eligible_streams':len(local),'stream_status_counts':{status:sum(s['status']==status for s in local) for status in ('fresh','stale','unknown','missing','disconnected')},'main_reason':f"{1+z['routes']} configured access routes; {'backup power available' if z['backup_power'] else 'no backup power'}; {z['facility_minutes']} minutes to essential services.",'confidence':'Structural attributes are declared simulation inputs. Current hazard certainty depends on available reports, not the structural index.'})
    p=np.array(list(snapshot['probabilities'].values()));entropy=float(-np.sum(p*np.log2(np.maximum(p,1e-100))))
    return {'module':'lifelines','minute':replay.minute,'snapshot_hash':snapshot['hash'],'zones':zones,'streams':streams,'eligible_count':len(STREAMS),'disconnected_count':len(replay.disabled_streams),'blackout':replay.blackout,'posterior_entropy_bits':entropy,'assumptions':['Synthetic area-level infrastructure only; no individual records or precise personal locations.','Structural fragility is separate from hazard, freshness and data availability.','Unknown registry streams have never reported; they are not fabricated normal observations.','Blackout chooses 6 of 10 eligible streams with a declared deterministic seed. Other stream classes are excluded.','Missingness is pooled as one network-loss group per minute; it may favor a sensor-fault explanation, not establish a hazard.','Posterior entropy can rise or fall; missing observations do not guarantee greater numerical entropy.','No federated learning, differential privacy or re-identification resistance has been implemented.']}

def apply_blackout(replay,seed,snapshot_hash):
    with replay.lock:
        if replay.blackout:return {'state':replay.state(),'result':inspect_lifelines(replay)}
        if replay.running:raise ValueError('Pause playback before the blackout experiment')
        if replay.history[-1]['hash']!=snapshot_hash:raise ValueError('Snapshot changed; review current coverage first')
        if replay.minute>=replay.episode.duration:raise ValueError('Replay finished; reset before a blackout')
        before=inspect_lifelines(replay)
        selected=sorted(random.Random(seed).sample([s['source'] for s in STREAMS],6))
        n=replay.minute+1
        for stream in STREAMS:
            if stream['source'] in selected:
                replay.queue(Event(id='blackout:'+stream['source'],source_id=stream['source'],kind='stream_missing',zone_id=stream['zone'],event_time=n,arrival_time=n,reliability=.8,gateway=stream['gateway'],correlation_group='blackout:network'))
        replay.disabled_streams=set(selected)
        replay.blackout={'seed':seed,'selected_streams':selected,'applied_minute':n,'before_entropy_bits':before['posterior_entropy_bits'],'before_quality':{z['id']:z['observation_quality'] for z in before['zones']},'before_structural':{z['id']:z['structural_score'] for z in before['zones']},'anchor_hash':snapshot_hash}
        state=replay.step();result=inspect_lifelines(replay)
        replay.store.save_analysis(replay.run_id,'blackout',{'module':'lifelines','minute':n,'snapshot_hash':snapshot_hash,'after_hash':state['current']['hash'],'result':result})
        return {'state':state,'result':result}
