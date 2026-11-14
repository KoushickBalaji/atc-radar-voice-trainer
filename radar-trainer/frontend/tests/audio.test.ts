import { afterEach, describe, expect, it, vi } from "vitest";
import { pilotWavBytes, playB64Wav, stopRadioPlayback, WavRecorder } from "../src/audio";

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

function toneWav(): string {
  const frames = 1600, bytes = new Uint8Array(44 + frames * 2), view = new DataView(bytes.buffer);
  const tag = (at: number, value: string) => { for (let i = 0; i < 4; i++) view.setUint8(at + i, value.charCodeAt(i)); };
  tag(0, 'RIFF'); view.setUint32(4, bytes.length - 8, true); tag(8, 'WAVE'); tag(12, 'fmt ');
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, 16000, true); view.setUint32(28, 32000, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); tag(36, 'data'); view.setUint32(40, frames * 2, true);
  for (let i = 0; i < frames; i++) view.setInt16(44 + i * 2, Math.sin(i * 2 * Math.PI * 1000 / 16000) * 12000, true);
  return btoa(String.fromCharCode(...bytes));
}

describe('pilot radio effect', () => {
  it('keeps Off byte-for-byte clear and separates both squelches from speech', () => {
    const raw = toneWav();
    const clear = pilotWavBytes(raw, false);
    expect(clear).toEqual(Uint8Array.from(atob(raw), c => c.charCodeAt(0)));
    const effected = pilotWavBytes(raw, true);
    const wav = new DataView(effected.buffer);
    const opener = 1040, gap = 1920, speech = 1600;
    expect(wav.getUint32(24, true)).toBe(16000);
    expect((effected.length - 44) / 2).toBe(opener * 2 + gap * 2 + speech);
    const sample = (i: number) => wav.getInt16(44 + i * 2, true);
    expect(sample(100)).not.toBe(0);
    for (let i = opener; i < opener + gap; i++) expect(sample(i)).toBe(0);
    expect(sample(opener + gap + 100)).not.toBe(0);
    for (let i = opener + gap + speech; i < opener + gap * 2 + speech; i++) expect(sample(i)).toBe(0);
    expect(sample(opener + gap * 2 + speech + 100)).not.toBe(0);
  });

  it('processes streaming WAV headers from the live TTS provider', () => {
    const raw = Uint8Array.from(atob(toneWav()), c => c.charCodeAt(0));
    const header = new DataView(raw.buffer);
    header.setUint32(4, 0xffffffff, true);
    header.setUint32(40, 0xffffffff, true);
    const effected = pilotWavBytes(btoa(String.fromCharCode(...raw)), true);
    expect(effected).not.toEqual(raw);
    expect(new DataView(effected.buffer).getUint32(40, true)).toBe(effected.length - 44);
  });

  it('keeps the louder hiss and squelch below clipping without filling the speech gaps', () => {
    const silent = Uint8Array.from(atob(toneWav()), c => c.charCodeAt(0));
    silent.fill(0, 44);
    const processed = pilotWavBytes(btoa(String.fromCharCode(...silent)), true);
    const view = new DataView(processed.buffer);
    const sample = (i: number) => view.getInt16(44 + i * 2, true);
    const opener = 1040, gap = 1920, speech = 1600;
    const squelchPeak = Math.max(...Array.from({ length: opener }, (_, i) => Math.abs(sample(i))));
    const hissRms = Math.sqrt(Array.from({ length: speech }, (_, i) => sample(opener + gap + i) ** 2)
      .reduce((sum, value) => sum + value, 0) / speech);
    expect(squelchPeak).toBeGreaterThan(9000);
    expect(squelchPeak).toBeLessThan(13000);
    expect(hissRms).toBeGreaterThan(230);
    expect(hissRms).toBeLessThan(310);
    expect(sample(opener + 100)).toBe(0);
    expect(sample(opener + gap + speech + 100)).toBe(0);
  });
});

describe("audio resource lifecycle", () => {
  it('stops a readback when its exercise ends and releases its URL', async () => {
    const pause = vi.fn();
    const revoke = vi.fn();
    vi.stubGlobal('URL', { createObjectURL: () => 'blob:old-session', revokeObjectURL: revoke });
    vi.stubGlobal('Audio', class { play() { return Promise.resolve(); } pause = pause; });
    const playback = playB64Wav('AA==');
    const rejected = expect(playback).rejects.toThrow('Exercise ended');
    stopRadioPlayback();
    await rejected;
    expect(pause).toHaveBeenCalledOnce();
    expect(revoke).toHaveBeenCalledWith('blob:old-session');
  });
  it("closes a microphone acquired after recording was cancelled", async () => {
    let grant!: (stream: MediaStream) => void;
    const stop = vi.fn();
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia: () => new Promise<MediaStream>((resolve) => { grant = resolve; }) } });
    const recorder = new WavRecorder();
    const starting = recorder.start();
    expect(await recorder.stop()).toBeNull();
    grant({ getTracks: () => [{ stop }] } as unknown as MediaStream);
    await starting;
    expect(stop).toHaveBeenCalledOnce();
  });

  it("releases the microphone if audio context creation fails", async () => {
    const stop = vi.fn();
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia: async () => ({ getTracks: () => [{ stop }] }) } });
    vi.stubGlobal("AudioContext", class { constructor() { throw new Error("context unavailable"); } });
    await expect(new WavRecorder().start()).rejects.toThrow("context unavailable");
    expect(stop).toHaveBeenCalledOnce();
  });

  it("releases the audio URL and reports rejected playback", async () => {
    const revoke = vi.fn();
    vi.stubGlobal("URL", { createObjectURL: () => "blob:readback", revokeObjectURL: revoke });
    vi.stubGlobal("Audio", class { play() { return Promise.reject(new Error("playback blocked")); } });
    await expect(playB64Wav("AA==")).rejects.toThrow("playback blocked");
    expect(revoke).toHaveBeenCalledWith("blob:readback");
  });
});
