"""Opt-in local notification adapter. Credentials and registration tokens stay server-side."""
import importlib.util
import os
from pathlib import Path
from datetime import datetime,timezone
import sqlite3
from threading import RLock
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel,Field
from fastapi import APIRouter,HTTPException

class Registration(BaseModel):
    client_id:str=Field(min_length=20,max_length=120)
    token:str=Field(min_length=20,max_length=4096)
    zone_id:Literal['north','river','east']

class ClientRequest(BaseModel):
    client_id:str=Field(min_length=20,max_length=120)

class ObservationRequest(ClientRequest):
    zone_id:Literal['north','river','east']
    send_push:bool=False

class NotificationAdapter:
    def __init__(self,db,lock=None):
        self.db=db;self.lock=lock or RLock()
        self.db.execute('CREATE TABLE IF NOT EXISTS notification_clients(client_id TEXT PRIMARY KEY, token TEXT NOT NULL, zone_id TEXT, opted_at TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS observation_requests(id TEXT PRIMARY KEY, zone_id TEXT, created_at TEXT, client_id TEXT)')
        self.db.commit()
    def register(self,registration):
        with self.lock:
            self.db.execute('INSERT OR REPLACE INTO notification_clients VALUES(?,?,?,?)',(registration.client_id,registration.token,registration.zone_id,datetime.now(timezone.utc).isoformat()))
            self.db.commit()
    def remove(self,client_id):
        with self.lock:
            self.db.execute('DELETE FROM notification_clients WHERE client_id=?',(client_id,));self.db.commit()
    def registered(self,client_id):
        with self.lock:
            return bool(self.db.execute('SELECT 1 FROM notification_clients WHERE client_id=?',(client_id,)).fetchone())
    def status(self):
        path=os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        configured=bool(path and Path(path).is_file())
        sdk=importlib.util.find_spec('firebase_admin') is not None
        return {'server_credentials_configured':configured,'server_sdk_installed':sdk,
            'sender_status':'configured, untested' if configured and sdk else 'not configured',
            'project_id':os.environ.get('FIREBASE_PROJECT_ID','sentinel-zero-c95fb'),
            'detail':'FCM sends are available only to this browser after explicit opt-in.' if configured and sdk else 'Set GOOGLE_APPLICATION_CREDENTIALS to a server-only service-account JSON file and install firebase-admin. Public web keys cannot authorize sending.'}
    def send(self,client_id,title,body,path='/citizen'):
        with self.lock:
            record=self.db.execute('SELECT token FROM notification_clients WHERE client_id=?',(client_id,)).fetchone()
        if not record:raise HTTPException(409,'This browser has no opted-in FCM registration')
        status=self.status()
        if not status['server_credentials_configured'] or not status['server_sdk_installed']:
            raise HTTPException(503,status['detail'])
        try:
            import firebase_admin
            from firebase_admin import credentials,messaging
            try:app=firebase_admin.get_app('sentinel-zero')
            except ValueError:
                app=firebase_admin.initialize_app(credentials.Certificate(os.environ['GOOGLE_APPLICATION_CREDENTIALS']),{'projectId':status['project_id']},name='sentinel-zero')
            # Data-only messages are rendered by the bundled service worker, avoiding duplicate notifications.
            message=messaging.Message(token=record[0],data={'title':title,'body':body,'path':path,'simulation':'true'})
            messaging.send(message,app=app)
            return {'sent':True,'message':'FCM accepted the message. Device delivery depends on browser/provider support.'}
        except HTTPException:raise
        except Exception:
            # Never echo SDK exceptions: they may include tokens or credential details.
            raise HTTPException(502,'FCM rejected the send. Check server credentials, project alignment, and the opted-in token.')
    def request(self,client_id,zone_id):
        row={'id':uuid4().hex,'zone_id':zone_id,'created_at':datetime.now(timezone.utc).isoformat(),
             'question':'Can you see standing water on the road from your current safe location?','simulated':True}
        with self.lock:
            self.db.execute('INSERT INTO observation_requests VALUES(?,?,?,?)',(row['id'],zone_id,row['created_at'],client_id));self.db.commit()
        return row
    def requests(self,client_id):
        with self.lock:
            return [{'id':r[0],'zone_id':r[1],'created_at':r[2],'simulated':True,
                'question':'Can you see standing water on the road from your current safe location?'} for r in self.db.execute('SELECT id,zone_id,created_at FROM observation_requests WHERE client_id=? ORDER BY created_at DESC LIMIT 20',(client_id,))]

def notification_router(db,lock=None):
    adapter=NotificationAdapter(db,lock)
    router=APIRouter(prefix='/api/notifications')
    @router.get('/status')
    def status(client_id:str|None=None):
        return {**adapter.status(),'registered':adapter.registered(client_id) if client_id else False}
    @router.post('/register',status_code=201)
    def register(request:Registration):
        adapter.register(request);return {'registered':True}
    @router.post('/unsubscribe')
    def unsubscribe(request:ClientRequest):
        adapter.remove(request.client_id);return {'registered':False}
    @router.post('/test')
    def test(request:ClientRequest):
        return adapter.send(request.client_id,'BEFOREPOINT · Test only','Your opt-in notification connection is working. This is not an emergency warning.')
    @router.post('/observation-request',status_code=201)
    def observation(request:ObservationRequest):
        row=adapter.request(request.client_id,request.zone_id)
        if request.send_push:
            try:
                row['push']=adapter.send(request.client_id,'BEFOREPOINT · Test observation request',row['question'],f'/citizen?request={row["id"]}')
            except HTTPException as error:
                row['push']={'sent':False,'message':error.detail,'error_status':error.status_code}
        else:row['push']={'sent':False,'message':'In-app request created. No push requested.'}
        return row
    @router.get('/requests')
    def requests(client_id:str):return adapter.requests(client_id)
    return router
