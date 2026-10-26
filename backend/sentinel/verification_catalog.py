"""Declared synthetic instruments; no future episode state is accepted by ranking."""
import math
import numpy as np
from .settings import CONFIG as C

CATALOG = [
 {**C['checks'][0], 'reliability':.8, 'source':'check:water','gateway':None,'authorization':'Independent simulated sensor'},
 {**C['checks'][1], 'reliability':.8, 'source':'check:gateway','gateway':None,'authorization':'Out-of-band simulated diagnostic'},
 {**C['checks'][2], 'reliability':.65, 'source':'check:observer','gateway':None,'authorization':'Voluntary remote observation from an already safe location; no travel'},
 {'id':'pump','label':'Pump-station telemetry','positive':[.05,.18,.72,.86],'delay':1,'cost':.5,'inconclusive':.12,'reliability':.8,'source':'check:pump','gateway':'gw-river','authorization':'Authorized simulated equipment telemetry'},
 {'id':'camera','label':'Authorized camera observation','positive':[.06,.08,.75,.82],'delay':1,'cost':.7,'inconclusive':.18,'reliability':.8,'source':'check:camera','gateway':None,'authorization':'Existing simulated camera; no personal imagery retained'},
 {'id':'traffic','label':'Independent traffic information','positive':[.15,.12,.55,.78],'delay':1,'cost':.3,'inconclusive':.1,'reliability':.8,'source':'check:traffic','gateway':None,'authorization':'Aggregate simulated traffic feed'}]
BY_ID={c['id']:c for c in CATALOG}

def effective_check(check,quality=None):
    q=check['reliability'] if quality is None else min(check['reliability'],quality)
    return {**check,'nominal_delay':check['delay'],'delay':math.ceil(check['delay']),'effective_reliability':q,'positive':(.5+q*(np.array(check['positive'])-.5)).tolist()}

def outcome_likelihood(candidate_id,outcome,quality):
    c=effective_check(BY_ID[candidate_id],quality); y=np.array(c['positive']);u=c['inconclusive']
    return {'positive':(1-u)*y,'negative':(1-u)*(1-y),'inconclusive':np.full(4,u)}[outcome]
