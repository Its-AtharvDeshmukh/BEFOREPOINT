"""Cached external context. Weather never enters the crisis inference engine."""
import asyncio
from datetime import datetime, timezone
import time
import httpx
from fastapi import APIRouter, HTTPException

router=APIRouter(prefix='/api')
LOCATIONS={
 'nagpur':{'name':'Nagpur, India','latitude':21.1458,'longitude':79.0882},
 'mumbai':{'name':'Mumbai, India','latitude':19.0760,'longitude':72.8777},
 'bengaluru':{'name':'Bengaluru, India','latitude':12.9716,'longitude':77.5946},
 'delhi':{'name':'New Delhi, India','latitude':28.6139,'longitude':77.2090},
 'kolkata':{'name':'Kolkata, India','latitude':22.5726,'longitude':88.3639}}
CACHE_SECONDS=600
cache={}
locks={}
backoff_until={}

class ProviderRateLimit(Exception):
    def __init__(self,seconds=60): self.seconds=max(30,min(600,seconds))

async def fetch_weather(location):
    async with httpx.AsyncClient(timeout=15) as client:
        response=await client.get('https://api.open-meteo.com/v1/forecast',params={
            **{k:v for k,v in LOCATIONS[location].items() if k!='name'},
            'current':'temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m,wind_gusts_10m,surface_pressure',
            'hourly':'temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,rain,wind_speed_10m,visibility',
            'daily':'temperature_2m_max,temperature_2m_min,precipitation_sum,wind_gusts_10m_max','forecast_days':2,'timezone':'Asia/Kolkata'})
        if response.status_code==429:
            try:seconds=int(response.headers.get('Retry-After','60'))
            except ValueError:seconds=60
            raise ProviderRateLimit(seconds)
        response.raise_for_status()
        data=response.json()
        if not data.get('current') or not data.get('hourly'): raise ValueError('Incomplete provider response')
        return validate_weather(data)

@router.get('/locations')
def locations(): return LOCATIONS

@router.get('/weather')
async def weather(location:str='nagpur'):
    if location not in LOCATIONS: raise HTTPException(422,'Select a supported city')
    lock=locks.setdefault(location,asyncio.Lock())
    async with lock:
        now=time.time()
        existing=cache.get(location)
        status='cached'
        error=None
        if now<backoff_until.get(location,0):
            if existing is None:
                raise HTTPException(503,'Open-Meteo rate limit cooldown is active. Retry later.',headers={'Retry-After':str(int(backoff_until[location]-now)+1)})
            status='stale';error='Provider rate limit cooldown; showing the last cached response.'
        elif existing is None or now-existing['timestamp']>=CACHE_SECONDS:
            try:
                data=await fetch_weather(location)
                existing={'timestamp':time.time(),'data':data}
                cache[location]=existing;status='fresh'
            except ProviderRateLimit as limited:
                backoff_until[location]=time.time()+limited.seconds
                if existing is None:
                    raise HTTPException(503,'Open-Meteo rate limit reached. Retry after the provider cooldown.',headers={'Retry-After':str(limited.seconds)})
                status='stale';error='Provider rate limit reached; showing the last cached response.'
            except (httpx.HTTPError,ValueError):
                if existing is None: raise HTTPException(503,'Open-Meteo is unavailable. Retry later; no readings were fabricated.')
                status='stale';error='Provider unavailable; showing the last cached response.'
        return {'provider':'Open-Meteo','attribution_url':'https://open-meteo.com/',
                'data_kind':'Weather-model estimates and forecasts; not a verified emergency',
                'location':LOCATIONS[location],'fetched_at':datetime.fromtimestamp(existing['timestamp'],timezone.utc).isoformat(),
                'age_seconds':round(time.time()-existing['timestamp']), 'cache_status':status,'error':error,
                'cache_ttl_seconds':CACHE_SECONDS,'data':existing['data']}

# Provider contract validation is separate from transport for direct unit testing.
from pydantic import BaseModel,ConfigDict,Field,model_validator

class CurrentConditions(BaseModel):
    model_config=ConfigDict(extra='allow',allow_inf_nan=False)
    time:str
    temperature_2m:float
    relative_humidity_2m:float=Field(ge=0,le=100)
    precipitation:float=Field(ge=0)
    rain:float=Field(ge=0)
    weather_code:int
    wind_speed_10m:float=Field(ge=0)
    wind_gusts_10m:float|None=Field(default=None,ge=0)
    surface_pressure:float|None=Field(default=None,gt=0)

class HourlyConditions(BaseModel):
    model_config=ConfigDict(extra='allow',allow_inf_nan=False)
    time:list[str]=Field(min_length=1)
    temperature_2m:list[float]
    relative_humidity_2m:list[float]
    precipitation_probability:list[float]
    precipitation:list[float]
    rain:list[float]
    wind_speed_10m:list[float]
    visibility:list[float|None]|None=None
    @model_validator(mode='after')
    def matching_arrays(self):
        for key in ('temperature_2m','relative_humidity_2m','precipitation_probability','precipitation','rain','wind_speed_10m'):
            if len(getattr(self,key))!=len(self.time):raise ValueError('Weather arrays have inconsistent lengths')
        if self.visibility is not None and len(self.visibility)!=len(self.time):raise ValueError('Visibility array has inconsistent length')
        return self

class DailyConditions(BaseModel):
    model_config=ConfigDict(extra='allow',allow_inf_nan=False)
    time:list[str]
    temperature_2m_max:list[float|None]
    temperature_2m_min:list[float|None]
    precipitation_sum:list[float|None]
    wind_gusts_10m_max:list[float|None]
    @model_validator(mode='after')
    def matching_arrays(self):
        for key in ('temperature_2m_max','temperature_2m_min','precipitation_sum','wind_gusts_10m_max'):
            if len(getattr(self,key))!=len(self.time):raise ValueError('Daily weather arrays have inconsistent lengths')
        return self

class ProviderWeather(BaseModel):
    model_config=ConfigDict(extra='allow')
    current:CurrentConditions
    hourly:HourlyConditions
    daily:DailyConditions|None=None
    daily_units:dict[str,str]|None=None
    current_units:dict[str,str]
    hourly_units:dict[str,str]
    timezone:str

def validate_weather(data):return ProviderWeather.model_validate(data).model_dump()
