import type { SimHub } from '../useSim';
import PilotReplay from './PilotReplay';

const labels = { tx: 'You transmitted', pilot: 'Pilot readback', cmd: 'Command accepted', rej: 'Rejected / error', warn: 'Warning', ok: 'Confirmed', info: 'Information' };

export default function MessageHistory({ hub, selected }: { hub: SimHub; selected: string | null }) {
  const latestExchange = [...hub.log].reverse().find(l => l.exchange)?.id;
  const entries = hub.log.filter(l => {
    if (l.exchangeId != null && !l.exchange) return false;
    // Unassigned history belongs only in the all-aircraft view.
    return selected == null || l.callsigns?.includes(selected);
  });
  return <>
    <div role="log" aria-label="Radio and command history" aria-live="polite" aria-relevant="additions">
      {[...entries].reverse().map(l => {
        const m = l.exchange;
        if (!m) return <article key={l.id} className={`hud-message hud-message-${l.kind}`}>
          <div><strong>{l.kind === 'pilot' ? `${l.callsigns?.join(' / ')} · Pilot transmission` : `System · ${labels[l.kind]}`}</strong><time>{l.t}</time></div><p>{l.text.replace(/^[📡🔊→⊘]\s*/u, '')}</p>
        </article>;
        const latest = l.id === latestExchange ? hub.lastExchange : null;
        const rejected = !!m.rejected?.length;
        return <article key={l.id} aria-label={`Exchange ${l.callsigns?.join(', ') || 'Unassigned'} at ${l.t}`} className={`hud-message hud-exchange ${rejected ? 'hud-message-rej' : 'hud-message-tx'}`}>
          <div><strong>{l.callsigns?.join(' / ') || 'Unassigned · command not accepted'}</strong><time>{l.t}</time></div>
          <section><h3>You transmitted</h3><p>{m.transcript || 'No speech transcribed.'}</p></section>
          {m.trafscript?.map((line, i) => <section key={i}><h3>Command accepted</h3><p>{line}</p></section>)}
          {m.feedback?.length ? m.feedback.map((item, i) => <section className="hud-exchange-rejection" key={i}>
            <h3>Trainer feedback{item.category === 'capability' ? ' · Simulator limitation' : item.category === 'system' ? ' · System issue' : ''}</h3>
            <p>{item.message}</p>
            {Array.isArray(item.evidence.phrases) && <p>Wording to review: {item.evidence.phrases.map(String).join(' / ')}</p>}
          </section>) : m.rejected?.map((reason, i) => <section className="hud-exchange-rejection" key={i}><h3>Not executed</h3><p>{reason}</p></section>)}
          {!m.orders?.length && !m.trafscript?.length && !rejected && !m.readback && <section className="hud-exchange-rejection"><h3>Feedback</h3><p>No command recognized.</p></section>}
          {m.readback && <section><h3>Pilot readback</h3><p>{m.readback}</p></section>}
          {m.tts_error && <p className="hud-exchange-rejection">Pilot audio failed: {m.tts_error}</p>}
          {latest?.audio_b64 && <PilotReplay audio={latest.audio_b64} radioNoise={hub.radioNoise} />}
        </article>;
      })}
    </div>
  </>;
}
