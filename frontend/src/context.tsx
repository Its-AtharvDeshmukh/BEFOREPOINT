import {createContext,useContext,useState,useEffect,type ReactNode} from 'react';
import {useQuery,useQueryClient,useMutation} from '@tanstack/react-query';
import type {Config,EngineState,Location} from './types';
import {api} from './lib/utils';
export type Mode='simulation'|'live'|'hybrid';
export const modeLabels={simulation:'Simulation Lab',live:'Live Observations',hybrid:'Hybrid Demo'};
type AppContext={state:EngineState|undefined,config:Config|undefined,connected:boolean,loading:boolean,error:string,message:string,notify:(text:string)=>void,clearError:()=>void,command:(path:string,body?:unknown)=>void,busy:boolean,mode:Mode,setMode:(mode:Mode)=>void,city:string,setCity:(city:string)=>void,locations:Record<string,Location>,page:string,navigate:(page:string)=>void,refreshSeconds:number,setRefreshSeconds:(v:number)=>void};
const Context=createContext<AppContext|null>(null);
const initialPage=()=>{try{return decodeURIComponent(location.hash.slice(1))||(location.pathname==='/citizen'?'Citizen Observations':'Command Center')}catch{return 'Command Center'}};
export function ApplicationProvider({children}:{children:ReactNode}){const query=useQueryClient();const [connected,setConnected]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState(''),[mode,setModeState]=useState<Mode>(()=>{const value=localStorage.getItem('sentinel-mode');return value==='live'||value==='hybrid'?value:'simulation'}),[city,setCityState]=useState(localStorage.getItem('sentinel-city')||'nagpur'),[page,setPage]=useState(initialPage),[refreshSeconds,setRefresh]=useState(Number(localStorage.getItem('sentinel-refresh'))||10);
const engine=useQuery({queryKey:['engine'],queryFn:()=>api<EngineState>('state'),refetchInterval:connected?false:refreshSeconds*1000});
const config=useQuery({queryKey:['config'],queryFn:()=>api<Config>('config'),staleTime:Infinity});
const locations=useQuery({queryKey:['locations'],queryFn:()=>api<Record<string,Location>>('locations'),staleTime:Infinity});
useEffect(()=>{const stream=new EventSource('/api/stream');stream.onopen=()=>setConnected(true);stream.onmessage=e=>{query.setQueryData(['engine'],JSON.parse(e.data));setConnected(true)};stream.onerror=()=>setConnected(false);return()=>stream.close()},[query]);
useEffect(()=>{const handler=()=>setPage(initialPage());window.addEventListener('hashchange',handler);return()=>window.removeEventListener('hashchange',handler)},[]);
const mutation=useMutation({mutationFn:({path,body}:{path:string,body:unknown})=>api<EngineState>(path,body),onSuccess:data=>{query.setQueryData(['engine'],data);setError('');setMessage('')},onError:e=>setError(e.message)});
function setMode(value:Mode){setModeState(value);localStorage.setItem('sentinel-mode',value)}
function setCity(value:string){setCityState(value);localStorage.setItem('sentinel-city',value)}
return <Context.Provider value={{state:engine.data,config:config.data,connected,loading:engine.isPending||config.isPending,error:error||engine.error?.message||config.error?.message||'',message,notify:setMessage,clearError:()=>setError(''),command:(path,body={})=>mutation.mutate({path,body}),busy:mutation.isPending,mode,setMode,city,setCity,locations:locations.data||{},page,navigate:value=>{setPage(value);location.hash=encodeURIComponent(value);window.scrollTo({top:0,behavior:'instant'})},refreshSeconds,setRefreshSeconds:v=>{setRefresh(v);localStorage.setItem('sentinel-refresh',String(v))}}}>{children}</Context.Provider>}
export function useApp(){const value=useContext(Context);if(!value)throw Error('Application provider missing');return value}
