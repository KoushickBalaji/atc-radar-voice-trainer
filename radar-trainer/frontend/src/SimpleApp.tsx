import { useEffect, useState } from 'react';
import { ChevronDown, Info, Layers2 } from 'lucide-react';
import RadarCanvas from './components/RadarCanvas';
import AircraftHud from './components/AircraftHud';
import AirportInfo from './components/AirportInfo';
import WeatherStrip from './components/WeatherStrip';
import { useSim } from './useSim';
import { api } from './api';
import { sessionFetch as fetch } from './session';
import { DEFAULT_RADAR_OPTIONS } from './radar';
import { mapMarkers, hiddenMarkerIds } from './mapMarkers';
import type { NavData } from './types';

export default function SimpleApp({ onExit }: { onExit?: () => void } = {}) {
  const hub = useSim();
  const [nav, setNav] = useState<NavData>({ waypoints: [], airports: [], fixes: [], routes: [], sector: [], range_nm: 25, center: [0, 0] });
  const [airports, setAirports] = useState<{icao: string; name: string; mode?: string}[]>([]);
  const profile = nav.profile;
  const training = profile?.training;
  const handover = profile?.tower_handover;
  useEffect(() => { void fetch('/api/demo').then(r => r.json()).then(d => setAirports(d.airports)).catch(() => undefined); }, []);
  useEffect(() => { document.title = profile ? `Voice radar trainer - ${profile.name}` : 'Voice radar trainer'; }, [profile]);
  const [error, setError] = useState('');
  const [infoOpen, setInfoOpen] = useState(false);
  const [working, setWorking] = useState(false);
  const [hiddenMarkers, setHiddenMarkers] = useState<string[]>([]);
  const [loadedVisibility, setLoadedVisibility] = useState('');
  const visibilityKey = `atc.mapLayers.v2.${profile?.icao ?? ''}`;
  const markers = mapMarkers(nav);
  useEffect(() => {
    if (!profile) return;
    let hidden = mapMarkers(nav).filter(m => m.defaultHidden).map(m => m.id);
    try {
      const saved: unknown = JSON.parse(localStorage.getItem(visibilityKey) ?? 'null');
      if (Array.isArray(saved)) hidden = saved.filter((id): id is string => typeof id === 'string');

    } catch { /* Keep markers visible when storage is unavailable. */ }
    setHiddenMarkers(hidden);
    setLoadedVisibility(visibilityKey);
  }, [visibilityKey, profile, nav]);
  const changeMarkers = (hidden: string[]) => {
    setHiddenMarkers(hidden);
    try { localStorage.setItem(visibilityKey, JSON.stringify(hidden)); } catch { /* Session-only preference. */ }
  };
  useEffect(() => { if (hub.connection === 'connected') void api.nav().then(setNav).catch(e => setError(String(e))); }, [hub.connection, hub.state.airport_id]);
  const act = async (operation: () => Promise<unknown>) => {
    setWorking(true); setError('');
    try { await operation(); } catch(e) { setError(String(e)); } finally { setWorking(false); }
  };
  const traffic = hub.state.traffic;
  const [selected, setSelected] = useState<string | null>(null);
  const aircraft = hub.state.aircraft.find(a => a.id === selected) ?? hub.state.aircraft[0];
  const exiting = hub.state.aircraft.filter(a => a.control_area?.exit_in_s != null)
    .sort((a,b) => a.control_area!.exit_in_s! - b.control_area!.exit_in_s!);
  const msaw = aircraft?.msaw;
  const ils = traffic ? aircraft?.ils : hub.state.ils;
  const stagePaused = traffic ? traffic.complete : ['handoff_ready', 'approach_complete', 'complete', 'missed', 'missed_finished', 'missed_fix_altitude'].includes(ils?.phase ?? '');
  const missed = ils?.missed_approach;
  const startedMissed = ['going_around','missed_finished','missed_fix_altitude'].includes(ils?.phase ?? '');
  const connected = hub.connection === 'connected' && hub.state.sim_alive !== false;
  return <div className="flex h-full min-h-dvh flex-col">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-edge bg-panel px-5 py-4">
      <div>{onExit && <button className="text-xs underline" onClick={onExit}>← Scenario selection</button>}<h1 className="text-lg font-semibold">radar ATC</h1><p className="text-sm text-mut">{profile?.name ?? 'Loading airport'} ({profile?.icao ?? '…'}) <button type="button" className="airport-info-trigger" aria-label="Airport and exercise information" aria-haspopup="dialog" onClick={() => setInfoOpen(true)}><Info size={16} aria-hidden="true" /></button> · {traffic ? traffic.title : 'one aircraft'} · OpenAI radio</p></div>
      <div className="flex items-center gap-3 text-sm">
        {!onExit && <label className="text-xs">Airport
          <select aria-label="Airport" className="ml-2 rounded border border-edge bg-panel p-2" value={profile?.icao ?? ''} disabled={!profile || working || !connected}
            onChange={e => { const icao = e.target.value; void act(async () => {
              const r = await fetch('/api/demo/airport', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({icao})});
              if (!r.ok) throw new Error((await r.json()).detail);
              setNav(await api.nav()); hub.clearLog();
            }); }}>
            {!profile && <option value="">Loading…</option>}
            {airports.map(a => <option key={a.icao} value={a.icao}>{a.name} ({a.icao}){a.mode === 'vectoring' ? ' · no ILS' : ''}</option>)}
          </select>
        </label>}
        {!onExit && !!profile?.scenarios?.length && <label className="text-xs">Exercise
          <select aria-label="Exercise" className="ml-2 rounded border border-edge bg-panel p-2"
            value={traffic?.id ?? ''} disabled={!connected || working}
            onChange={e => { const scenario_id = e.target.value; void act(async () => {
              const r = await fetch('/api/demo/airport', {method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({icao:profile.icao, scenario_id})});
              if (!r.ok) throw new Error((await r.json()).detail);
              setSelected(null); hub.clearLog();
            }); }}>
            <option value="">Single aircraft</option>
            {profile.scenarios.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}
          </select>
        </label>}
        <span role="status">{!connected ? 'Connecting…' : traffic ? (traffic.complete ? 'Exercise complete' : (hub.state.paused ? 'Paused · ' : '') + traffic.flights.filter(f => f.phase === 'complete').length + ' / ' + traffic.flights.length + ' complete') : ils?.phase === 'missed_finished' ? 'Missed approach complete' : ils?.phase === 'missed_fix_altitude' ? 'Review altitude at the fix' : ils?.phase === 'complete' ? 'Approach exercise complete' : ils?.phase === 'missed' ? 'Approach tracking lost' : ils?.phase === 'handoff_ready' ? 'Paused — issue tower handoff' : hub.state.paused ? 'Paused — ready for practice' : 'Simulation running'}</span>
        <button className="rounded bg-acc px-4 py-2 text-white disabled:opacity-50" disabled={!connected || working || stagePaused}
          onClick={() => void act(hub.state.paused ? api.resume : api.pause)}>{hub.state.paused ? 'Start / Resume' : 'Pause'}</button>
        <button type="button" className={`rounded border px-3 py-2 disabled:opacity-50 ${hub.state.speed > 1 ? 'border-acc bg-acc text-white' : 'border-edge'}`}
          aria-label={`Simulation speed: ${hub.state.speed}×`}
          title={`Switch to ${hub.state.speed === 1 ? 2 : hub.state.speed === 2 ? 4 : 1}× speed`} disabled={!connected || working}
          onClick={() => void act(() => api.setSpeed(hub.state.speed === 1 ? 2 : hub.state.speed === 2 ? 4 : 1))}>{hub.state.speed}×</button>
        <button className="rounded border border-edge px-3 py-2" disabled={working || !connected}
          onClick={() => void act(async () => { const r = await fetch('/api/demo/reset', { method: 'POST' }); if (!r.ok) throw new Error((await r.json()).detail); hub.clearLog(); })}>Reset exercise</button>
        {!traffic && profile?.approach && missed && <>
              <button type="button" className="rounded border border-edge px-3 py-2 disabled:opacity-50" aria-pressed={!!ils?.go_around_on_handoff} title="Arm a go-around at tower handoff; click again to cancel"
                disabled={!connected || working || !['awaiting_clearance','armed','localizer','glideslope','handoff_ready'].includes(ils?.phase ?? '') || hub.state.airport_id !== profile.icao}
                onClick={() => void act(async () => {
                  const r = await fetch('/api/demo/go-around', {method:'POST',headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({icao:profile.icao, runway:missed.runway, approach_id:missed.approach_id, callsign:profile.aircraft.callsign, armed:!ils?.go_around_on_handoff})});
                  if (!r.ok) throw new Error((await r.json()).detail);
                })}>{ils?.go_around_on_handoff ? 'Go-around armed · cancel' : 'Go-around on handoff'}</button>
        </>}
      </div>
    </header>
    {profile && (!hub.state.airport_id || hub.state.airport_id === profile.icao) &&
      <WeatherStrip key={profile.icao} icao={profile.icao} />}
    {(error || hub.state.last_error) && <p role="alert" className="bg-red-50 p-3 text-dang">{error || hub.state.last_error}</p>}
    <div className="workspace">
      <main className="radar-stage" aria-label={`${profile?.name ?? "Airport"} radar`}>
        <RadarCanvas key={profile?.icao + (traffic?.id ?? '')} stateRef={hub.stateRef} nav={nav} selected={aircraft?.id ?? null} onSelect={setSelected}
          placeMode={null} onPlace={() => undefined} options={{...DEFAULT_RADAR_OPTIONS, hiddenMarkers: hiddenMarkerIds(nav, loadedVisibility === visibilityKey ? hiddenMarkers : markers.filter(m => m.defaultHidden).map(m => m.id))}} />
        <p className="pointer-events-none absolute left-5 top-4 text-sm text-green-100">{profile?.name.toUpperCase()} · {profile?.icao} · {nav.range_nm} NM<br/><span className="text-xs">Scroll to zoom · drag to pan</span></p>
        <details className="radar-controls group absolute bottom-5 left-5 w-56 max-w-[calc(100%-2.5rem)] overflow-hidden rounded-lg text-[13px] shadow-lg">
          <summary className="flex list-none items-center gap-2 px-3 py-2.5 font-medium [&::-webkit-details-marker]:hidden">
            <Layers2 size={15} aria-hidden="true" />
            <span className="flex-1">Map layers</span>
            <ChevronDown size={14} aria-hidden="true" className="transition-transform group-open:rotate-180" />
          </summary>
          <div className="flex items-center justify-end gap-1 border-t border-white/10 px-2 py-1">
            <button className="rounded px-2 py-1 text-xs opacity-75 hover:opacity-100" onClick={() => changeMarkers([])}>Show all</button>
            <span aria-hidden="true" className="text-white/20">/</span>
            <button className="rounded px-2 py-1 text-xs opacity-75 hover:opacity-100" onClick={() => changeMarkers(markers.map(m => m.id))}>Hide all</button>
          </div>
          <div className="max-h-[40vh] overflow-y-auto px-1.5 pb-1.5">
            {markers.map(marker => <label key={marker.id} className="flex min-h-8 cursor-pointer items-center gap-2 rounded px-2 hover:bg-white/5">
              <span aria-hidden="true" className="inline-block w-4 text-center" style={{color: marker.color}}>{marker.symbol}</span>
              <span className="flex-1">{marker.label}</span>
              <input type="checkbox" className="h-3.5 w-3.5 shrink-0 cursor-pointer" checked={!hiddenMarkers.includes(marker.id)} onChange={e => changeMarkers(e.target.checked
                ? hiddenMarkers.filter(id => id !== marker.id) : [...hiddenMarkers, marker.id])} />
            </label>)}
          </div>
        </details>
      </main>
      <AircraftHud key={profile?.icao} hub={hub} nav={nav} selection={selected} onSelection={setSelected} />
    </div>
    <AirportInfo open={infoOpen} onClose={() => setInfoOpen(false)} title={`${profile?.name ?? 'Airport'} · Exercise information`}>

          {traffic && <section className="text-sm"><h2 className="font-semibold">{traffic.title}</h2><p>{traffic.brief}</p></section>}
          <section className="text-sm"><h2 className="font-semibold">{profile?.name} · {profile?.icao}</h2><p>RWY {profile?.runway.name} · {profile?.runway.length_m.toLocaleString()} × {profile?.runway.width_m} m · elevation {profile?.elevation_ft.toLocaleString()} ft</p><p className="text-xs text-mut">{profile?.runway.ends.every(e => e.bearing_magnetic_chart != null) && <>Chart bearings: {profile.runway.ends.map(e => `${e.bearing_magnetic_chart!.toString().padStart(3,'0')}°`).join(' / ')} magnetic. </>}Simulator headings use true north.</p>{profile?.scope_note && <p className="mt-2 text-xs text-mut">{profile.scope_note}</p>}</section>
          {!traffic && profile?.entry && <p className="text-xs text-mut">{profile.entry.status === 'boundary_based'
            ? `Entry: ${profile.entry.buffer_nm} NM outside ${profile.entry.boundary}. ${profile.entry.incomplete ? 'Some published boundary details remain unmodeled.' : ''}`
            : profile.entry.note}</p>}
          <section aria-label="Control area" className="rounded border border-edge p-3 text-sm" role="status">
            <h2 className="font-semibold">Control area</h2>
            {connected && exiting.length > 0 && <div className="my-2 rounded border border-amber-500 bg-amber-50 p-2 text-amber-950">
              <strong>Projected airspace exit · {traffic ? 'review transfer or reroute' : 'reroute'}</strong>
              <ul>{exiting.map(a => <li key={a.id}>{a.id} · {a.control_area!.exit_in_s} s to exit</li>)}</ul>
            </div>}
            <p>{!connected ? 'Monitoring unavailable — simulator disconnected.' :
              aircraft?.control_area?.status === 'inside' ? `Within ${aircraft.control_area.areas.join(', ')}.` :
              aircraft?.control_area?.status === 'outside' ? 'Outside the configured control volumes.' :
              aircraft?.control_area?.status === 'uncertain' ? 'Lateral position matches; altitude reference or operating hours cannot be verified.' :
              aircraft?.control_area?.status === 'invalid_position' ? 'Position or altitude unavailable.' :
              'Reviewed control-area data has not been configured for this airport.'}</p>
            {!!aircraft?.control_area?.uncertain.length && <p className="text-xs">Unverified: {aircraft.control_area.uncertain.join(', ')}.</p>}
            {nav.control_areas?.map(a => <p key={a.name} className="mt-1 text-xs">{a.name}: {[a.lower, a.upper].map(l => l.reference === 'AMSL' ? `${l.value} ft AMSL` : l.reference === 'FL' ? `FL ${l.value}` : l.reference).join(' – ')}</p>)}
            {!!nav.control_areas?.length && <p className="mt-2 text-xs text-mut">Outlines show lateral extents; altitude limits and CTR exclusions determine membership. FL limits require pressure altitude, which this simulator does not currently supply. This status does not grant clearance or trigger handoff. Map visibility does not affect monitoring.</p>}
          </section>
          <section aria-label="Minimum safe altitude warning" role={msaw?.status === 'warning' ? 'alert' : 'status'}
            className={`rounded border p-3 text-sm ${msaw?.status === 'warning' ? 'border-red-600 bg-red-50 text-red-800' : 'border-edge'}`}>
            <h2 className="font-semibold">{msaw?.status === 'warning' ? 'MSAW — LOW ALTITUDE' : 'Minimum safe altitude'}</h2>
            <p>{!connected ? 'Monitoring unavailable — simulator disconnected.' : !msaw ? 'Waiting for aircraft position…' :
              msaw.status === 'warning' ? `${aircraft?.id}: ${Math.round(aircraft?.alt_ft ?? 0).toLocaleString()} ft; minimum ${msaw.minimum_ft?.toLocaleString()} ft AMSL. ${Math.ceil(msaw.deficit_ft).toLocaleString()} ft below minimum.` :
              msaw.status === 'clear' ? `At or above the ${msaw.minimum_ft?.toLocaleString()} ft AMSL vectoring minimum here.` :
              msaw.status === 'approach_suspended' ? 'SMAC check suspended while the aircraft tracks the expected ILS profile. Monitoring resumes on deviation or go-around.' :
              msaw.status === 'outside_coverage' ? 'Outside the charted SMAC coverage — minimum unknown.' :
              msaw.status === 'invalid_position' ? 'Monitoring unavailable — invalid aircraft position or altitude.' :
              'SMAC data has not been configured for this airport.'}</p>
            {nav.msaw && <p className="mt-2 text-xs">Purple boundaries: SMAC areas · {nav.msaw.source.chart} · {nav.msaw.source.effective_date}. Training altitude check; no terrain or predictive warning.</p>}
          </section>
          {!traffic && <>{!!nav.holds?.length && <section aria-label="Published holding" className="rounded border border-edge p-3 text-sm">
            <h2 className="font-semibold">Published holding</h2>
            {nav.holds.map(p => <p key={p.id}>{p.fix} · {String(p.inbound_magnetic_deg).padStart(3,'0')}°M inbound · {p.turn} turns · {p.leg_seconds} s · minimum {p.minimum_ft.toLocaleString()} ft · maximum {p.max_kias} KIAS</p>)}
            {ils?.holding ? <p role="status">{ils.message} · {ils.holding.altitude_ft.toLocaleString()} ft · {ils.holding.circuits} completed circuits{ils.holding.entry && ' · '+ils.holding.entry+' entry'}{ils.holding.expected && ' · expect clearance '+ils.holding.expected+' UTC'}. Issue a heading to leave the hold.</p> :
              <p className="mt-1 text-xs text-mut">By voice, clear the aircraft to the fix and say “hold as published.”</p>}
          </section>}
          {profile?.approach && <section aria-label="Missed approach exercise" className="rounded border border-edge p-3 text-sm">
            <h2 className="font-semibold">Missed approach</h2>
            {missed ? <>
              <p>{missed.name} · maximum {missed.max_kias} KIAS</p>
              <ol className="ml-5 list-decimal">{missed.legs.map(leg => <li key={leg}>{leg}</li>)}</ol>
              <p className="my-2">{Object.keys(missed.overrides).length ? 'ATC assignments: ' + Object.entries(missed.overrides).map(([axis,v]) =>
                axis === 'HDG' ? 'heading '+v+'°' : axis === 'ALT' ? v+' ft' : v+' kt').join(', ') : 'Published procedure selected.'}</p>
              {startedMissed ? <p role="status" className="my-2 font-semibold">{ils?.message}</p> :
                <p className="text-xs text-mut">To assign an alternative in advance, say “{profile.examples[0]?.split(',')[0]}, on missed approach fly heading two seven zero.”</p>}

              <p className="mt-1 text-xs text-mut">{missed.source}</p>
            </> : <p>No missed approach has been configured for this runway and approach variant.</p>}
          </section>}
          {profile?.approach ? !startedMissed && !ils?.holding && <section aria-label="ILS capture objective" className="rounded border border-edge p-3 text-sm" role="status">
            <h2 className="font-semibold">RWY{profile.approach.runway} ILS · {ils?.phase === 'complete' ? 'SUCCESS' : ils?.phase?.replaceAll('_', ' ').toUpperCase() ?? 'AWAITING CLEARANCE'}</h2>
            <p>{ils?.message ?? 'Vector the aircraft to capture the localizer, then the glide slope from below.'}</p>
            {ils?.along_nm != null && <p className="mt-2 font-mono text-xs">To threshold {ils.along_nm} NM · off final {Math.abs(ils.cross_nm ?? 0).toFixed(2)} NM<br/>Intercept {ils.intercept_deg}° · GS error {ils.glide_error_ft} ft<br/>Stable {ils.stable_s ?? 0}/{training?.stable_seconds ?? '—'} s</p>}
            <p className="mt-2">1. Clear ILS RWY{profile.approach.runway} by voice.<br/>2. Establish localizer and glide-slope tracking.<br/>3. {handover ? `Hand over to tower on the glide slope. The pilot asks at ${handover.request_nm} NM and goes around at ${handover.go_around_nm} NM if still awaiting handover.` : 'At the training pause, hand over to tower.'}</p>
            <p className="mt-2 text-xs text-mut">Say “{profile.examples[0]?.split(',')[0]}, cleared ILS approach runway {profile.approach.runway}.” Issue clearance separately from vectors.</p>
            <p className="mt-2 text-xs">{profile.approach.intercept_alt_ft >= 5000
              ? 'This profile’s intercept level is above the trainer’s 5,000 ft approach-clearance limit. Use it for vectoring practice.'
              : <>At localizer capture, respond to the pilot with “{profile.examples[0]?.split(',')[0]}, runway {profile.approach.runway}, cleared to land.”</>}</p>
            {profile.tower ? <p className="mt-2 text-xs">Tower: {profile.tower.name} · {profile.tower.frequency_mhz} MHz. At handoff, say “{profile.examples[0]?.split(',')[0]}, contact tower {profile.tower.frequency_mhz.replace('.', ' decimal ')}.”</p> : <p>No verified tower channel: this exercise ends at stable tracking.</p>}
            <p className="mt-2 text-xs text-mut">Published fix references appear where configured. NM THR markers measure horizontal distance from the threshold; they are not published fixes or DME readings. Hiding markers affects display only.</p>
          </section> : profile && <section aria-label="Vectoring practice" className="rounded border border-edge p-3 text-sm" role="status">
            <h2 className="font-semibold">Vectoring practice · no ILS</h2>
            <p>Practice heading, altitude and speed instructions. This airport has no modeled ILS: there is no localizer or glide-slope capture, automatic approach, or ILS success score.</p>
            <p className="mt-2 text-xs text-mut">Exercise altitudes are practice settings, not published approach clearances. Other instrument procedures, visual approaches and landing are not simulated.</p>
          </section>}
          <section className="space-y-2 text-sm"><h2 className="font-semibold">Vectoring transmissions</h2>
            {nav.msaw && <p className="text-sm">Check the SMAC minimum before issuing a descent. {profile?.approach && <>Reach the {profile.approach.intercept_alt_ft.toLocaleString()} ft area before using the final-approach altitude example below. </>}A red MSAW alert calls for corrective vectoring or climb instructions.</p>}
            {profile?.examples.map(example => <p key={example}>“{example}”</p>)}
            <p className="text-mut">Select Enable microphone and allow access. When “Hold to talk” appears, hold V or the mic button while speaking. Release to send. Use headphones. You can issue approach clearance while paused.</p>
          </section>
          <section className="border-t border-edge pt-3 text-xs text-mut">{profile?.approach && <p>Training limits: ≤{training?.intercept_max_deg}° intercept, {profile.approach.intercept_alt_ft.toLocaleString()} ft ±{training?.altitude_tolerance_ft} ft, {training?.speed_min_kt}–{training?.speed_max_kt} kt. Capture localizer {training?.localizer_min_nm}–{training?.localizer_max_nm} NM before the threshold, then meet the {profile.approach.glide_deg}° glide slope from below. These tolerances are exercise settings, not chart minima. Terrain, full procedures and landing are not modeled.</p>}
            <p className="mt-2">AAI references: 12.17.1.3 (heading), 12.16.1.2 (level), 12.17.1.6 (speed). Feedback here reports command handling, not a competency score.</p>
          </section>

          </>}
    </AirportInfo>
  </div>;
}
