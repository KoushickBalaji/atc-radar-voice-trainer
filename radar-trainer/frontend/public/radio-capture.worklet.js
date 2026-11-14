// Boundaries and look-back live on the audio thread, independent of radar renders.
class RadioCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.history = new Float32Array(Math.ceil(sampleRate * 0.2));
    this.cursor = this.filled = 0;
    this.clip = null;
    this.port.onmessage = ({ data }) => {
      if (data === 'cancel') {
        this.clip = null;
        this.filled = this.cursor = 0;
      } else if (data === 'begin' && !this.clip) {
        this.clip = new Float32Array(sampleRate * 30);
        const tail = this.history.subarray(this.history.length - this.filled + this.cursor);
        this.clip.set(tail);
        this.clip.set(this.history.subarray(0, this.cursor), tail.length);
        this.length = this.filled;
        this.preRoll = this.filled;
        this.overflow = false;
        this.filled = this.cursor = 0;
      } else if (data === 'end' && this.clip) {
        // A tap must not transmit idle conversation just because the ring is full.
        const held = this.length - this.preRoll;
        const samples = this.overflow ? null : held < sampleRate * 0.1
          ? new Float32Array(0) : this.clip.slice(0, this.length);
        this.clip = null;
        this.port.postMessage({ type: 'clip', samples }, samples ? [samples.buffer] : []);
      }
    };
  }
  process(inputs) {
    const block = inputs[0]?.[0];
    if (!block?.length) return true;
    if (this.clip) {
      if (this.length + block.length > this.clip.length) this.overflow = true;
      else { this.clip.set(block, this.length); this.length += block.length; }
    } else {
      for (const sample of block) {
        this.history[this.cursor] = sample;
        this.cursor = (this.cursor + 1) % this.history.length;
      }
      this.filled = Math.min(this.filled + block.length, this.history.length);
      if (!this.ready && this.filled === this.history.length) {
        this.ready = true;
        this.port.postMessage({ type: 'ready' });
      }
    }
    return true;
  }
}
registerProcessor('radio-capture', RadioCapture);
