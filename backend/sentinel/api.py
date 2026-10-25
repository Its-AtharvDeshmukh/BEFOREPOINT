import asyncio
import json
import os
from pathlib import Path
from contextlib import asynccontextmanager
from functools import lru_cache
from hashlib import sha256
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from .models import Event, ResetRequest, CitizenRequest
from .replay import Replay
from .receipts import ReceiptStore
from .simulator import SCENARIOS
from .settings import CONFIG
from .evaluation import evaluate, twin_test
from .weather import router as weather_router
from .twin_lab import router as twin_router, lab
from .notifications import notification_router
from .analysis import analysis_router

store=ReceiptStore(os.environ.get('SENTINEL_DB','sentinel.sqlite3'))
replay=Replay(store=store)

@asynccontextmanager
async def lifespan(app):
    async def clock():
        while True:
            await asyncio.sleep(2)
            if replay.running: replay.step()
            if lab.running: lab.step()
    task=asyncio.create_task(clock())
    yield
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass

app=FastAPI(title='BEFOREPOINT',version='0.2.0',lifespan=lifespan)
app.include_router(weather_router)
app.include_router(twin_router)
app.include_router(analysis_router(lambda: replay))
app.include_router(notification_router(store.db,store.lock))

@app.get('/api/health')
def health(): return {'ok':True,'mode':'simulation','model_version':CONFIG['version']}

@app.get('/api/diagnostics')
def diagnostics():
    return {**store.diagnostics(),'mode':'local simulation','model_version':CONFIG['version'],'current_run':replay.run_id,'minute':replay.minute,'optional_services_required':False,'public_emergency_broadcasts_enabled':False}

@app.get('/api/decisions')
def decisions():
    snapshot=replay.state()['current']
    return {'minute':snapshot['minute'],'probabilities':snapshot['probabilities'],'decision':snapshot['decision'],'verification':snapshot['voi'],'forecasts':snapshot['forecasts'],'deadlines':snapshot['deadlines']}

@app.get('/api/config')
def config(): return {'scenarios':SCENARIOS,**CONFIG}

@app.get('/api/state')
def state(): return replay.state()

@app.post('/api/reset')
def reset(request:ResetRequest):
    global replay
    if request.scenario not in SCENARIOS: raise HTTPException(422,'Unknown scenario')
    replay=Replay(request.scenario,request.seed,store=store,shifted=request.shifted)
    return replay.state()

@app.post('/api/step')
def step(): return replay.step()

@app.post('/api/start')
def start():
    if replay.minute < replay.episode.duration: replay.running=True
    return replay.state()

@app.post('/api/pause')
def pause():
    replay.running=False
    return replay.state()

@app.post('/api/events',status_code=202)
def inject(event:Event):
    try: accepted=replay.queue(event)
    except ValueError as e: raise HTTPException(409,str(e)) from e
    return {'accepted':accepted,'effective_minute':event.arrival_time}

@app.post('/api/citizen',status_code=202)
def citizen(request:CitizenRequest):
    with replay.lock:
        next_minute=replay.minute+1
        # One answer per token per zone per run, plus inference-level common-source pooling.
        identity=sha256(f'{replay.run_id}:{request.zone_id}:{request.token}'.encode()).hexdigest()[:20]
        if any(e.id==f'citizen-{identity}' for e in [*replay.events.values(),*replay.pending]):
            raise HTTPException(409,'This observer already submitted an answer for this zone in this run')
        event=Event(id=f'citizen-{identity}',source_id=f'citizen:{identity}',kind=f'citizen_{request.answer}',
                    zone_id=request.zone_id,event_time=next_minute,arrival_time=next_minute,reliability=.65,
                    correlation_group=f'citizen:{request.zone_id}')
        return inject(event)

@app.get('/api/receipts')
def receipts(run_id:str|None=None):
    selected=run_id or replay.run_id
    return {'run_id':selected,'valid':store.verify(selected),'receipts':store.list(selected)}

@app.get('/api/runs')
def runs(): return store.runs()

@app.get('/api/twins')
def twins(seed:int=26): return twin_test(seed)

@lru_cache(maxsize=1)
def benchmark():
    result=evaluate()
    store.save_evaluation(CONFIG['version'],result)
    return result

@app.get('/api/evaluation')
async def evaluation(): return await asyncio.to_thread(benchmark)

@app.post('/api/outcome/reveal')
def reveal_outcome():
    if replay.minute<replay.episode.duration:
        raise HTTPException(409,'Complete the simulation before revealing its outcome')
    return {'run_id':replay.run_id,'outcome':replay.episode.truth,'simulated':True}

@app.get('/api/stream')
async def stream():
    async def updates():
        revision=None
        while True:
            snapshot=replay.state()
            current=(snapshot['run_id'],snapshot['current']['minute'],snapshot['running'],snapshot['pending_count'])
            if current!=revision:
                yield f'data: {json.dumps(snapshot)}\n\n'
                revision=current
            else: yield ': heartbeat\n\n'
            await asyncio.sleep(1)
    return StreamingResponse(updates(),media_type='text/event-stream',headers={'Cache-Control':'no-cache'})

DIST=Path(__file__).resolve().parents[2]/'frontend'/'dist'
if DIST.exists():
    app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='assets')
    @app.get('/favicon.svg')
    def favicon(): return FileResponse(DIST/'favicon.svg',media_type='image/svg+xml')
    @app.get('/firebase-messaging-sw.js')
    def messaging_worker():
        return FileResponse(DIST/'firebase-messaging-sw.js',media_type='application/javascript',headers={'Service-Worker-Allowed':'/','Cache-Control':'no-cache'})
    @app.get('/')
    @app.get('/citizen')
    def index(): return FileResponse(DIST/'index.html')
