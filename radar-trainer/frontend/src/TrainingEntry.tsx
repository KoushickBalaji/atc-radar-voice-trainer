import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Headphones, Radar, Radio} from 'lucide-react';
import scenarioSource from '../../data/traffic/VOCB.json?raw';
import { api } from './api';
import { beginSession, endSession, hasSession, sessionFetch } from './session';
import './training-entry.css';

const SimpleApp = lazy(() => import('./SimpleApp'));
type Flight = { callsign: string; role: string; type: string; at_s: number; entry_alt_ft?: number; alt_ft?: number; climb_ft?: number };
type Scenario = { id: string; title: string; brief: string; flights: Flight[] };
const scenarios: Scenario[] = (JSON.parse(scenarioSource) as Scenario[]).filter(s => s.id === 'routine-23');
type Screen = 'welcome' | 'airport' | 'briefing' | 'about' | 'tutorial' | 'sim';
const steps = [
  { title: 'Your radar picture', text: 'Select an aircraft on the radar or in the traffic list. Scroll to zoom, drag to pan, or use the + and − controls.', box: [1, 17, 70, 74] },
  { title: 'Traffic and aircraft details', text: 'The traffic list and selected-aircraft panel show callsigns, levels, headings and speeds. Select a strip to focus on that aircraft.', box: [72, 16, 27, 37] },
  { title: 'Radio and messages', text: 'Read pilot calls and readbacks in the message panel. Filter by the selected aircraft or show all traffic; warnings remain visible.', box: [72, 54, 27, 35] },
  { title: 'Transmit by voice', text: 'Use headphones. Select Enable microphone and allow access. Once ready, hold V or the microphone button, speak, then release to send. Listen to the readback before transmitting again.', box: [72, 92, 27, 7] },
  { title: 'Control the exercise', text: 'Start / Resume begins the paused exercise. Pause gives you time to review; the speed button cycles through 1×, 2× and 4×. Reset exercise starts the selected scenario again.', box: [47, 0, 52, 11] },
  { title: 'Choose your map layers', text: 'Open Map layers to show or hide airspace, routes and navigation references. Display choices do not change aircraft behaviour or monitoring.', box: [1, 91, 20, 8] },
];

async function selectScenario(id: string) {
  const response = await sessionFetch('/api/demo/airport', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ icao: 'VOCB', scenario_id: id }), signal: AbortSignal.timeout(25000) });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || 'The simulator could not load this exercise. Please try again.');
  }
  // A static hosting fallback can return HTML with 200. Require the API contract.
  const result = await response.json();
  if (result.airport?.icao !== 'VOCB') throw new Error('The simulation service is unavailable. Please try again.');
  await api.pause();
}

export default function TrainingEntry() {
  const [screen, setScreen] = useState<Screen>('welcome');
  const [selectedId, setSelectedId] = useState(scenarios[0].id);
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const shell = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const scenario = scenarios.find(s => s.id === selectedId)!;
  const go = (next: Screen) => { setError(''); setScreen(next); };
  useEffect(() => {
    const ended = () => { setScreen('briefing'); setBusy(false); setError('The connection ended. Your previous exercise has been closed. Enter the simulator to start a fresh exercise.'); };
    const unload = () => { void endSession(); };
    window.addEventListener('atc-session-ended', ended);
    window.addEventListener('pagehide', unload);
    return () => { window.removeEventListener('atc-session-ended', ended); window.removeEventListener('pagehide', unload); };
  }, []);
  useEffect(() => {
    if (screen !== 'sim') document.title = 'radar ATC · Controller practice';
    heading.current?.focus({ preventScroll: true });
    if (shell.current) shell.current.scrollTop = 0;
  }, [screen]);
  useEffect(() => {
    if (screen !== 'sim') return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [screen]);
  const launch = async () => {
    if (busy) return;
    setBusy(true); setError('');
    try { await beginSession(); await selectScenario(selectedId); setScreen('sim'); }
    catch (e) { await endSession(); setError(`Unable to start. ${e instanceof Error ? e.message : 'Please try again.'}`); }
    finally { setBusy(false); }
  };
  const leave = async () => {
    if (busy || !window.confirm('Return to scenario selection? This exercise will end. Launching a scenario again will start a fresh exercise.')) return;
    setBusy(true); setError('');
    try { if (hasSession()) await endSession(); else await api.pause(); go('briefing'); }
    catch { setError('Could not pause the exercise. Check the connection and try again.'); }
    finally { setBusy(false); }
  };
  if (screen === 'sim') return <><Suspense fallback={<div className="entry-loading" role="status">Opening radar…</div>}><SimpleApp onExit={() => void leave()} /></Suspense>{error && <div className="entry-session-error" role="alert">{error}<button onClick={() => setError('')}>Dismiss</button></div>}</>;
  
  return <div ref={shell} className={`entry-shell entry-screen-${screen}`}>
    <header className="entry-header">
      <button className="entry-brand" onClick={() => go('welcome')} disabled={busy} aria-label="radar ATC home"><Radar aria-hidden="true" /><span>radar <strong>ATC</strong></span></button>
      <span className="entry-preview"><i /> CONTROLLER PREVIEW</span>
    </header>
    {screen === 'welcome' ? <main className="entry-welcome-content">
      <h1 ref={heading} tabIndex={-1}>Your airspace.<br /><span>Your control.</span></h1>
      <p className="entry-intro">Step into the controller’s seat.<br className="entry-desktop-break" />Experience realistic traffic management.</p>
      <div className="entry-welcome-actions"><button className="entry-primary" onClick={() => go('airport')}>Start <ArrowRight size={19} /></button><div className="entry-welcome-secondary-actions"><button className="entry-secondary" onClick={() => go('about')}>About</button><button className="entry-secondary" onClick={() => { setStep(0); go('tutorial'); }}>Tutorial</button></div></div>
      <div className="entry-welcome-notes"><span><Headphones size={16} /> Headphones recommended</span></div>
    </main> : <main className="entry-content">
      <div className="entry-context"><button className="entry-back" disabled={busy} onClick={() => go(screen === 'briefing' ? 'airport' : 'welcome')}><ArrowLeft size={16} /> {screen === 'briefing' ? 'Airport selection' : 'Welcome'}</button>
      </div>
      {screen === 'airport' && <><p className="entry-eyebrow">01 / SELECT YOUR AIRSPACE</p><h1 ref={heading} tabIndex={-1}>Where will you control?</h1>
        <div className="entry-airport-grid"><div className="entry-airport-visual"><div className="entry-airport-code">VOCB</div><div><h2>Coimbatore</h2><p>Approach practice</p></div></div>
          <section className="entry-airport-select"><label htmlFor="training-airport">Airport</label><select id="training-airport" defaultValue="VOCB"><option value="VOCB">Coimbatore (VOCB)</option></select><div><span></span></div><button className="entry-primary" onClick={() => go('briefing')}>Select scenario <ArrowRight size={18} /></button></section></div></>}
      {screen === 'briefing' && <><p className="entry-eyebrow">02 / SCENARIO BRIEFING</p><h1 ref={heading} tabIndex={-1}>Choose your exercise.</h1><p className="entry-subtitle">Coimbatore · VOCB · Combined approach and tower</p><div className="entry-briefing-grid">
        <nav className="entry-scenario-list" aria-label="Scenarios">{scenarios.map((s, index) => <button key={s.id} aria-pressed={s.id === selectedId} disabled={busy} onClick={() => { setSelectedId(s.id); setError(''); }}><span className="entry-scenario-index">SCENARIO 0{index + 1}</span><strong>{s.id === 'routine-23' ? 'Routine mixed traffic' : 'Level changeovers'}</strong><span>{s.id === 'routine-23' ? 'Sequence arrivals, release a departure and work a transit.' : 'Coordinate level changes and separate frequency transfers.'}</span><small>{s.flights.length} aircraft <span>RWY 23</span></small>{s.id === selectedId && <ArrowRight className="entry-selected-arrow" size={18} />}</button>)}</nav>
        <article className="entry-briefing" aria-label="Selected scenario briefing"><div className="entry-briefing-top"><span className="entry-eyebrow">EXERCISE BRIEF</span><span className="entry-tag">VOCB / 23</span></div><h2>{scenario.title}</h2><div className="entry-metrics"><span><strong>{scenario.flights.length}</strong> aircraft</span><span><strong>ILS Z</strong> RWY 23</span></div>
          <br></br><p>{scenario.id === 'routine-23' ? 'Build the arrival sequence, manage the departure and transit, and complete the coordinated transfers.' : 'Descend the arrival to its transfer level, manage the departure climb, and issue each frequency change separately.'}</p>
          <details className="entry-full-brief"><summary>Full scenario briefing & exercise assumptions</summary><p>{scenario.brief}</p></details>
          <div className="entry-launch"><p><Headphones size={17} /> Have your headset ready.<br /><span>The exercise opens paused.</span></p><button className="entry-primary" disabled={busy} onClick={() => void launch()}>{busy ? 'Preparing exercise…' : 'Enter simulator'} {!busy && <ArrowRight size={18} />}</button></div>
          {error && <p className="entry-error" role="alert">{error}</p>}{busy && <p role="status" className="entry-muted">Loading your scenario and pausing the traffic…</p>}
        </article></div></>}
      {screen === 'about' && <><p className="entry-eyebrow">ABOUT RADAR ATC</p><h1 ref={heading} tabIndex={-1}>A place to practise the picture.</h1><p className="entry-subtitle">A voice-operated radar simulation for controller feedback and practice.</p><div className="entry-about-grid"><section><Radio /><h2>Work the frequency</h2><p>Issue heading, level and speed instructions. Listen to pilot readbacks, sequence arrivals, manage departures and coordinate transfers.</p></section><section><Radar /><h2>Build the sequence</h2><p>Practise with Coimbatore traffic, published holding references and ILS Z runway 23. Pause to review the picture and restart to try a different sequence.</p></section><section><Headphones /><h2>Help shape the trainer</h2><p>Look for unexpected aircraft behaviour, unclear readbacks and anything that would teach the wrong habit. Note the scenario, callsign and instruction when sharing feedback.</p></section></div><div className="entry-about-note"><h2>Before you take control</h2><p>This is an early training prototype, not an operational system or an assessment of controller competence. Procedures and aircraft behaviour are simplified. Read the scenario assumptions and use current approved procedures for operational work.</p><p>Use a desktop or laptop and headphones for this preview. Microphone access is requested inside the simulator. Voice recordings are sent to OpenAI for processing; pilot voices are AI-generated.</p></div><button className="entry-primary" onClick={() => go('airport')}>Select an airport <ArrowRight size={18} /></button></>}
      {screen === 'tutorial' && <><p className="entry-eyebrow">A QUICK LOOK AROUND</p><h1 ref={heading} tabIndex={-1}>Know your position.</h1><p className="entry-subtitle">One radar picture. The controls you need to get started.</p><div className="entry-tutorial"><div className="entry-tutorial-image"><img src="/onboarding/radar-walkthrough.png" alt="radar ATC desktop interface: radar on the left, traffic and aircraft details on the upper right, messages and microphone below, exercise controls above." width="1440" height="900" /><div className="entry-highlight" style={{ left: `${steps[step].box[0]}%`, top: `${steps[step].box[1]}%`, width: `${steps[step].box[2]}%`, height: `${steps[step].box[3]}%` }}><span>{step + 1}</span></div></div><section className="entry-tutorial-copy" aria-live="polite"><span className="entry-eyebrow">{String(step + 1).padStart(2, '0')} / {String(steps.length).padStart(2, '0')}</span><h2>{steps[step].title}</h2><p>{steps[step].text}</p><div className="entry-tutorial-dots">{steps.map((s, i) => <button key={s.title} aria-label={`Step ${i + 1}: ${s.title}`} aria-current={i === step ? 'step' : undefined} onClick={() => setStep(i)}>{i + 1}</button>)}</div><div className="entry-tutorial-nav"><button className="entry-secondary" disabled={step === 0} onClick={() => setStep(step - 1)}>Previous</button><button className="entry-primary" onClick={() => step === steps.length - 1 ? go('airport') : setStep(step + 1)}>{step === steps.length - 1 ? 'Select airport' : 'Next'}<ArrowRight size={16} /></button></div></section></div></>}
    </main>}
  </div>;
}
