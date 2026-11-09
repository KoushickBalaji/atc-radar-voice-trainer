import {expect, it, vi} from 'vitest';
import {drawScope, DEFAULT_RADAR_OPTIONS} from '../src/radar';
import type {NavData, SimState} from '../src/types';it('marks the exiting callsign even with ordinary labels hidden', () => {  const nav: NavData = {range_nm:25,center:[0,0],airports:[],waypoints:[],fixes:[],routes:[],sector:[]};  const state = {aircraft:[    {id:'INBOUND',x:0,y:0,gs:150,trk:90,control_area:{exit_in_s:null}},    {id:'OUTBOUND',x:2,y:1,gs:180,trk:90,control_area:{exit_in_s:20}},  ],conflicts:[],predicted:[]} as unknown as SimState;  const fillText = vi.fn(), arc = vi.fn();  const ctx = new Proxy({fillText,arc}, {get:(target,key)=>key in target ? target[key as keyof typeof target] : () => undefined}) as unknown as CanvasRenderingContext2D;  drawScope(ctx,{panX:0,panY:0,scale:10,w:500,h:500},nav,state,new Map(),null,0,    {...DEFAULT_RADAR_OPTIONS, labels:false, exitPulse:1});  expect(fillText.mock.calls.map(args=>args[0])).toContain('OUTBOUND EXIT');  expect(fillText.mock.calls.map(args=>args[0])).not.toContain('INBOUND EXIT');  expect(arc).toHaveBeenCalledWith(270,240,21,0,2*Math.PI);});

it('hides only fix/distance markers while retaining final line and aircraft state', () => {
  const nav: NavData = {range_nm:25,center:[0,0],airports:[],waypoints:[],fixes:[],routes:[],sector:[],
    approach:{runway:'23',course_true:225,course_magnetic:228,glide_deg:3,intercept_alt_ft:3200,
      line:[[0,0],[10,10]],fixes:[{name:'Published IF',x:8,y:8}],
      distance_markers:[{name:'5 NM THR',x:3,y:3}]}};
  const state = {aircraft:[],conflicts:[],predicted:[]} as unknown as SimState;
  const before = JSON.stringify({nav,state});
  const render = (shown: boolean) => {
    const text = vi.fn();
    const ctx = new Proxy({fillText:text}, {get: (target,key) => key in target ? target[key as keyof typeof target] : () => undefined}) as unknown as CanvasRenderingContext2D;
    drawScope(ctx,{panX:0,panY:0,scale:10,w:500,h:500},nav,state,new Map(),null,0,
      {...DEFAULT_RADAR_OPTIONS,approachMarkers:shown});
    return text.mock.calls.map(args=>args[0]);
  };
  expect(render(true)).toEqual(expect.arrayContaining(['Published IF','5 NM THR']));
  const hidden = render(false);
  expect(hidden).not.toContain('Published IF');
  expect(hidden).not.toContain('5 NM THR');
  expect(hidden).toContain('ILS 23 · 228°M · 3° GS');
  expect(JSON.stringify({nav,state})).toBe(before);
});


it('toggles individual references independently and can hide every map marker without changing data', async () => {
  const {mapMarkers, hiddenMarkerIds} = await import('../src/mapMarkers');
  const nav: NavData = {range_nm:25,center:[0,0],airports:[{name:'Airport',x:0,y:0}],waypoints:[],fixes:[],routes:[],sector:[],
    runways:[{name:'05/23',length_m:2990,width_m:45,ends:[{name:'05',x:0,y:0},{name:'23',x:1,y:1}]}],
    navaids:[{name:'VOR',x:1,y:2}],
    msaw:{source:{chart:'Test',effective_date:'2026-01-01'},regions:[{id:'east',minimum_ft:3200,points:[[0,0],[1,1]],label:[1,0]}]},
    approach:{runway:'23',course_true:225,course_magnetic:228,glide_deg:3,intercept_alt_ft:3200,
      line:[[0,0],[10,10]],fixes:[{name:'Published IF',x:8,y:8}],distance_markers:[{name:'5 NM THR',x:3,y:3}]}};
  const state = {aircraft:[],conflicts:[],predicted:[]} as unknown as SimState;
  const before = JSON.stringify({nav,state});
  const render = (hiddenMarkers: string[]) => {
    const text = vi.fn();
    const ctx = new Proxy({fillText:text}, {get:(target,key)=>key in target ? target[key as keyof typeof target] : () => undefined}) as unknown as CanvasRenderingContext2D;
    drawScope(ctx,{panX:0,panY:0,scale:10,w:500,h:500},nav,state,new Map(),null,0,{...DEFAULT_RADAR_OPTIONS,hiddenMarkers});
    return text.mock.calls.map(args=>args[0]);
  };
  expect(render(hiddenMarkerIds(nav, ['ils']))).not.toContain('Published IF');
  expect(render(hiddenMarkerIds(nav, ['ils']))).not.toContain('5 NM THR');
  expect(render(hiddenMarkerIds(nav, ['ils']))).toContain('VOR');
  expect(mapMarkers(nav).find(m=>m.id==='navaids')?.defaultHidden).toBe(true);
  expect(render(['navaid:VOR'])).not.toContain('VOR');
  expect(render(['navaid:VOR'])).toContain('Published IF');
  expect(render(['approachFix:Published IF'])).not.toContain('Published IF');
  expect(render(['approachFix:Published IF'])).toContain('5 NM THR');
  expect(render(['approach:line'])).toContain('Published IF');
  expect(render(['approach:line'])).not.toContain('ILS 23 \u00b7 228\u00b0M \u00b7 3\u00b0 GS');
  expect(render(hiddenMarkerIds(nav, mapMarkers(nav).map(m=>m.id)))).toEqual([]);
  expect(JSON.stringify({nav,state})).toBe(before);
});
