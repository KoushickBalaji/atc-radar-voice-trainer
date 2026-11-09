import type { NavData } from './types';

export interface MapMarker { id: string; label: string; symbol: string; color: string }

function individualMarkers(nav: NavData): MapMarker[] {
  const markers: MapMarker[] = [
    {id: 'scope:rings', label: 'Range rings / bearings', symbol: '◯', color: '#83a797'},
    {id: 'scope:center', label: 'Radar center', symbol: '+', color: '#a4d4b0'},
  ];
  if (nav.sector.length || nav.entry_areas?.length) markers.push({id: 'scope:sector', label: 'Entry envelope', symbol: '⬡', color: '#789586'});
  if (nav.control_areas?.length) markers.push({id: 'scope:control', label: 'Control areas', symbol: '⬡', color: '#789586'});
  if (nav.ats_routes?.length) markers.push({id:'ats:routes', label:'ATS routes', symbol:'┄', color:'#fff'});
  for (const p of nav.runways ?? []) markers.push({id: `runway:${p.name}`, label: `Runway ${p.name}`, symbol: '━', color: '#caa54e'});
  for (const p of nav.airports) markers.push({id: `airport:${p.name}`, label: p.name, symbol: '□', color: '#caa54e'});
  if (nav.approach) {
    markers.push({id: 'approach:line', label: `ILS ${nav.approach.runway} final line`, symbol: '┄', color: '#98e2eb'});
    for (const p of nav.approach.fixes) markers.push({id: `approachFix:${p.name}`, label: p.name, symbol: '×', color: '#98e2eb'});
    for (const p of nav.approach.distance_markers ?? []) markers.push({id: `distance:${p.name}`, label: p.name, symbol: '×', color: '#98e2eb'});
  }
  for (const p of nav.navaids ?? []) markers.push({id: `navaid:${p.name}`, label: p.name, symbol: p.type === 'ndb' ? '○' : '◇', color: '#98e2eb'});
  for (const p of nav.waypoints) markers.push({id: `waypoint:${p.name}`, label: p.name, symbol: '△', color: '#83a797'});
  for (const p of nav.fixes) markers.push({id: `fix:${p.name}`, label: p.name, symbol: '◇', color: '#b1c6aa'});
  for (const p of nav.msaw?.regions ?? []) markers.push({id: `msaw:${p.id}`, label: `SMAC ${p.id} · ${p.minimum_ft.toLocaleString()} ft`, symbol: '┄', color: '#ceb2e2'});
  for (const p of nav.holds ?? []) markers.push({id:'hold:'+p.id, label:p.fix, symbol:'↺', color:'#f3bb78'});
  return markers;
}


export interface MapLayer extends MapMarker { description: string; members: string[]; defaultHidden?: boolean }

export function mapMarkers(nav: NavData): MapLayer[] {
  const items = individualMarkers(nav);
  const definitions = [
    {id:'ats', label:'ATS routes', description:'Published routes and next fixes at the control-area edge', symbol:'┄', color:'#fff', prefixes:['ats:']},
    {id:'holds', label:'Holding patterns', description:'Published fixes and nominal racetracks', symbol:'↺', color:'#f3bb78', prefixes:['hold:']},
    {id:'ils', label:'ILS approach', description:'Final line, published fixes and threshold distances', symbol:'┄', color:'#98e2eb', prefixes:['approach:', 'approachFix:', 'distance:']},
    {id:'airport', label:'Airport', description:'Runway, airport position and name', symbol:'━', color:'#caa54e', prefixes:['runway:', 'airport:']},
    {id:'smac', label:'SMAC', description:'All minimum-altitude areas and labels', symbol:'⬡', color:'#ceb2e2', prefixes:['msaw:']},
    {id:'navaids', label:'Navigation aids', description:'VOR / NDB / ILS antennas, names and frequencies', symbol:'◇', color:'#98e2eb', prefixes:['navaid:'], defaultHidden:true},
    {id:'reference', label:'Radar guides', description:'Range rings, bearings and radar center', symbol:'◯', color:'#83a797', prefixes:['scope:rings', 'scope:center']},
    {id:'navigation', label:'Other navigation fixes', description:'Waypoints and en-route fixes', symbol:'△', color:'#b1c6aa', prefixes:['waypoint:', 'fix:']},
    {id:'boundary', label:'Entry envelope', description:'Lateral boundary used for training entry, not jurisdiction', symbol:'┄', color:'#789586', prefixes:['scope:sector'], defaultHidden:true},
    {id:'control', label:'Control areas', description:'Reviewed CTR / CTA outlines; see altitude limits in the console', symbol:'┄', color:'#789586', prefixes:['scope:control']},
  ];
  return definitions.map(d => ({...d, members:items.filter(m => d.prefixes.some(prefix => m.id.startsWith(prefix))).map(m => m.id)}))
    .filter(d => d.members.length > 0);
}

export function hiddenMarkerIds(nav: NavData, hiddenLayers: string[]): string[] {
  return mapMarkers(nav).filter(layer => hiddenLayers.includes(layer.id)).flatMap(layer => layer.members);
}
