'use strict';

export class AudioRecorder {
  constructor() {
    this._recorder = null;
    this._chunks = [];
    this._stream = null;
  }

  async start() {
    this._stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm';
    this._recorder = new MediaRecorder(this._stream, { mimeType });
    this._chunks = [];
    this._recorder.ondataavailable = e => { if (e.data.size > 0) this._chunks.push(e.data); };
    this._recorder.start(200);
  }

  async stop() {
    if (!this._recorder) return null;
    return new Promise(resolve => {
      this._recorder.onstop = () => {
        const blob = new Blob(this._chunks, { type: this._recorder.mimeType });
        this._chunks = [];
        this._stream.getTracks().forEach(t => t.stop());
        this._stream = null;
        this._recorder = null;
        resolve(blob);
      };
      this._recorder.stop();
    });
  }

  get active() { return this._recorder !== null; }
}

export class AudioPlayer {
  constructor() {
    this._ctx = null;
    this._queue = Promise.resolve();
  }

  /** Call once on any user gesture to unblock autoplay policy. */
  unlock() {
    if (!this._ctx) this._ctx = new AudioContext();
    if (this._ctx.state === 'suspended') this._ctx.resume();
  }

  _ctx_get() {
    if (!this._ctx) this._ctx = new AudioContext();
    return this._ctx;
  }

  playWav(arrayBuffer) {
    const ctx = this._ctx_get();
    this._queue = this._queue.then(async () => {
      try {
        if (ctx.state === 'suspended') await ctx.resume();
        const decoded = await ctx.decodeAudioData(arrayBuffer);
        await new Promise(resolve => {
          const src = ctx.createBufferSource();
          src.buffer = decoded;
          src.connect(ctx.destination);
          src.onended = resolve;
          src.start();
        });
      } catch (e) {
        console.warn('Audio playback error:', e);
      }
    });
  }
}
