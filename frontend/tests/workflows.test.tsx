import React from 'react';
import {describe,it,expect,vi,beforeEach} from 'vitest';
import {render,screen,waitFor,within,fireEvent} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import * as Tooltip from '@radix-ui/react-tooltip';
import fixture from './engine.fixture.json';
import {CommandCenter} from '../src/pages/Operations';
import {Shell} from '../src/components/Shell';
import {VoiPanel} from '../src/components/EnginePanels';
import {CitizenObservations,Notifications} from '../src/pages/Community';
import type {EngineState,Config} from '../src/types';
import {api} from '../src/lib/utils';

const mocked=vi.hoisted(()=>({context:{} as Record<string,unknown>,optIn:vi.fn(),support:vi.fn(async()=>({supported:true,reason:'Test browser support'}))}));
vi.mock('../src/context',async importOriginal=>({...await importOriginal<object>(),useApp:()=>mocked.context}));
vi.mock('../src/lib/utils',async importOriginal=>({...await importOriginal<object>(),api:vi.fn()}));
vi.mock('../src/lib/firebase',()=>({pushSupport:mocked.support,initializeForeground:vi.fn(async()=>()=>{}),optIn:mocked.optIn,optOut:vi.fn()}));
vi.mock('../src/components/CityMap',()=>({CityMap:()=>null}));
vi.mock('../src/lib/env',()=>({firebaseConfigured:true,mapKey:'test-only-public-key'}));
const state=fixture.state as EngineState;
beforeEach(()=>{mocked.context={state,config:fixture.config as unknown as Config,mode:'simulation',setMode:vi.fn(),city:'nagpur',setCity:vi.fn(),locations:{nagpur:{name:'Nagpur, India',latitude:21.1,longitude:79.1}},page:'Command Center',navigate:vi.fn(),connected:true,loading:false,error:'',message:'',clearError:vi.fn(),notify:vi.fn(),busy:false,command:vi.fn()};vi.mocked(api).mockImplementation(async(path)=>{if(path.startsWith('notifications/requests'))return [] as never;if(path.startsWith('notifications/status'))return {registered:false,server_credentials_configured:false,server_sdk_installed:false,sender_status:'not configured',detail:'Credentials missing',project_id:'sentinel-zero-c95fb'} as never;if(path==='citizen')return {effective_minute:4} as never;return {} as never});Object.defineProperty(window,'Notification',{configurable:true,value:{permission:'default',requestPermission:vi.fn()}})});
function wrapper(children:React.ReactNode){const query=new QueryClient({defaultOptions:{queries:{retry:false}}});return render(<QueryClientProvider client={query}><Tooltip.Provider>{children}</Tooltip.Provider></QueryClientProvider>)}

describe('Data-mode boundaries',()=>{
 it('shows simulation controls in Simulation Lab',()=>{wrapper(<Shell><p>Page content</p></Shell>);expect(screen.getByLabelText('Simulation scenario')).toBeTruthy();expect(screen.getByRole('button',{name:'Step',exact:true}).hasAttribute('disabled')).toBe(false)});
 it('hides simulation controls and labels Live Observations as context only',()=>{mocked.context.mode='live';wrapper(<Shell><p>Live context</p></Shell>);expect(screen.queryByLabelText('Simulation scenario')).toBeNull();expect(screen.getByText('External context only. No verified hazard assessment.')).toBeTruthy()});
 it('disables stepping at the end of an episode',()=>{mocked.context.state={...state,current:{...state.current,minute:18}};wrapper(<Shell><p>Completed run</p></Shell>);expect(screen.getByRole('button',{name:'Step',exact:true}).hasAttribute('disabled')).toBe(true);expect(screen.getByRole('button',{name:'Run',exact:true}).hasAttribute('disabled')).toBe(true)});
});

describe('Citizen consent and real pipeline contract',()=>{
 it('does not submit before explicit safe-location consent',async()=>{wrapper(<CitizenObservations/>);await userEvent.click(screen.getByRole('button',{name:'Submit observation',exact:true}));expect(await screen.findByText('Confirm that you can answer from your current safe location.')).toBeTruthy();expect(vi.mocked(api).mock.calls.some(([path])=>path==='citizen')).toBe(false)});
 it('submits an opt-in cannot-determine report and displays the backend effective minute',async()=>{wrapper(<CitizenObservations/>);await userEvent.click(screen.getByLabelText('I am answering from my current safe location and understand this is a simulation.'));await userEvent.click(screen.getByRole('button',{name:'Submit observation',exact:true}));expect(await screen.findByText('Observation received.')).toBeTruthy();const call=vi.mocked(api).mock.calls.find(([path])=>path==='citizen');expect(call?.[1]).toMatchObject({zone_id:'river',answer:'unknown'});expect(screen.getByText(/Queued for simulated minute/).textContent).toContain('4')});
});

describe('Transparent verification and notification behavior',()=>{
 it('renders calculated check values from a real engine fixture',async()=>{wrapper(<VoiPanel receipt={state.current} full/>);await userEvent.click(screen.getByText('Independent water sensor',{exact:false}).closest('summary')!);const check=state.current.voi.checks[0];expect(screen.getByText(check.evsi.toFixed(3))).toBeTruthy();expect(within(screen.getByText('Independent water sensor',{exact:false}).closest('details')!).getByText(/Net value = information value/)).toBeTruthy()});
 it('never requests browser notification permission on page load and disables unconfigured sends',async()=>{wrapper(<Notifications/>);await waitFor(()=>expect(screen.getByText('Supported',{exact:false})).toBeTruthy());expect(Notification.requestPermission).not.toHaveBeenCalled();expect(mocked.optIn).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Send FCM test to this browser',exact:true}).hasAttribute('disabled')).toBe(true)});
});


describe('Command Center hierarchy',()=>{
 it('puts the recommendation before probabilities and keeps diagnostics expandable',async()=>{
  wrapper(<CommandCenter/>);
  const action=screen.getByRole('heading',{name:state.current.decision.action,exact:true});
  const probabilities=screen.getByRole('heading',{name:/03 \/ Four possible explanations/});
  expect(action.compareDocumentPosition(probabilities)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.queryByRole('heading',{name:'Evidence timeline',exact:true})).toBeNull();
  await userEvent.click(screen.getByText('Evidence and source diagnostics',{exact:true}));
  expect(screen.getByRole('heading',{name:'Evidence timeline',exact:true})).toBeTruthy();
 });
});
