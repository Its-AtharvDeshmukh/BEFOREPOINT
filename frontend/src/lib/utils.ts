import {clsx,type ClassValue} from 'clsx';
import {twMerge} from 'tailwind-merge';
export function cn(...inputs:ClassValue[]){return twMerge(clsx(inputs))}
export const H=['NOISE','SENSOR_FAILURE','ISOLATED_INCIDENT','CASCADING_CRISIS'];
export const colors=['#91a5bc','#b0a0ee','#e5bc72','#ef887d'];
export const nice=(s:string)=>s.replaceAll('_',' ').toLowerCase().replace(/\b\w/g,c=>c.toUpperCase());
export const pct=(v:number,d=1)=>`${(v*100).toFixed(d)}%`;
export const fmt=(v:number|null|undefined,d=3)=>v==null?'Unavailable':v.toFixed(d);
export const stamp=(s:string)=>new Date(s).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'});
export function download(data:unknown,name:string){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url)}
export function clientId(){let id=localStorage.getItem('sentinel-client');if(!id){id=crypto.randomUUID();localStorage.setItem('sentinel-client',id)}return id}
export async function api<T>(path:string,body?:unknown):Promise<T>{const response=await fetch('/api/'+path,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!response.ok){let detail='Request failed';try{const e=await response.json();detail=typeof e.detail==='string'?e.detail:JSON.stringify(e.detail)}catch{/* Keep bounded default. */}throw new Error(detail)}return response.json()}
