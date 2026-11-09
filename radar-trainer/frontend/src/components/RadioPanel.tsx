/** Poste radio du controleur : push-to-talk (touche « V » maintenue) + saisie
 *  texte + dernier echange. Chemin UNIQUE : capture WAV -> /api/voice (API STT)
 *  -> interpretation -> collationnement TOUJOURS vocalise par l'API TTS (audio
 *  joue par l'event WebSocket "exchange", commande tapee ou parlee). */
import { useCallback, useEffect, useRef, useState } from "react";
import { Mic } from "lucide-react";
import { api } from "../api";
import { RadioMic } from "../audio";
import { type SimHub } from "../useSim";


export default function RadioPanel({ hub, compact = false }: { hub: SimHub; prefill?: string; compact?: boolean }) {
  const { pushLog } = hub;
  type Phase = 'off' | 'arming' | 'ready' | 'talking' | 'busy';
  const [phase, renderPhase] = useState<Phase>('off');
  const phaseRef = useRef<Phase>('off');
  const change = useCallback((next: Phase) => { phaseRef.current = next; renderPhase(next); }, []);
  const mic = useRef<RadioMic | null>(null);
  const off = useCallback(() => {
    const current = mic.current;
    mic.current = null;
    current?.close();
    change('off');
  }, [change]);
  const available = hub.connection === 'connected' && hub.state.sim_alive !== false && hub.providers.stt;
  useEffect(() => {
    if (!available) off();
    return off;
  }, [available, off]);

  const startTalk = useCallback(async () => {
    if (!available) return;
    if (phaseRef.current === 'ready') {
      mic.current!.begin();
      change('talking');
    } else if (phaseRef.current === 'off') {
      // First gesture is setup only: don't claim to record through a permission prompt.
      change('arming');
      const session = mic.current = new RadioMic();
      try {
        await session.arm(message => {
          if (mic.current === session) { off(); pushLog('rej', message); }
        });
        if (mic.current === session) change('ready');
      } catch (e) {
        if (mic.current === session) { off(); pushLog('rej', `Microphone unavailable: ${e}`); }
      }
    }
  }, [available, change, off, pushLog]);

  const stopTalk = useCallback(async () => {
    const session = mic.current;
    if (!session || phaseRef.current !== 'talking') return;
    change('busy');
    try {
      const wav = await session.finish();
      if (wav && mic.current === session) await api.voice(wav);
    } catch (e) {
      if (mic.current === session) pushLog('rej', `Transmission failed: ${e}`);
    } finally {
      if (mic.current === session) change('ready');
    }
  }, [change, pushLog]);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.code !== 'KeyV' || e.ctrlKey || e.metaKey || e.altKey || e.repeat) return;
      const target = e.target;
      if (target instanceof HTMLElement && (target.isContentEditable ||
          target.closest('input, textarea, select, button:not([data-radio-ptt])'))) return;
      e.preventDefault(); void startTalk();
    };
    const up = (e: KeyboardEvent) => {
      if (e.code === 'KeyV' && phaseRef.current === 'talking') { e.preventDefault(); void stopTalk(); }
    };
    const onBlur = () => { if (phaseRef.current !== 'arming') off(); };
    const onVisibility = () => { if (document.hidden) off(); };
    window.addEventListener('keydown', down);
    window.addEventListener('keyup', up);
    window.addEventListener('blur', onBlur);
    window.addEventListener('pagehide', off);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('keydown', down);
      window.removeEventListener('keyup', up);
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('pagehide', off);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [startTalk, stopTalk, off]);

  const talking = phase === 'talking';
  const label = { off: 'Enable microphone', arming: 'Preparing microphone…', ready: 'Hold to talk · V',
    talking: 'LISTENING…', busy: 'PROCESSING…' }[phase];
  const m = hub.lastExchange;
  return (
    <div className={compact ? "hud-radio" : "shrink-0 border-t border-edge bg-panel px-4 py-3"}>
      <button
        type="button"
        data-radio-ptt
        disabled={!available || phase === 'busy'}
        aria-label={label}
        onPointerDown={(e) => { if (e.button === 0) { e.currentTarget.setPointerCapture(e.pointerId); void startTalk(); } }}
        onPointerUp={() => void stopTalk()}
        onPointerCancel={off}
        onKeyDown={(e) => { if ((e.key === " " || e.key === "Enter") && !e.repeat) { e.preventDefault(); void startTalk(); } }}
        onKeyUp={(e) => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); void stopTalk(); } }}
        onBlur={() => { if (phaseRef.current === 'talking') off(); }}
        aria-live="polite"
        className={`${compact ? "hud-ptt " : ""}flex w-full select-none items-center justify-center gap-1.5 rounded-lg
          border px-4 py-3 text-[13px] font-medium transition-colors disabled:opacity-50 ${talking
            ? "border-dang bg-dang text-white"
            : "border-edge bg-panel2 text-mut"}`}
        title="Enable the mic once, then hold V to talk. The mic stays ready until switched off."
      >
        <Mic size={15} className={talking ? "inline" : "inline opacity-70"} />
        {label}
      </button>

      {phase !== "off" && <button type="button" className="text-xs text-mut underline" onClick={off}>Switch mic off</button>}
      {!compact && <p className="mt-2 text-xs text-mut">Voice only. Release to send automatically. Pilot voices are AI-generated. Audio is processed by OpenAI.</p>}
      {!compact && m?.tts_error && <p role="alert" className="text-dang">Pilot audio failed: {m.tts_error}</p>}
      {!compact && m?.audio_b64 && <audio aria-label="Replay pilot readback" controls src={`data:audio/wav;base64,${m.audio_b64}`} className="mt-2 w-full" />}
      {!compact && m && (
        <div className="mt-2 space-y-0.5 text-[12.5px] leading-snug">
          <div className="text-rdr">📡 « {m.transcript} »</div>
          {m.trafscript?.length > 0 && (
            <div className="font-mono text-[11.5px] text-wpt">→ {m.trafscript.join(" · ")}</div>
          )}
          {m.readback && <div className="text-warn">🔊 {m.readback}</div>}
          {m.rejected?.map((r, i) => <div key={i} className="text-dang">⊘ {r}</div>)}
          {!m.trafscript?.length && !m.rejected?.length && (
            <div className="text-dang">⊘ No command recognized</div>
          )}
        </div>
      )}
    </div>
  );
}
