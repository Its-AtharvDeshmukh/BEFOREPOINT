from uuid import uuid4
from threading import RLock
from .models import Event
from .simulator import generate
from .inference import BayesianFilter
from .decision import decide
from .graph import forecast, deadlines
from .voi import value_of_information
from .vulnerability import assess
from .receipts import ReceiptStore, digest
from .settings import CONFIG as C


class Replay:
    def __init__(self,scenario='twin_crisis',seed=26,store=None,shifted=False,engine=None):
        self.lock=RLock()
        self.scenario,self.seed=scenario,seed
        self.episode=generate(scenario,seed,shifted)
        self.store=store if store is not None else ReceiptStore()
        self.initial_source_betas=self.store.source_priors()
        self.engine=engine or BayesianFilter(initial_betas=self.initial_source_betas)
        self.run_id=uuid4().hex
        self.minute=-1
        self.events={}
        self.history=[]
        self.running=False
        self.last_change=-99
        self.pending=[]
        self.store.save_run(self.run_id,{'scenario':scenario,'seed':seed,'shifted':shifted,'model_version':C['version'],'configuration':C,'initial_source_betas':self.initial_source_betas,'events':[e.model_dump() for e in self.episode.events],'withheld_outcome':self.episode.truth,'withheld_failures':self.episode.failures})
        self.step()

    def ingest(self,event):
        existing=self.events.get(event.id)
        if existing:
            if existing != event: raise ValueError('Conflicting event ID; original retained')
            return False
        if event.arrival_time>self.minute or event.event_time>self.minute:
            raise ValueError('Event is not yet available at simulated time')
        self.events[event.id]=event
        self.store.event(self.run_id,event)
        return True

    def queue(self,event):
        # All newly submitted observations take effect on the next simulated minute.
        with self.lock:
            if self.minute>=self.episode.duration: raise ValueError('Episode finished; reset before submitting')
            if event.arrival_time != self.minute+1 or event.event_time>event.arrival_time:
                raise ValueError('Submission arrival must equal the next simulated minute')
            if event.kind in ('retraction','verification'):
                target=self.events.get(event.retracts)
                if target is None or target.kind in ('verification','retraction'):
                    raise ValueError('Reference must identify an already available observation')
            existing=next((e for e in self.pending if e.id==event.id),self.events.get(event.id))
            if existing:
                if existing!=event: raise ValueError('Conflicting event ID')
                return False
            self.pending.append(event)
            return True

    def step(self):
        with self.lock:
            if self.minute>=self.episode.duration:
                self.running=False
                return self.state()
            self.minute+=1
            for event in (*self.episode.events,*self.pending):
                if event.arrival_time==self.minute:
                    self.ingest(event)
            self.pending=[e for e in self.pending if e.arrival_time>self.minute]
            p,active,trace,scores=self.engine.estimate(list(self.events.values()),self.minute)
            prev=self.history[-1] if self.history else None
            predictions=forecast(active,self.minute,p,scores)
            deadline_rows=deadlines(predictions,self.minute)
            decision=decide(p,prev['decision']['action'] if prev else None,self.minute-self.last_change,deadline_rows)
            if not prev or decision['action']!=prev['decision']['action']: self.last_change=self.minute
            zones=assess(active,self.minute)
            source_latest={}
            gateway_latest={}
            for e in sorted(active,key=lambda e:(e.arrival_time,e.id)):
                if e.kind in C['likelihoods']:
                    source_latest[e.source_id]={'source':e.source_id,'kind':e.kind,'zone':e.zone_id,'gateway':e.gateway,
                        'reliability':scores.get(e.source_id,.8),'last_seen':e.event_time,
                        'status':'missing' if e.kind in ('stream_missing','gateway_down') else ('stale' if self.minute-e.event_time>4 else 'reporting')}
                if e.gateway:
                    gateway_latest[e.gateway]={'gateway':e.gateway,'status':'unconfirmed loss' if e.kind=='stream_missing' else ('offline' if e.kind=='gateway_down' else 'online' if e.kind=='gateway_up' else 'reporting'),'last_seen':e.event_time}
            delta={h:float(p[i]-(prev['probabilities'][h] if prev else C['prior'][i])) for i,h in enumerate(C['hypotheses'])}
            snapshot={'minute':self.minute,'probabilities':dict(zip(C['hypotheses'],p.tolist())),
                'decision':decision,'forecasts':predictions,'deadlines':deadline_rows,
                'voi':value_of_information(p,deadline_rows),'zones':zones,'evidence_trace':trace,
                'sources':list(source_latest.values()),'gateways':list(gateway_latest.values()),
                'delta':delta,'visible_event_ids':sorted(self.events),'active_event_ids':sorted(e.id for e in active),
                'initial_source_betas':self.initial_source_betas,'model_version':C['version'],'configuration_hash':digest(C),'supporting_evidence':[e.model_dump() for e in active],
                'explanation':f'{len(active)} available reports; {len(trace)} recent dependency groups. Missing readings represent lost evidence. Probabilities are model estimates using illustrative likelihoods.'}
            receipt=self.store.append(self.run_id,snapshot)
            self.history.append(receipt)
            self.store.learn_sources(self.run_id,list(self.events.values()),self.minute)
            if self.minute>=self.episode.duration: self.running=False
            return self.state()

    def state(self):
        with self.lock:
            return {'run_id':self.run_id,'scenario':self.scenario,'seed':self.seed,'running':self.running,
                'duration':self.episode.duration,'pending_count':len(self.pending),
                'current':self.history[-1] if self.history else None,
                'history':[{'minute':r['minute'],'probabilities':r['probabilities'],'action':r['decision']['action'],'hash':r['hash']} for r in self.history],
                'events':[e.model_dump() for e in sorted(self.events.values(),key=lambda e:(-e.arrival_time,e.id))]}
