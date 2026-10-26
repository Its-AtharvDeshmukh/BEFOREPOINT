import React,{Suspense,lazy,Component,type ReactNode} from 'react';
import {createRoot} from 'react-dom/client';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import * as Tooltip from '@radix-ui/react-tooltip';
import {ApplicationProvider,useApp} from './context';
import {Shell,allPages} from './components/Shell';
import {Loading,Empty,Button} from './components/ui';
import './style.css';
const Flagships=()=>import('./pages/Flagships');
const Operations=()=>import('./pages/Operations');const Intelligence=()=>import('./pages/Intelligence');const Validation=()=>import('./pages/Validation');const Community=()=>import('./pages/Community');const System=()=>import('./pages/System');
const pages:Record<string,React.LazyExoticComponent<React.ComponentType>>={
 'Command Center':lazy(()=>Operations().then(m=>({default:m.CommandCenter}))),
 'Live Conditions':lazy(()=>Operations().then(m=>({default:m.LiveConditions}))),
 'City Intelligence':lazy(()=>Operations().then(m=>({default:m.CityIntelligence}))),
 'PROVE ME WRONG':lazy(()=>Flagships().then(m=>({default:m.ProveMeWrong}))),
 'CASCADE CUT':lazy(()=>Flagships().then(m=>({default:m.CascadeCut}))),
 'INVISIBLE LIFELINES':lazy(()=>Flagships().then(m=>({default:m.InvisibleLifelines}))),
 'Twin Test':lazy(()=>Validation().then(m=>({default:m.TwinTest}))),
 'Evaluation':lazy(()=>Validation().then(m=>({default:m.EvaluationPage}))),
 'Forecast Receipts':lazy(()=>Validation().then(m=>({default:m.ForecastReceipts}))),
 'Citizen Observations':lazy(()=>Community().then(m=>({default:m.CitizenObservations}))),
 'Notifications':lazy(()=>Community().then(m=>({default:m.Notifications}))),
 'Integrations':lazy(()=>System().then(m=>({default:m.Integrations}))),
 'Model & Assumptions':lazy(()=>System().then(m=>({default:m.ModelAssumptions}))),
 'Settings':lazy(()=>System().then(m=>({default:m.SettingsPage})))
};
class ErrorBoundary extends Component<{children:ReactNode},{error:string}>{state={error:''};static getDerivedStateFromError(error:Error){return {error:error.message}}render(){return this.state.error?<div className="fatal-error"><h1>Something interrupted the workspace.</h1><p>{this.state.error}</p><Button onClick={()=>location.reload()}>Reload application</Button></div>:this.props.children}}
function Workspace(){const {page,mode,setMode,navigate,loading,state}=useApp();const Page=pages[page];const simulated=['PROVE ME WRONG','CASCADE CUT','INVISIBLE LIFELINES'];return <Shell>{loading?<Loading label="Connecting to the crisis intelligence engine…"/>:!state?<Empty title="The local backend is unavailable" description="Start the FastAPI server and reload this page."/>:!allPages.includes(page as typeof allPages[number])||!Page?<Empty title="Page not found" action={<Button onClick={()=>navigate('Command Center')}>Open Command Center</Button>}/>:mode==='live'&&simulated.includes(page)?<Empty title="This feature requires simulated crisis evidence" description="Live Observations contains only external context. No verified live crisis model or infrastructure statuses are connected." action={<Button variant="default" onClick={()=>setMode('simulation')}>Open in Simulation Lab</Button>}/>:<ErrorBoundary key={page}><Suspense fallback={<Loading label="Opening workspace page…"/>}><Page/></Suspense></ErrorBoundary>}</Shell>}
window.addEventListener('vite:preloadError',event=>{const last=Number(sessionStorage.getItem('sentinel-chunk-reload')||0);if(Date.now()-last>10000){event.preventDefault();sessionStorage.setItem('sentinel-chunk-reload',String(Date.now()));location.reload()}});
const queryClient=new QueryClient({defaultOptions:{queries:{retry:1,refetchOnWindowFocus:false}}});
document.documentElement.dataset.motion=localStorage.getItem('sentinel-reduced-motion')==='true'?'reduced':'standard';document.documentElement.dataset.density=localStorage.getItem('sentinel-density')||'comfortable';
createRoot(document.getElementById('root')!).render(<React.StrictMode><ErrorBoundary><QueryClientProvider client={queryClient}><Tooltip.Provider delayDuration={200}><ApplicationProvider><Workspace/></ApplicationProvider></Tooltip.Provider></QueryClientProvider></ErrorBoundary></React.StrictMode>);
