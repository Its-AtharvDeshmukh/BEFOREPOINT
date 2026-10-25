from threading import RLock
from pydantic import BaseModel, Field
from typing import Literal
from fastapi import APIRouter,HTTPException
from .replay import Replay

router=APIRouter(prefix='/api/twin-lab')

class TwinRequest(BaseModel):
    seed:int=Field(default=26,ge=0,le=2147483647)
    pair:Literal['standard','ambiguous']='standard'

class TwinLab:
    def __init__(self):
        self.lock=RLock();self.reset(26,'standard')
    def reset(self,seed,pair):
        with self.lock:
            self.seed,self.pair=seed,pair
            self.a=Replay('twin_crisis',seed)
            self.b=Replay('twin_benign' if pair=='standard' else 'ambiguous',seed)
            self.running=False;self.revealed=False
    def step(self):
        with self.lock:
            self.a.step();self.b.step()
            if self.a.minute>=18:self.running=False
            return self.state()
    def state(self):
        with self.lock:
            a,b=self.a.state(),self.b.state()
            a.pop('scenario');b.pop('scenario')
            equal=all(x['probabilities']==y['probabilities'] and x['decision']==y['decision'] and x['forecasts']==y['forecasts'] for x,y in zip(self.a.history[:8],self.b.history[:8]))
            return {'a':a,'b':b,'seed':self.seed,'pair':self.pair,'running':self.running,
                'minute':self.a.minute,'prefix_consistent':equal,'prefix_complete':self.a.minute>=7,
                'revealed':self.revealed,'outcomes':{'a':self.a.episode.truth,'b':self.b.episode.truth} if self.revealed else None,
                'different_evidence':self.difference()}
    def difference(self):
        a={e.id:e.model_dump() for e in self.a.events.values()}
        b={e.id:e.model_dump() for e in self.b.events.values()}
        return [{'id':id,'a':a.get(id),'b':b.get(id)} for id in sorted(a.keys()|b.keys()) if a.get(id)!=b.get(id)]

lab=TwinLab()

@router.get('/state')
def state():return lab.state()
@router.post('/reset')
def reset(request:TwinRequest):
    lab.reset(request.seed,request.pair);return lab.state()
@router.post('/step')
def step():return lab.step()
@router.post('/start')
def start():
    lab.running=lab.a.minute<18;return lab.state()
@router.post('/pause')
def pause():
    lab.running=False;return lab.state()
@router.post('/reveal')
def reveal():
    if lab.a.minute<8:raise HTTPException(409,'Outcomes remain hidden until distinguishing evidence can arrive at minute 8')
    lab.revealed=True;return lab.state()
