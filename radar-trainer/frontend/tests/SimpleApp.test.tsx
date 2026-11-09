import React from 'react';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import SimpleApp from '../src/SimpleApp';
import type {NavData} from '../src/types';

const nav: NavData = {range_nm:25,center:[0,0],waypoints:[],fixes:[],routes:[],sector:[],airports:[],
  navaids:[{name:'Test VOR',type:'vor',x:1,y:1}],
  profile:{icao:'TEST',name:'Test airport',elevation_ft:0,range_nm:25,mode:'vectoring',approach:null,
    runway:{name:'09/27',length_m:2000,width_m:45,ends:[]},training:{},aircraft:{callsign:'AFR123'},examples:[]}};
vi.mock('../src/useSim',()=>({useSim:()=>({connection:'connected',state:{aircraft:[],paused:true,sim_alive:true},stateRef:{current:{}},log:[],providers:{},refreshHealth:vi.fn()})}));
vi.mock('../src/api',()=>({api:{nav:async()=>nav}}));
vi.mock('../src/components/RadioPanel',()=>({default:()=>null}));
vi.mock('../src/components/RadarCanvas',()=>({default:({options}:{options:{hiddenMarkers:string[]}})=><output data-testid="hidden-markers">{JSON.stringify(options.hiddenMarkers)}</output>}));
afterEach(()=>{cleanup();localStorage.clear();vi.unstubAllGlobals();});

it('offers a collapsed legend with grouped controls, hide/show all and persisted visibility',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>({json:async()=>({airports:[{icao:'TEST',name:'Test airport'}]})})));
  const first=render(<SimpleApp/>);
  const vor=await screen.findByRole('checkbox',{name:/Navigation aids/,hidden:true});
  expect(screen.getByText(/Map layers/).closest('details')?.open).toBe(false);
  await waitFor(()=>expect((vor as HTMLInputElement).checked).toBe(false));
  fireEvent.click(vor);
  expect((vor as HTMLInputElement).checked).toBe(true);
  fireEvent.click(vor);
  await waitFor(()=>expect(screen.getByTestId('hidden-markers').textContent).toContain('navaid:Test VOR'));
  expect((screen.getByRole('checkbox',{name:/Radar guides/,hidden:true}) as HTMLInputElement).checked).toBe(true);
  expect(JSON.parse(localStorage.getItem('atc.mapLayers.v2.TEST')!)).toEqual(['navaids']);
  first.unmount();
  render(<SimpleApp/>);
  await waitFor(()=>expect((screen.getByRole('checkbox',{name:/Navigation aids/,hidden:true}) as HTMLInputElement).checked).toBe(false));
  fireEvent.click(screen.getByRole('button',{name:'Hide all',hidden:true}));
  expect(screen.getAllByRole('checkbox',{hidden:true}).every(box=>!(box as HTMLInputElement).checked)).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Show all',hidden:true}));
  expect(screen.getAllByRole('checkbox',{hidden:true}).every(box=>(box as HTMLInputElement).checked)).toBe(true);
});
