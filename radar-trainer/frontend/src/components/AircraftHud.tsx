import { useState } from 'react';
import { AlertTriangle, ArrowDown, ArrowRight, ArrowUp, Radio } from 'lucide-react';
import type { Aircraft, NavData } from '../types';
import type { SimHub } from '../useSim';
import RadioPanel from './RadioPanel';
import MessageHistory from './MessageHistory';

type Filter = 'ALL' | 'ARR' | 'DEP' | 'ALERT';
const filters: Filter[] = ['ALL', 'ARR', 'DEP', 'ALERT'];
const labels = { ALL: 'All aircraft', ARR: 'Arrivals', DEP: 'Departures', ALERT: 'Aircraft with alerts' };
const heading = (value: number) => `${Math.round(value).toString().padStart(3, '0')}°`;
const altitude = (value: number | null | undefined) => value == null ? '—' : `${Math.round(value).toLocaleString()} ft`;

// Only the configured ILS exercise has a known inbound role. Vectoring traffic
// stays unclassified; vertical speed is not an arrival/departure indicator.
function role(a: Aircraft, nav: NavData): 'ARR' | 'DEP' | 'OVR' | null {
  if (a.role) return {arrival:'ARR',departure:'DEP',overflight:'OVR'}[a.role] as 'ARR' | 'DEP' | 'OVR';
  return nav.profile?.approach && a.id === nav.profile.aircraft.callsign ? 'ARR' : null;
}
function hasAlert(a: Aircraft, hub: SimHub) {
  return Boolean(a.alert || a.conflict || a.inzone || a.msaw?.status === 'warning' ||
    a.control_area?.exit_in_s != null ||
    hub.state.conflicts?.some(pair => pair.includes(a.id)) || hub.state.predicted?.some(p => p.pair.includes(a.id)));
}

export default function AircraftHud({ hub, nav, selection: externalSelection, onSelection }: {
  hub: SimHub; nav: NavData; selection?: string | null; onSelection?: (id:string | null) => void
}) {
  const [filter, setFilter] = useState<Filter>('ALL');
  const [localSelection, setLocalSelection] = useState<string | null>(null);
  const selection = externalSelection === undefined ? localSelection : externalSelection;
  const setSelection = onSelection ?? setLocalSelection;
  const matches = (a: Aircraft, f: Filter) => f === 'ALL' || (f === 'ALERT' ? hasAlert(a, hub) : role(a, nav) === f);
  const visible = hub.state.aircraft.filter(a => matches(a, filter))
    .sort((a, b) => Number(hasAlert(b, hub)) - Number(hasAlert(a, hub)) || a.id.localeCompare(b.id));
  const selected = visible.find(a => a.id === selection);
  const connected = hub.connection === 'connected' && hub.state.sim_alive !== false;
  return <aside className="console hud" aria-label="Aircraft HUD">
    <div className="hud-aircraft">
      <div className="hud-filters" role="group" aria-label="Filter aircraft">
        {filters.map(f => <button type="button" key={f} aria-label={labels[f]} aria-pressed={filter === f}
          className={`hud-filter ${f === 'ALERT' ? 'hud-alert-filter' : ''}`} onClick={() => setFilter(f)}>
          {f === 'ALERT' ? <><AlertTriangle size={12} aria-hidden="true" /> Alerts</> : f}
          <span>{hub.state.aircraft.filter(a => matches(a, f)).length}</span>
        </button>)}
      </div>
      <div className="hud-columns" aria-hidden="true"><span /><span>Callsign</span><span>Alt / Clrd</span><span>Spd</span><span>Hdg</span><span>State</span></div>
      <div className="hud-strips" role="group" aria-label="Aircraft list">
        {visible.map(a => {
          const alert = hasAlert(a, hub);
          const Trend = a.vs_fpm > 300 ? ArrowUp : a.vs_fpm < -300 ? ArrowDown : ArrowRight;
          return <button type="button" key={a.id} aria-label={`Select ${a.id}`} aria-expanded={selected?.id === a.id} aria-controls="hud-aircraft-detail"
            className={`hud-strip ${alert ? 'hud-strip-alert' : ''}`} onClick={() => setSelection(selection === a.id ? null : a.id)}>
            <span className="hud-dot" aria-hidden="true" />
            <strong>{a.id}</strong>
            <span className="hud-strip-alt" title={`Altitude ${altitude(a.alt_ft)}; cleared ${altitude(a.sel_alt_ft)}`}>
              <span>{(a.alt_ft / 1000).toFixed(1)}<Trend size={11} aria-hidden="true" /></span>
              <small>{a.sel_alt_ft == null ? '—' : (a.sel_alt_ft / 1000).toFixed(1)}</small>
            </span>
            <span title="Indicated airspeed, knots">{a.cas_kt ?? '—'}</span><span>{heading(a.hdg)}</span>
            <span className="hud-badge">{alert ? 'ALERT' : role(a, nav) ?? 'VECT'}</span>
          </button>;
        })}
        {!visible.length && <p className="hud-empty">{filter === 'ALL' ? 'Waiting for aircraft…' : `No ${filter === 'ALERT' ? 'aircraft with alerts' : labels[filter].toLowerCase()}.`}</p>}
      </div>
      {selected && <section id="hud-aircraft-detail" className="hud-detail" aria-label="Selected aircraft details">
        <div className="hud-detail-header"><span className="hud-dot" aria-hidden="true" /><div><h2>{selected.id}</h2><p>{selected.type || 'Aircraft'} · {selected.role ?? (role(selected, nav) === 'ARR' ? 'Arrival' : 'Vectoring')} · {connected ? 'Live' : 'Last known data'}</p></div>
          <span className="hud-runway">{selected.phase ? selected.phase.replaceAll('_',' ') : nav.profile?.approach ? `ILS ${nav.profile.approach.runway}` : nav.profile?.icao ?? '—'}</span></div>
        <dl className="hud-data">
          {[
            ['Altitude', altitude(selected.alt_ft)], ['Cleared to', altitude(selected.sel_alt_ft)],
            ['Airspeed', `${selected.cas_kt ?? '—'} kt`], ['Heading · true', heading(selected.hdg)],
            ['Vertical speed', `${Math.round(selected.vs_fpm).toLocaleString()} ft/min`], ['Groundspeed', `${selected.gs} kt`],
          ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
        </dl>
      </section>}
    </div>
    <section className="hud-messages" aria-labelledby="hud-messages-heading">
      <div className="hud-section-title"><h2 id="hud-messages-heading"><Radio size={13} aria-hidden="true" /> Messages</h2></div>
      <div className="hud-message-scroll" tabIndex={0} aria-label="Message history">
        {!connected && <div className="hud-message hud-warning" role="status"><strong>Monitoring unavailable</strong><p>Simulator {hub.connection === 'connecting' ? 'connecting' : 'disconnected'}. Aircraft data may be stale.</p></div>}
        {connected && hub.state.aircraft.map(a => <AircraftWarnings key={a.id} a={a} hub={hub} />)}
        {hub.state.last_error && <div className="hud-message hud-warning" role="alert">{hub.state.last_error}</div>}
        {hub.state.traffic && <div className="hud-message hud-objective" role="status">
          {hub.state.traffic.flights.map(f => <p key={f.callsign}><strong>{f.callsign}</strong> · {f.role} · {f.phase.replaceAll('_',' ')}{f.overdue && ' · transfer overdue at boundary'}</p>)}
          {selected?.ils && <p>{selected.ils.message}</p>}
        </div>}
        {hub.state.ils && (!selected || selected.id === nav.profile?.aircraft.callsign) && <div className="hud-message hud-objective" role="status"><strong>{nav.profile?.aircraft.callsign ?? 'Exercise'} · {hub.state.ils.phase.replaceAll('_', ' ')}</strong><p>{hub.state.ils.message}</p></div>}
        <MessageHistory hub={hub} selected={selected?.id ?? null} />
      </div>
    </section>
    <div className="hud-services" aria-label="Radio service status">
      {(['stt', 'llm', 'tts'] as const).map(p => <button key={p} type="button" onClick={() => void hub.refreshHealth()}
        aria-label={`${p.toUpperCase()} ${hub.providers[p] ? 'connected' : 'unavailable'}. Retry service check.`}
        className={hub.providers[p] ? 'hud-service-ok' : 'hud-service-off'}><span className="hud-dot" aria-hidden="true" />{p.toUpperCase()}</button>)}
      <span>Voice only · V to transmit</span>
    </div>
    <RadioPanel hub={hub} compact />
  </aside>;
}

function AircraftWarnings({ a, hub }: { a: Aircraft; hub: SimHub }) {
  const conflicts = hub.state.conflicts?.filter(pair => pair.includes(a.id)) ?? [];
  const predicted = hub.state.predicted?.filter(p => p.pair.includes(a.id)) ?? [];
  return <>
    {(a.alert || a.conflict || conflicts.length > 0 || predicted.length > 0) && <div className="hud-message hud-warning" role="alert"><strong>{a.id} · {a.alert === 'los' || conflicts.length > 0 ? 'Separation alert' : 'Conflict alert'}</strong>
      <p>{conflicts.map(pair => pair.join(' / ')).join(', ') || predicted.map(p => `${p.pair.join(' / ')} · ${p.d} NM in ${p.t} s`).join(', ') || 'Review aircraft separation.'}</p></div>}
    {a.msaw?.status === 'warning' && <div className="hud-message hud-warning" role="alert"><strong>{a.id} · MSAW — LOW ALTITUDE</strong><p>{altitude(a.alt_ft)}; minimum {altitude(a.msaw.minimum_ft)} AMSL. {Math.ceil(a.msaw.deficit_ft).toLocaleString()} ft below minimum.</p></div>}
    {a.control_area?.exit_in_s != null && <div className="hud-message hud-warning" role="alert"><strong>{a.id} · Projected airspace exit</strong><p>{a.control_area.exit_in_s} s to exit · {a.phase === 'handoff_requested' ? 'transfer requested.' : 'reroute.'}</p></div>}
    {a.inzone && <div className="hud-message hud-warning" role="alert"><strong>{a.id} · Zone alert</strong><p>{a.inzone}</p></div>}
  </>;
}
