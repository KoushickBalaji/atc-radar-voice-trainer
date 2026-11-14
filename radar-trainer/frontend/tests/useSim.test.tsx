import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSim } from "../src/useSim";
import { playB64Wav } from "../src/audio";
import { beginSession, endSession } from '../src/session';

vi.mock("../src/api", () => ({ api: {
  health: vi.fn(async () => ({ providers: { stt: true, llm: true, tts: true } })),
  healthRefresh: vi.fn(async () => ({ providers: { stt: true, llm: true, tts: true } })),
  exerciseReport: vi.fn(async () => null),
} }));
vi.mock("../src/audio", () => ({ stopRadioPlayback: vi.fn(), playB64Wav: vi.fn(async (_audio: string, onPlaying?: () => void) => onPlaying?.()) }));

class FakeSocket {
  static OPEN = 1;
  static instances: FakeSocket[] = [];
  readyState = 0;
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor() { FakeSocket.instances.push(this); }
  open() { this.readyState = 1; this.onopen?.(); }
  message(value: unknown) { this.onmessage?.({ data: JSON.stringify(value) }); }
  close() { this.readyState = 3; this.onclose?.(); }
}
const state = (t: number) => ({ type: "state", t, speed: 1, aircraft: [], conflicts: [], predicted: [], paused: false, running: true, sim_alive: true });

beforeEach(() => {
  vi.useFakeTimers();
  FakeSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeSocket);
});
afterEach(async () => { cleanup(); await endSession(); vi.useRealTimers(); vi.unstubAllGlobals(); });

describe("simulation feed lifecycle", () => {
  it('starts with radio effect on and uses the current toggle for subsequent transmissions', async () => {
    const { result } = renderHook(useSim);
    expect(result.current.radioNoise).toBe(true);
    act(() => result.current.setRadioNoise(false));
    expect(result.current.radioNoise).toBe(false);
    await act(async () => FakeSocket.instances[0].message({type: 'exchange', transcript: 'Turn left', orders: [], trafscript: [], rejected: [], readback: 'Turning left', audio_b64: 'clear'}));
    expect(playB64Wav).toHaveBeenCalledWith('clear', expect.any(Function), false);
  });
  it('retains structured trainer feedback in the exchange history', async () => {
    const { result } = renderHook(useSim);
    const feedback = [{code: 'vertical_direction_conflict', category: 'instruction', blocking: true,
      message: 'If 8,000 feet was intended, use climb.', evidence: {current_altitude_ft: 5000}}];
    await act(async () => FakeSocket.instances[0].message({type: 'exchange',
      transcript: 'AFR123 descend 8000 feet', addressed_callsigns: ['AFR123'],
      orders: [], trafscript: [], readback: '', rejected: [feedback[0].message], feedback}));
    expect(result.current.log.find(l => l.exchange)?.exchange?.feedback).toEqual(feedback);
    expect(result.current.lastExchange?.feedback).toEqual(feedback);
  });
  it('keeps an identified but rejected transmission in its aircraft history', async () => {
    const { result } = renderHook(useSim);
    await act(async () => FakeSocket.instances[0].message({type: 'exchange',
      transcript: 'Air France one two three, turn right heading 090',
      addressed_callsigns: ['AFR123'], orders: [], trafscript: [],
      rejected: ['Recognition disagreed. No action taken.'], readback: ''}));
    const entry = result.current.log.find(l => l.exchange);
    expect(entry?.callsigns).toEqual(['AFR123']);
    expect(entry?.exchange?.orders).toEqual([]);
    expect(entry?.exchange?.trafscript).toEqual([]);
  });
  it('ends a hosted session on disconnect instead of silently reconnecting to old state', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({token:'c'.repeat(43)}),{status:200})));
    await beginSession();
    const ended = vi.fn();
    window.addEventListener('atc-session-ended',ended);
    renderHook(useSim);
    act(() => vi.advanceTimersByTime(1));
    const socket = FakeSocket.instances[0];
    act(() => { socket.open(); socket.message(state(1)); socket.close(); });
    expect(ended).toHaveBeenCalledOnce();
    act(() => vi.advanceTimersByTime(2000));
    expect(FakeSocket.instances).toHaveLength(1);
    window.removeEventListener('atc-session-ended',ended);
  });
  it("loops one alarm during actual separation loss and stops it when cleared", async () => {
    const play = vi.fn(async () => undefined);
    const pause = vi.fn();
    class FakeAudio {
      loop = false;
      play = play;
      pause = pause;
    }
    vi.stubGlobal("Audio", FakeAudio);
    renderHook(useSim);
    const socket = FakeSocket.instances[0];
    const pair = ["AAA", "BBB"];
    const update = async (t: number, conflicts: string[][]) => {
      await act(async () => {
        socket.message({ ...state(t), conflicts, predicted: [{ pair, t: 60, d: 1 }] });
        vi.advanceTimersByTime(300);
      });
    };
    await update(1, []);
    expect(play).not.toHaveBeenCalled();
    await update(2, [pair]);
    await update(3, [pair]);
    expect(play).toHaveBeenCalledTimes(1);
    expect(play.mock.contexts[0]).toMatchObject({ loop: true });
    await update(4, []);
    expect(pause).toHaveBeenCalledTimes(1);
    await update(5, [pair]);
    expect(play).toHaveBeenCalledTimes(2);
    act(() => socket.close());
    expect(pause).toHaveBeenCalledTimes(2);
  });
  it("logs a pilot call once and ignores delayed audio after handover", async () => {
    const { result } = renderHook(useSim);
    const socket = FakeSocket.instances[0];
    const pilot_call = {id: 'request1', callsign: 'AFR123', text: 'Air France one two three, confirm contact tower.'};
    vi.mocked(playB64Wav).mockClear();
    await act(async () => {
      socket.open();
      socket.message({...state(1), pilot_call});
      socket.message({...state(2), pilot_call});
      socket.message({type: 'pilot_audio', id: pilot_call.id, audio_b64: 'valid'});
      socket.message(state(3));
      socket.message({type: 'pilot_audio', id: pilot_call.id, audio_b64: 'stale'});
    });
    expect(result.current.log.filter(entry => entry.kind === 'pilot')).toHaveLength(1);
    expect(playB64Wav).toHaveBeenCalledExactlyOnceWith('valid', expect.any(Function), true);
  });
  it("reveals each queued transmission only when its audio starts", async () => {
    const { result } = renderHook(useSim);
    const socket = FakeSocket.instances[0];
    let start!: () => void;
    let finish!: () => void;
    vi.mocked(playB64Wav).mockImplementationOnce((_audio, onPlaying) => {
      start = onPlaying!;
      return new Promise<void>(resolve => { finish = resolve; });
    });
    const secondPlayback = vi.fn(async (_audio: string, onPlaying?: () => void) => { start = onPlaying!; });
    vi.mocked(playB64Wav).mockImplementationOnce(secondPlayback);
    const call = {id: "first", callsign: "AFR123", text: "Ready"};
    await act(async () => {
      socket.message({...state(1), traffic_calls: [call]});
      socket.message({type: "pilot_audio", id: call.id, audio_b64: "first"});
      socket.message({type: "exchange", transcript: "Turn left", orders: [], trafscript: ["HDG"], rejected: [], readback: "Turning left", audio_b64: "second"});
    });
    expect(result.current.log.some(l => l.kind === "pilot")).toBe(false);
    expect(secondPlayback).not.toHaveBeenCalled();
    expect(result.current.lastExchange?.readback).toBe("");
    expect(result.current.log.find(l => l.exchange)?.exchange?.readback).toBe("");
    act(() => start());
    expect(result.current.log.filter(l => l.kind === "pilot").map(l => l.text)).toEqual(["Ready"]);
    await act(async () => finish());
    expect(secondPlayback).not.toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(secondPlayback).toHaveBeenCalledOnce();
    expect(result.current.lastExchange?.readback).toBe("");
    act(() => start());
    expect(result.current.lastExchange?.readback).toBe("Turning left");
    expect(result.current.log.find(l => l.exchange)?.exchange?.readback).toBe("Turning left");
  });
  it("accepts the initial frame of older servers before predictions are ready", async () => {
    const { result } = renderHook(useSim);
    const socket = FakeSocket.instances[0];
    await act(async () => { socket.open(); socket.message({ ...state(0), predicted: undefined }); });
    expect(result.current.connection).toBe("connected");
    expect(result.current.state.predicted).toEqual([]);
    expect(result.current.stateRef.current.predicted).toEqual([]);
  });

  it("shows disconnection and cancels pending reconnect on unmount", async () => {
    const { result, unmount } = renderHook(useSim);
    const socket = FakeSocket.instances[0];
    await act(async () => { socket.open(); socket.message(state(1)); });
    expect(result.current.connection).toBe("connected");
    act(() => socket.close());
    expect(result.current.connection).toBe("disconnected");
    unmount();
    act(() => vi.advanceTimersByTime(10000));
    expect(FakeSocket.instances).toHaveLength(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("renders the final state of a burst and keeps the radar ref current", async () => {
    const { result } = renderHook(useSim);
    const socket = FakeSocket.instances[0];
    await act(async () => { socket.open(); socket.message(state(1)); socket.message(state(2)); socket.message(state(3)); });
    expect(result.current.stateRef.current.t).toBe(3);
    act(() => vi.advanceTimersByTime(260));
    expect(result.current.state.t).toBe(3);
  });

  it("reconnects if an open connection stops delivering snapshots", async () => {
    const { result } = renderHook(useSim);
    const socket = FakeSocket.instances[0];
    await act(async () => { socket.open(); socket.message(state(1)); });
    act(() => vi.advanceTimersByTime(16100));
    expect(result.current.connection).toBe("disconnected");
    act(() => vi.advanceTimersByTime(1600));
    expect(FakeSocket.instances).toHaveLength(2);
  });

  it("rejects malformed states without replacing the last valid radar state", async () => {
    const { result } = renderHook(useSim);
    const socket = FakeSocket.instances[0];
    await act(async () => { socket.open(); socket.message(state(12)); socket.message({ type: "state", t: "bad" }); });
    expect(result.current.stateRef.current.t).toBe(12);
    expect(result.current.log.some((entry) => entry.kind === "warn")).toBe(true);
  });
});

it('preserves exchange boundaries and callsigns even for simultaneous messages, and clears them on reset', async () => {
  const { result } = renderHook(useSim);
  const socket = FakeSocket.instances[0];
  const exchange = (callsign: string) => ({ type: 'exchange', transcript: callsign + ' descend', orders: [{ callsign, action: 'ALT', value: 3000 }], trafscript: [callsign + ' ALT 3000'], readback: callsign + ' descending', rejected: [] });
  await act(async () => { socket.open(); socket.message(exchange('AFR123')); socket.message(exchange('IGO456')); socket.message({ type: 'exchange', transcript: '', orders: [], trafscript: [], readback: '', rejected: ['Unclear instruction'] }); });
  const groups = result.current.log.filter(l => l.exchange);
  expect(groups).toHaveLength(3);
  expect(groups.map(l => l.callsigns)).toEqual([['AFR123'], ['IGO456'], []]);
  expect(new Set(groups.map(l => l.exchangeId)).size).toBe(3);
  expect(result.current.log.filter(l => l.exchangeId === groups[0].exchangeId)).toHaveLength(3);
  act(() => result.current.clearLog());
  expect(result.current.log).toEqual([]);
  expect(result.current.lastExchange).toBeNull();
});
