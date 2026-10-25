"""Synthetic observations and withheld labels. Only event lists cross into inference."""
from dataclasses import dataclass
import random
from .models import Event

SCENARIOS = {
 'normal_rain':'Normal heavy rain', 'flood':'Developing flood', 'isolated':'Isolated waterlogging',
 'gateway_failure':'Shared gateway failure', 'misinformation':'Coordinated false reports',
 'delayed_calls':'Delayed and duplicated calls', 'missing_streams':'Sudden stream loss',
 'monsoon':'Monsoon baseline shift', 'twin_crisis':'Twin A · cascading crisis',
 'twin_benign':'Twin B · gateway outage', 'silent_zone':'Vulnerable zone goes silent',
 'ambiguous':'Prolonged ambiguity'}

@dataclass(frozen=True)
class Episode:
    events: tuple[Event,...]
    truth: str
    failures: tuple[tuple[str,int],...]
    crisis_onset: int | None
    duration: int = 18


def generate(name='twin_crisis', seed=26, shifted=False):
    if name not in SCENARIOS: raise ValueError('Unknown scenario')
    rng=random.Random(seed)
    events=[]
    def add(t,kind,source,zone='river',arrival=None,gateway=None,group=None,payload=None,id=None):
        events.append(Event(id=id or f'e{len(events):04}',source_id=source,kind=kind,zone_id=zone,
                            event_time=t,arrival_time=t if arrival is None else arrival,
                            gateway=gateway,correlation_group=group,reliability=.86,
                            payload=payload or {}))
    # Twins have byte-identical events through minute seven for any common seed/config.
    common=name.startswith('twin') or name=='ambiguous'
    add(1,'rain_high','weather','north')
    if common:
        add(2,'water_high','level-r1',gateway='gw-river')
        add(3,'traffic_slow','traffic-1')
        add(4,'stream_missing','level-r1',gateway='gw-river')
        add(4,'stream_missing','level-r2',gateway='gw-river')
        add(6,'calls_surge','dispatch-logs',arrival=7)
    else:
        for t in range(2,8,2):
            kind='water_normal' if name in ('normal_rain','gateway_failure','misinformation','monsoon') else 'water_high'
            add(t,kind,'level-r1',gateway='gw-river')
    crisis = name in ('twin_crisis','flood','delayed_calls','silent_zone')
    truth='CASCADING_CRISIS' if crisis else ('SENSOR_FAILURE' if name in ('twin_benign','gateway_failure','missing_streams','misinformation','ambiguous') else ('ISOLATED_INCIDENT' if name=='isolated' else 'NOISE'))
    failures=[]
    divergence=11 if name=='ambiguous' else 8
    if crisis:
        add(8,'water_high','independent-level')
        add(9,'calls_surge','dispatch-logs')
        add(10,'road_closed','roads-operator',payload={'component':'underpass'})
        add(12,'power_loss','power-operator',payload={'component':'substation'})
        add(14,'hospital_surge','hospital-operator',payload={'component':'hospital'})
        failures=[('drainage',8),('underpass',10),('substation',12),('hospital',14)]
    elif name in ('twin_benign','gateway_failure','ambiguous'):
        add(divergence,'gateway_down','gateway-diagnostic',gateway='gw-river')
        for t in (divergence+1,divergence+3,divergence+5):
            add(t,'water_normal','independent-level')
        add(15,'gateway_up','gateway-diagnostic',gateway='gw-river')
    elif name=='isolated':
        add(8,'road_closed','roads-operator',payload={'component':'underpass'})
        add(9,'water_normal','level-east','east')
        add(12,'water_normal','independent-level')
        failures=[('underpass',8)]
    if name=='misinformation':
        for i in range(45):
            add(4,'citizen_yes',f'citizen:bot{i}',group='copied-rumor')
        add(8,'water_normal','independent-level')
    if name=='delayed_calls':
        add(3,'calls_surge','dispatch-late',arrival=8,id='late-call')
        events.append(events[-1])  # Exact delivery duplicate, including original identity.
    if name in ('missing_streams','silent_zone'):
        for i in range(12): add(5,'stream_missing',f'level-r{i}',gateway='gw-river')
    if name=='monsoon' or shifted:
        add(0,'baseline_shift','weather-operator',payload={'regime':'monsoon'})
    # Seeded nuisance events and arrival latency, independent of withheld outcome.
    for t in range(9,18,3):
        kind=rng.choice(['rain_high','water_normal','traffic_slow'])
        if shifted and kind=='water_normal': kind='rain_high'
        add(t,kind,'weather-secondary' if kind=='rain_high' else 'level-north','north',arrival=t+rng.randrange(0,2))
    return Episode(tuple(events),truth,tuple(failures),10 if crisis else None)
