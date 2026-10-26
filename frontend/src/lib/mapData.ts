import type {FeatureCollection,Point,Polygon,LineString} from 'geojson';
import type {EngineState,Config,Location} from '../types';
export const placements:Record<string,[number,number]>={rainfall:[-.014,.027],drainage:[-.008,.012],gateway:[.006,.008],underpass:[-.003,-.005],junction:[.017,.012],substation:[-.017,-.015],hospital:[.029,.026],dispatch:[.031,.002],alternate_road:[.036,-.012]};
const kindNodes:Record<string,string>={rain_high:'rainfall',water_high:'drainage',water_normal:'drainage',gateway_down:'gateway',gateway_up:'gateway',road_closed:'underpass',traffic_slow:'junction',power_loss:'substation',hospital_surge:'hospital',dispatch_delay:'dispatch'};
export type MapLayer='observations'|'network'|'forecasts'|'zones'|'unknown';
export const intelligenceLayers:{id:MapLayer,label:string,description:string,color:string}[]=[
 {id:'observations',label:'Reported observations',description:'Available replay reports at illustrative component locations.',color:'#66d8c1'},
 {id:'network',label:'Infrastructure network',description:'Configured assets and dependency links; not surveyed installations.',color:'#83b8ed'},
 {id:'forecasts',label:'Predicted disruptions',description:'Domino Clock probabilities and windows, not confirmed failures.',color:'#f5ba73'},
 {id:'zones',label:'Vulnerability zones',description:'Structural consequence index. Separate from hazard probability.',color:'#c4a5f5'},
 {id:'unknown',label:'Missing / unknown information',description:'Missing, stale or unobserved components. Never assumed safe.',color:'#a9b7c9'}];
export function mapData(state:EngineState|undefined,config:Config|undefined,loc:Location){
 const coordinate=(id:string):[number,number]=>[loc.longitude+placements[id][0],loc.latitude+placements[id][1]];
 const current=state?.current;const minute=current?.minute??0;
 // Use active evidence from the current receipt, not retracted historical reports.
 const reports=[...(current?.supporting_evidence||[])].sort((a,b)=>b.arrival_time-a.arrival_time||b.event_time-a.event_time);
 const nodes:FeatureCollection<Point>={type:'FeatureCollection',features:Object.keys(placements).map(id=>{
  const report=reports.find(e=>kindNodes[e.kind]===id);
  const source=report&&current?.sources.find(s=>s.source===report.source_id);
  const age=report?minute-report.event_time:null;
  const unavailable=source?.status==='missing'||source?.status==='stale'||(age!==null&&age>4);
  const observed=!!report&&!unavailable;
  const forecast=current?.forecasts.find(f=>f.component===id);
  return {type:'Feature',geometry:{type:'Point',coordinates:coordinate(id)},properties:{id,observed,forecast:!!forecast,unknown:!observed,missing:unavailable,status:unavailable?'Missing / stale report':observed?'Reported observation':'Not observed',report_kind:report?.kind||'',report_minute:report?.event_time??null,forecast_probability:forecast?.probability??null,forecast_window:forecast?.window.join('–')||''}};
 })};
 const offsets=[[-.03,.016],[0,-.013],[.033,.015]];
 const zones:FeatureCollection<Polygon>={type:'FeatureCollection',features:(current?.zones||[]).map((z,i)=>{const offset=offsets[i];if(!offset)return null;const x=loc.longitude+offset[0],y=loc.latitude+offset[1];return {type:'Feature' as const,geometry:{type:'Polygon' as const,coordinates:[[[x-.02,y-.015],[x+.02,y-.015],[x+.02,y+.015],[x-.02,y+.015],[x-.02,y-.015]]]},properties:{id:z.id,label:z.name,consequence:z.consequence_score}}}).filter((z):z is NonNullable<typeof z>=>!!z)};
 const edges:FeatureCollection<LineString>={type:'FeatureCollection',features:(config?.edges||[]).filter(e=>placements[e.from]&&placements[e.to]).map(e=>({type:'Feature',geometry:{type:'LineString',coordinates:[coordinate(e.from),coordinate(e.to)]},properties:{id:e.from+'>'+e.to,from:e.from,to:e.to,probability:e.probability,meaning:e.meaning}}))};
 return {nodes,zones,edges};
}
