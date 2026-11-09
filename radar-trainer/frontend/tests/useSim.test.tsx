import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSim } from "../src/useSim";
import { playB64Wav } from "../src/audio";

vi.mock("../src/api", () => ({ api: {
  health: vi.fn(async () => ({ providers: { stt: true, llm: true, tts: true } })),
  healthRefresh: vi.fn(async () => ({ providers: { stt: true, llm: true, tts: true } })),
  exerciseReport: vi.fn(async () => null),
} }));
vi.mock("../src/audio", () => ({ playB64Wav: vi.fn(async () => undefined) }));

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
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });

describe("simulation feed lifecycle", () => {
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
    expect(playB64Wav).toHaveBeenCalledExactlyOnceWith('valid');
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
    act(() => vi.advanceTimersByTime(6100));
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
