/** Audio : capture micro WAV mono 16 kHz (envoyee a l'API STT via /api/voice)
 *  et lecture des WAV de collationnement renvoyes par l'API TTS. */

export async function playB64Wav(b64: string) {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  const url = URL.createObjectURL(new Blob([arr], { type: "audio/wav" }));
  // URL blob revoquee apres lecture (sinon fuite memoire cumulative : un blob
  // par collationnement TTS sur toute la session). revoke est idempotent.
  const audio = new Audio(url);
  const ended = new Promise<void>((resolve, reject) => {
    audio.onended = () => resolve();
    audio.onerror = () => reject(new Error('Radio audio playback failed'));
  });
  // Lecture bloquee (politique autoplay...) : jamais totalement silencieux.
  try { await Promise.all([audio.play(), ended]); } finally { URL.revokeObjectURL(url); }
}

/* ----- capture micro -> WAV mono 16 kHz (envoye a /api/voice) ---------------- */
export class WavRecorder {
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private proc: ScriptProcessorNode | null = null;
  private src: MediaStreamAudioSourceNode | null = null;
  private chunks: Float32Array[] = [];
  private rate = 48000;
  private cancelled = false;

  async start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    if (this.cancelled) {
      // stop() est arrive PENDANT l'attente getUserMedia (appui bref sur V,
      // popup de permission qui vole le focus...) : fermer le flux tout de
      // suite, sinon le micro resterait ouvert sur un enregistreur orphelin.
      stream.getTracks().forEach((t) => t.stop());
      return;
    }
    this.stream = stream;
    try {
      this.ctx = new AudioContext();
      this.rate = this.ctx.sampleRate;
      this.src = this.ctx.createMediaStreamSource(this.stream);
      this.proc = this.ctx.createScriptProcessor(4096, 1, 1);
      this.chunks = [];
      this.proc.onaudioprocess = (e) =>
        this.chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
      this.src.connect(this.proc);
      this.proc.connect(this.ctx.destination);
    } catch (error) {
      await this.stop();
      throw error;
    }
  }

  /** Arrete la capture et renvoie le WAV (ou null si vide). Idempotent :
   *  un second appel ne renvoie pas une seconde copie de l'audio. */
  async stop(): Promise<Blob | null> {
    this.cancelled = true;
    this.proc?.disconnect();
    this.src?.disconnect();
    this.stream?.getTracks().forEach((t) => t.stop());
    const data = mergeFloat(this.chunks);
    this.chunks = [];
    await this.ctx?.close().catch(() => undefined);
    this.ctx = this.stream = this.proc = this.src = null;
    if (!data.length) return null;
    const wav = encodeWav(downsample(data, this.rate, 16000), 16000);
    return new Blob([wav], { type: "audio/wav" });
  }
}

/** One explicitly armed radio. No PCM leaves the worklet until a PTT release. */
export class RadioMic {
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private node: AudioWorkletNode | null = null;
  private disposed = false;
  private rejectPending?: (e: Error) => void;
  private onClip?: (samples: Float32Array | null) => void;

  async arm(onLost: (message: string) => void) {
    try {
      // Unlock audio inside the user's gesture, before the permission dialog.
      const ctx = this.ctx = new AudioContext();
      const resumed = ctx.resume();
      const streamPromise = navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } }).then(stream => {
        if (this.disposed) { stream.getTracks().forEach(t => t.stop()); throw new Error('Mic closed'); }
        this.stream = stream;
        return stream;
      });
      const [stream] = await Promise.all([streamPromise, resumed, ctx.audioWorklet.addModule('/radio-capture.worklet.js')]);
      if (this.disposed) throw new Error('Mic closed');
      const lost = () => { if (!this.disposed) { this.close(); onLost('Microphone interrupted. Enable it again.'); } };
      stream.getAudioTracks().forEach(t => { t.onended = lost; t.onmute = lost; });
      ctx.onstatechange = () => { if (ctx.state !== 'running') lost(); };
      const node = this.node = new AudioWorkletNode(ctx, 'radio-capture', { channelCount: 1, channelCountMode: 'explicit' });
      node.onprocessorerror = lost;
      await new Promise<void>((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('No microphone samples received.')), 5000);
        this.rejectPending = e => { clearTimeout(timer); reject(e); };
        node.port.onmessage = ({ data }) => {
          if (data.type === 'ready') { clearTimeout(timer); this.rejectPending = undefined; resolve(); }
          if (data.type === 'clip') this.onClip?.(data.samples);
        };
        ctx.createMediaStreamSource(stream).connect(node);
        node.connect(ctx.destination); // processor writes silence to its output
      });
    } catch (e) { this.close(); throw e; }
  }
  begin() { this.node!.port.postMessage('begin'); }
  async finish(): Promise<Blob | null> {
    const rate = this.ctx!.sampleRate;
    const samples = await new Promise<Float32Array>((resolve, reject) => {
      this.rejectPending = reject;
      this.onClip = pcm => {
        this.rejectPending = this.onClip = undefined;
        if (pcm) resolve(pcm); else reject(new Error('Transmission exceeds 30 seconds.'));
      };
      this.node!.port.postMessage('end');
    });
    if (!samples.length) return null;
    const rateOut = Math.min(rate, 16000);
    return new Blob([encodeWav(downsample(samples, rate, rateOut), rateOut)], { type: 'audio/wav' });
  }
  close() {
    if (this.disposed) return;
    this.disposed = true;
    this.rejectPending?.(new Error('Mic closed'));
    this.rejectPending = this.onClip = undefined;
    this.node?.port.close();
    this.node?.disconnect();
    this.stream?.getTracks().forEach(t => t.stop());
    void this.ctx?.close().catch(() => undefined);
    this.stream = this.node = this.ctx = null;
  }
}

function mergeFloat(chunks: Float32Array[]): Float32Array {
  const n = chunks.reduce((s, c) => s + c.length, 0);
  const out = new Float32Array(n);
  let o = 0;
  for (const c of chunks) { out.set(c, o); o += c.length; }
  return out;
}

/** Passe-bas 1 pole aller-retour (phase nulle, ~12 dB/oct) applique EN PLACE.
 *  Anti-repliement avant decimation : sans lui, tout contenu > 8 kHz replie
 *  dans la bande utile du WAV 16 kHz envoye au STT. */
function lowpassInPlace(buf: Float32Array, rate: number, cutoff: number) {
  const a = 1 - Math.exp((-2 * Math.PI * cutoff) / rate);
  let y = buf[0] ?? 0;
  for (let i = 0; i < buf.length; i++) { y += a * (buf[i] - y); buf[i] = y; }
  y = buf[buf.length - 1] ?? 0;
  for (let i = buf.length - 1; i >= 0; i--) { y += a * (buf[i] - y); buf[i] = y; }
}

function downsample(buf: Float32Array, from: number, to: number): Float32Array {
  if (to >= from) return buf;
  lowpassInPlace(buf, from, 0.45 * to);   // coupure sous Nyquist cible (7,2 kHz)
  const ratio = from / to;
  const n = Math.round(buf.length / ratio);
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(buf.length, Math.floor((i + 1) * ratio));
    let s = 0;
    for (let j = start; j < end; j++) s += buf[j];
    out[i] = end > start ? s / (end - start) : 0;
  }
  return out;
}

function encodeWav(samples: Float32Array, rate: number): ArrayBuffer {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const wr = (o: number, s: string) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  wr(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); wr(8, "WAVE"); wr(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true);
  v.setUint16(34, 16, true); wr(36, "data"); v.setUint32(40, samples.length * 2, true);
  let o = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    o += 2;
  }
  return buf;
}
