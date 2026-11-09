/** Etat temps reel de la simulation : WebSocket /ws + journal + evenements.
 *  Le dernier etat est garde dans une ref (lu a 60 fps par le canvas) et la
 *  version React n'est rafraichie qu'a ~4 Hz pour ne pas re-rendre les panneaux
 *  a la cadence du serveur. */
import { useCallback, useEffect, useRef, useState } from "react";
import type { Exchange, ExerciseReport, ExerciseScore, LogEntry, Providers, SimState } from "./types";
import { api } from "./api";
import { playB64Wav } from "./audio";

const EMPTY: SimState = {
  t: 0, running: false, paused: false, speed: 1,
  aircraft: [], conflicts: [], predicted: [],
};

let logSeq = 0;
const now = () => new Date().toLocaleTimeString("fr-FR", { hour12: false });

export interface SimHub {
  connection: "connecting" | "connected" | "disconnected";
  stateRef: React.RefObject<SimState>;
  state: SimState;                       // version throttlee (~4 Hz)
  providers: Providers;                  // sante des fournisseurs IA (stt/llm/tts)
  log: LogEntry[];
  lastExchange: Exchange | null;
  report: ExerciseReport | null;
  exerciseLive: { elapsed_s: number; remaining_s: number; score: ExerciseScore } | null;
  exerciseActive: boolean;
  pushLog: (kind: LogEntry["kind"], text: string) => void;
  clearLog: () => void;
  refreshHealth: () => Promise<void>;
  setReport: (r: ExerciseReport | null) => void;
  onExerciseEnded: (cb: () => void) => () => void;
}

export function useSim(): SimHub {
  const [connection, setConnection] = useState<SimHub["connection"]>("connecting");
  const stateRef = useRef<SimState>(EMPTY);
  const [state, setState] = useState<SimState>(EMPTY);
  const [providers, setProviders] = useState<Providers>({ stt: false, llm: false, tts: false });
  const [log, setLog] = useState<LogEntry[]>([]);
  const [lastExchange, setLastExchange] = useState<Exchange | null>(null);
  const [report, setReport] = useState<ExerciseReport | null>(null);
  const endedCb = useRef<() => void>(() => undefined);

  const pushLog = useCallback((kind: LogEntry["kind"], text: string, context: Partial<Pick<LogEntry, "exchangeId" | "exchange" | "callsigns">> = {}) => {
    setLog((l) => [...l.slice(-249), { id: ++logSeq, t: now(), kind, text, ...context }]);
  }, []);

  const refreshHealth = useCallback(async () => {
    try {
      const h = await api.healthRefresh();
      setProviders(h.providers);
    } catch { setProviders({ stt: false, llm: false, tts: false }); }
  }, []);

  // sante initiale + dernier rapport d'exercice eventuel
  useEffect(() => {
    api.health().then((h) => setProviders(h.providers)).catch(() => undefined);
    api.exerciseReport().then(setReport).catch(() => undefined);
  }, []);

  // WebSocket + throttling de l'etat React
  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;
    let lastPush = -1e9;          // le tout premier etat est rendu immediatement
    let trailing: number | null = null;   // bord de fuite du throttle
    let reconnect: number | undefined;
    let lastStateAt = performance.now();
    let invalidReported = false;
    let lastError = "";

    let radioPlayback: Promise<void> | null = null;
    const playRadio = (audio: string, warning: string, current = () => true) => {
      const play = async () => { if (current()) await playB64Wav(audio); };
      const tail = (radioPlayback ? radioPlayback.then(play) : play()).catch(() => pushLog("warn", warning));
      radioPlayback = tail;
      void tail.then(() => { if (radioPlayback === tail) radioPlayback = null; });
    };

    const handle = (msg: Record<string, unknown>) => {
      switch (msg.type) {
        case "state": {
          if (!Array.isArray(msg.aircraft) || !Array.isArray(msg.conflicts) || !Number.isFinite(msg.t)) {
            throw new Error("État de simulation invalide");
          }
          if (msg.predicted !== undefined && !Array.isArray(msg.predicted)) {
            throw new Error("Liste de conflits prédits invalide");
          }
          lastStateAt = performance.now();
          setConnection("connected");
          // Older servers omit predictions in the first frame during BlueSky startup.
          const previousTrafficCalls = new Set(stateRef.current.traffic_calls?.map(c => c.id));
          const previousCall = stateRef.current.pilot_call;
          stateRef.current = { ...EMPTY, ...msg, predicted: msg.predicted ?? [] } as SimState;
          for (const c of stateRef.current.traffic_calls ?? []) {
            if (!previousTrafficCalls.has(c.id)) pushLog("pilot", c.text, {callsigns:[c.callsign]});
          }
          const call = stateRef.current.pilot_call;
          if (call && call.id !== previousCall?.id) pushLog("pilot", call.text, {callsigns: [call.callsign]});
          const error = JSON.stringify([msg.last_error, msg.command_errors]);
          if (error !== lastError) {
            lastError = error;
            if (msg.last_error) pushLog("rej", `Simulation : ${msg.last_error}`);
            const failures = msg.command_errors as SimState["command_errors"];
            if (failures?.length) pushLog("rej", `Simulation : ${failures[failures.length - 1].message}`);
          }
          const t = performance.now();
          if (t - lastPush > 240) {
            lastPush = t;
            setState(stateRef.current);
          } else if (trailing === null) {
            // bord de fuite : le DERNIER etat d'une rafale est toujours rendu
            // (sinon les panneaux restent figes sur l'avant-dernier etat)
            trailing = window.setTimeout(() => {
              trailing = null;
              lastPush = performance.now();
              setState(stateRef.current);
            }, 240 - (t - lastPush) + 10);
          }
          break;
        }
        case "pilot_audio":
          if ((stateRef.current.pilot_call?.id === msg.id || stateRef.current.traffic_calls?.some(c => c.id === msg.id)) && typeof msg.audio_b64 === "string") {
            playRadio(msg.audio_b64, "Pilot audio playback blocked. Allow sound in your browser.",
              () => stateRef.current.pilot_call?.id === msg.id || !!stateRef.current.traffic_calls?.some(c => c.id === msg.id));
          }
          break;
        case "exchange": {
          const m = msg as unknown as Exchange & { readback: string };
          setLastExchange(m);
          const exchangeId = ++logSeq;
          const callsigns = [...new Set((m.orders ?? []).map(o => o.callsign).filter(Boolean))];
          // Preserve the event boundary, not adjacency or timestamps, for grouping.
          // Audio remains on lastExchange rather than accumulating in history.
          const { audio_b64: _audio, ...exchange } = m;
          pushLog("tx", `📡 ${m.transcript}`, { exchangeId, exchange, callsigns });
          (m.trafscript ?? []).forEach((l) => pushLog("cmd", `→ ${l}`, { exchangeId }));
          if (m.readback) pushLog("pilot", `🔊 ${m.readback}`, { exchangeId });
          (m.rejected ?? []).forEach((r) => pushLog("rej", `⊘ ${r}`, { exchangeId }));
          if (!m.orders?.length && !m.trafscript?.length && !m.rejected?.length) pushLog("rej", "⊘ aucun ordre reconnu", { exchangeId });
          // Reponse vocale systematique : l'audio du collationnement (API TTS)
          // est joue ICI, chemin unique pour les commandes tapees et vocales.
          // (un echec TTS est deja journalise par l'event "error" du backend)
          if (m.audio_b64) playRadio(m.audio_b64, "Audio playback blocked. Use the replay control or allow sound in your browser.");
          break;
        }
        case "situation":
          pushLog("ok", `✈ Situation : ${msg.description} → ${((msg.created as string[]) ?? []).join(", ") || "-"}`);
          break;
        case "info":
          pushLog("info", String(msg.message ?? ""));
          break;
        case "error":
          // Erreur d'un fournisseur IA : toujours VISIBLE (jamais avalee).
          pushLog("rej", `⊘ ${String(msg.provider ?? "IA").toUpperCase()} : ${msg.message}`);
          break;
        case "exercise_started":
          pushLog("ok", `▶ Exercice ${msg.label ?? ""} démarré - ${((msg.aircraft as string[]) ?? []).length} aéronefs`);
          break;
        case "exercise_event": {
          const kind = msg.kind as string;
          if (kind === "los") pushLog("rej", `⚠ PERTE DE SÉPARATION ${(msg.pair as string[]).join(" / ")} (t=${msg.t}s)`);
          else if (kind === "predicted") pushLog("warn", `△ Conflit prédit ${(msg.pair as string[]).join(" / ")} - CPA ${msg.dcpa} NM dans ${msg.tcpa}s`);
          else if (kind === "zone") pushLog("warn", `△ ${msg.callsign} pénètre ${msg.zone} (t=${msg.t}s)`);
          break;
        }
        case "exercise_ended": {
          const sc = msg.score as ExerciseScore | undefined;
          pushLog("ok", `■ Exercice terminé - score ${sc?.total ?? "?"}/100 (${sc?.grade ?? ""})`);
          api.exerciseReport().then((r) => { setReport(r); endedCb.current(); }).catch(() => undefined);
          break;
        }
      }
    };

    const connect = () => {
      if (closed) return;
      lastStateAt = performance.now();
      ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
      // (re)connexion : re-tester les fournisseurs (couvre un health initial
      // rate ou un provider demarre apres l'application)
      ws.onopen = () => {
        void refreshHealth();
        void api.exerciseReport().then(setReport).catch(() => undefined);
      };
      ws.onmessage = (ev) => {
        try { handle(JSON.parse(ev.data)); } catch {
          if (!invalidReported) { pushLog("warn", "Une trame de simulation invalide a été ignorée."); invalidReported = true; }
        }
      };
      ws.onerror = () => ws?.close();
      ws.onclose = () => {
        if (!closed) {
          setConnection("disconnected");
          reconnect = window.setTimeout(connect, 1500);
        }
      };
    };
    connect();
    const watchdog = window.setInterval(() => {
      if (performance.now() - lastStateAt > 5000 && ws?.readyState === WebSocket.OPEN) {
        setConnection("disconnected");
        ws.close();
      }
    }, 1000);
    return () => {
      closed = true;
      window.clearTimeout(reconnect);
      window.clearInterval(watchdog);
      if (trailing !== null) window.clearTimeout(trailing);
      ws?.close();
    };
  }, [pushLog, refreshHealth]);

  const onExerciseEnded = useCallback((cb: () => void) => {
    endedCb.current = cb;
    return () => { if (endedCb.current === cb) endedCb.current = () => undefined; };
  }, []);
  const clearLog = useCallback(() => { setLog([]); setLastExchange(null); }, []);

  return {
    connection, stateRef, state, providers, log, lastExchange, report,
    exerciseLive: state.exercise ?? null,
    exerciseActive: !!state.exercise,
    pushLog,
    clearLog,
    refreshHealth,
    setReport,
    onExerciseEnded,
  };
}
