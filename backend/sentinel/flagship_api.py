from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .prove import rank, request_check, reveal_check
from .interventions import evaluate_interventions
from .lifelines import inspect_lifelines, apply_blackout

class CheckRequest(BaseModel):
    candidate_id:str
    snapshot_hash:str=Field(min_length=64,max_length=64)
class RevealRequest(BaseModel):
    candidate_id:str

class CascadeRequest(BaseModel):
    snapshot_hash:str=Field(min_length=64,max_length=64)
    crews:int=Field(default=2,ge=0,le=4)
    pumps:int=Field(default=1,ge=0,le=2)
    budget:float=Field(default=9,ge=0,le=50)
    start_delay:float=Field(default=0,ge=0,le=24)
    samples:int=Field(default=512,ge=64,le=2048)
    seed:int=Field(default=26,ge=0,le=2147483647)
    dependency_scale:float=Field(default=1,ge=.5,le=1.5)
class BlackoutRequest(BaseModel):
    snapshot_hash:str=Field(min_length=64,max_length=64)
    seed:int=Field(default=26,ge=0,le=2147483647)

def flagship_router(get_replay):
    router=APIRouter(prefix='/api/lab',tags=['shared scenario experiments'])
    @router.get('/prove')
    def prove():
        r=get_replay()
        with r.lock:
            tickets=[a for a in r.store.analyses(r.run_id) if a.get('module')=='prove']
            return {**rank(r.history[-1],r.episode.duration,[t['candidate_id'] for t in tickets]),'tickets':tickets}
    @router.post('/prove/request')
    def request(body:CheckRequest):
        try:return request_check(get_replay(),body.candidate_id,body.snapshot_hash)
        except ValueError as e:raise HTTPException(409,str(e)) from e
    @router.post('/prove/reveal')
    def reveal(body:RevealRequest):
        try:return reveal_check(get_replay(),body.candidate_id)
        except ValueError as e:raise HTTPException(409,str(e)) from e
    @router.post('/cascade')
    def cascade(body:CascadeRequest):
        r=get_replay()
        with r.lock:
            if r.history[-1]['hash']!=body.snapshot_hash:raise HTTPException(409,'Snapshot changed; compare again at the current minute')
            result=evaluate_interventions(r.history[-1],**body.model_dump(exclude={'snapshot_hash'}))
            r.store.save_analysis(r.run_id,'cascade:'+__import__('hashlib').sha256(str(body).encode()).hexdigest()[:16],result)
            return result
    @router.get('/lifelines')
    def lifelines():
        r=get_replay()
        with r.lock:return inspect_lifelines(r)
    @router.post('/lifelines/blackout')
    def blackout(body:BlackoutRequest):
        try:return apply_blackout(get_replay(),body.seed,body.snapshot_hash)
        except ValueError as e:raise HTTPException(409,str(e)) from e
    @router.get('/evaluation')
    def evaluated_report():
        import json
        from pathlib import Path
        path=Path(__file__).resolve().parents[2]/'docs'/'phase4-evaluation.json'
        if not path.exists():raise HTTPException(503,'Run the offline Phase 4 evaluation first')
        return json.loads(path.read_text())
    return router
