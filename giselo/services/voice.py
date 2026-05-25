import logging
import pathlib
import threading
import time
import wave
import numpy as np
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

log = logging.getLogger(__name__)


class _AlwaysOnStream(threading.Thread):
    """Single sounddevice stream: VAD + recording + level in one callback.

    No arecord subprocess. No device conflicts. Captures frames, runs webrtcvad,
    accumulates speech into memory, writes WAV when silence detected.
    """

    def __init__(self, cfg: dict, on_audio_ready, on_level, on_silence_fired):
        super().__init__(daemon=True)
        ao             = cfg.get("always_on", {})
        audio_cfg      = cfg.get("audio", {})
        self._rate     = audio_cfg.get("rate", 16000)
        self._silence_ms   = ao.get("silence_duration_ms", 1500)
        self._min_speech_ms = ao.get("min_speech_ms", 600)
        self._aggressiveness = ao.get("vad_aggressiveness", 2)
        self._max_sec  = ao.get("max_record_seconds", 120)
        cfg_device     = audio_cfg.get("monitor_device") or audio_cfg.get("device", "default")
        self._sd_device, self._pulse_source = _sd_device(cfg_device)
        self._on_audio_ready  = on_audio_ready   # callback(wav_path: Path)
        self._on_level        = on_level          # callback(level: int)
        self._on_silence_fired = on_silence_fired # callback() — so VoiceService knows
        self._stop_ev  = threading.Event()
        self._tmp_dir  = pathlib.Path(audio_cfg.get("tmp_dir", "/tmp/crowia"))

    def stop(self) -> None:
        self._stop_ev.set()

    def run(self) -> None:
        import os
        try:
            import webrtcvad
            import sounddevice as sd
        except ImportError as e:
            log.error("AlwaysOnStream deps missing: %s", e)
            return

        if self._pulse_source:
            os.environ["PULSE_SOURCE"] = self._pulse_source

        vad = webrtcvad.Vad(self._aggressiveness)
        frame_ms      = 20
        frame_samples = self._rate * frame_ms // 1000   # 320 samples @ 16kHz
        frame_bytes   = frame_samples * 2               # int16

        min_speech_frames  = self._min_speech_ms // frame_ms
        max_silence_frames = self._silence_ms // frame_ms
        max_frames         = int(self._max_sec * 1000 / frame_ms)

        # State
        frames_buf      = b""          # raw bytes accumulator for 20ms chunks
        recorded_chunks = []           # list of 20ms byte chunks (captured speech)
        speech_frames   = 0
        silence_frames  = 0
        consec_speech   = 0
        had_speech      = False
        done            = False
        start_time      = time.monotonic()

        def _cb(indata, n_frames, _time, status):
            nonlocal frames_buf, recorded_chunks
            nonlocal speech_frames, silence_frames, consec_speech, had_speech, done

            if done or self._stop_ev.is_set():
                raise sd.CallbackStop()

            # Level meter (fast path, no VAD needed)
            rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
            level = min(100, int(rms * 600))
            self._on_level(level)

            mono = indata[:, 0] if indata.ndim > 1 else indata.ravel()
            frames_buf += mono.astype(np.int16).tobytes()

            while len(frames_buf) >= frame_bytes:
                chunk, frames_buf = frames_buf[:frame_bytes], frames_buf[frame_bytes:]

                # Always accumulate — we keep pre-speech and speech frames
                recorded_chunks.append(chunk)

                # Hard cap
                if len(recorded_chunks) >= max_frames:
                    log.info("AlwaysOnStream: max_record_seconds reached, stopping")
                    done = True
                    self._stop_ev.set()
                    raise sd.CallbackStop()

                try:
                    is_speech = vad.is_speech(chunk, self._rate)
                except Exception:
                    continue

                if is_speech:
                    speech_frames += 1
                    if speech_frames >= min_speech_frames:
                        had_speech = True
                    if had_speech:
                        consec_speech += 1
                        if consec_speech > 4:   # >80ms sustained — real re-speech
                            silence_frames = 0
                else:
                    consec_speech = 0
                    if had_speech:
                        silence_frames += 1
                        if silence_frames >= max_silence_frames:
                            log.info("AlwaysOnStream: silence detected after speech")
                            done = True
                            self._stop_ev.set()
                            raise sd.CallbackStop()

        try:
            devices = [self._sd_device]
            if self._sd_device is not None:
                devices.append(None)  # fallback
            for dev in devices:
                try:
                    with sd.InputStream(
                        samplerate=self._rate, channels=1, device=dev,
                        dtype="int16", blocksize=0, callback=_cb,
                    ):
                        self._stop_ev.wait()
                    break
                except sd.CallbackStop:
                    break
                except Exception as e:
                    if dev is devices[-1]:
                        log.warning("AlwaysOnStream open failed: %s", e)
                    else:
                        log.debug("AlwaysOnStream: device %r failed (%s), trying default", dev, e)
        finally:
            if self._pulse_source:
                os.environ.pop("PULSE_SOURCE", None)

        if not had_speech:
            log.debug("AlwaysOnStream: no speech detected, discarding")
            self._on_silence_fired()
            return

        # Trim trailing silence (keep max 0.5s after last speech)
        trail_frames = int(500 / frame_ms)
        last_speech  = len(recorded_chunks)
        for i in range(len(recorded_chunks) - 1, -1, -1):
            try:
                if vad.is_speech(recorded_chunks[i], self._rate):
                    last_speech = i + 1
                    break
            except Exception:
                break
        keep = recorded_chunks[:last_speech + trail_frames]

        if not keep:
            self._on_silence_fired()
            return

        # Write WAV
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        wav_path = self._tmp_dir / f"ao_{int(time.time())}.wav"
        try:
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self._rate)
                wf.writeframes(b"".join(keep))
            log.info("AlwaysOnStream: wrote %s (%.1fs)", wav_path,
                     len(keep) * frame_ms / 1000)
        except Exception as e:
            log.error("AlwaysOnStream: WAV write failed: %s", e)
            self._on_silence_fired()
            return

        self._on_silence_fired()
        self._on_audio_ready(wav_path)


class _TranscribeWorker(QThread):
    done              = pyqtSignal(str)
    error             = pyqtSignal(str)
    transcriber_ready = pyqtSignal(object)

    def __init__(self, cfg: dict, wav_path: pathlib.Path,
                 transcriber=None, parent=None):
        super().__init__(parent)
        self._cfg         = cfg
        self._wav_path    = wav_path
        self._transcriber = transcriber

    def run(self) -> None:
        try:
            t = self._transcriber
            if t is None:
                from crowia.transcriber import Transcriber
                t = Transcriber(self._cfg)
                self.transcriber_ready.emit(t)
            text = t.transcribe(self._wav_path)
            self.done.emit(text.strip())
        except Exception as e:
            log.exception("Transcription failed")
            self.error.emit(str(e))


def _sd_device(cfg_device: str | None) -> tuple:
    """Return (sd_device, pulse_source_env) for the configured device."""
    if not cfg_device or cfg_device == "default":
        return None, None
    if cfg_device.startswith(("alsa_input.", "bluez_input.")):
        return "pulse", cfg_device
    return cfg_device, None


class _LevelThread(threading.Thread):
    """Level meter for manual recording mode (arecord-based)."""

    def __init__(self, on_level, rate: int = 16000, device: str | None = None):
        super().__init__(daemon=True)
        self._on_level = on_level
        self._rate = rate
        self._device, self._pulse_source = _sd_device(device)
        self._stop = threading.Event()

    def run(self) -> None:
        import os
        try:
            import sounddevice as sd
            if self._pulse_source:
                os.environ["PULSE_SOURCE"] = self._pulse_source

            def _cb(indata, frames, time_info, status):
                rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
                level = min(100, int(rms * 600))
                self._on_level(level)

            devices = [self._device]
            if self._device is not None:
                devices.append(None)
            for dev in devices:
                try:
                    with sd.InputStream(samplerate=self._rate, channels=1, device=dev,
                                        dtype="int16", blocksize=1024, callback=_cb):
                        self._stop.wait()
                    break
                except Exception as e:
                    if dev is devices[-1]:
                        log.warning("Level monitor failed: %s", e)
                    else:
                        log.debug("Level: device %r failed (%s), trying system default", dev, e)
        finally:
            if self._pulse_source:
                os.environ.pop("PULSE_SOURCE", None)

    def stop(self) -> None:
        self._stop.set()


class VoiceService(QObject):
    started            = pyqtSignal()
    stopped_recording  = pyqtSignal()
    transcribed        = pyqtSignal(str)
    error              = pyqtSignal(str)
    level_changed      = pyqtSignal(int)
    # Internal cross-thread signals
    _ao_audio_ready    = pyqtSignal(object)   # Path — always-on WAV ready
    _ao_silence_fired  = pyqtSignal()          # stream finished (with or without audio)

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._recording = False
        self._wav_path: pathlib.Path | None = None
        self._level_thread: _LevelThread | None = None
        self._ao_stream: _AlwaysOnStream | None = None
        self._worker: _TranscribeWorker | None = None
        self._transcriber = None
        self._max_rec_timer = QTimer(self)
        self._max_rec_timer.setSingleShot(True)
        self._max_rec_timer.timeout.connect(self.stop_recording)

        self._ao_audio_ready.connect(self._on_ao_audio_ready)
        self._ao_silence_fired.connect(self._on_ao_silence_fired)

        from crowia.recorder import Recorder
        self._recorder = Recorder(cfg)

        threading.Thread(target=self._prewarm_whisper, daemon=True).start()

    def _prewarm_whisper(self) -> None:
        try:
            from crowia.transcriber import Transcriber
            self._transcriber = Transcriber(self._cfg)
            log.info("Whisper pre-warmed")
        except Exception as e:
            log.warning("Whisper prewarm failed: %s", e)

    @property
    def recording(self) -> bool:
        return self._recording

    @property
    def busy(self) -> bool:
        """True while recording OR transcription worker is running."""
        return self._recording or (
            self._worker is not None and self._worker.isRunning()
        )

    # ── Manual recording (hotkey) ─────────────────────────────────────────────

    def start_recording(self, auto_stop: bool = False) -> None:
        if self._recording:
            return
        self._recording = True

        if auto_stop:
            self._start_always_on_stream()
        else:
            self._start_manual_stream()

        self.started.emit()
        log.info("VoiceService: recording started (auto_stop=%s)", auto_stop)

    def _start_manual_stream(self) -> None:
        """arecord subprocess + level meter — for hotkey-triggered recording."""
        self._wav_path = self._recorder.start()
        audio_cfg  = self._cfg.get("audio", {})
        cfg_device = audio_cfg.get("monitor_device") or audio_cfg.get("device", "default")
        rate       = audio_cfg.get("rate", 16000)
        self._level_thread = _LevelThread(self._emit_level, rate=rate, device=cfg_device)
        self._level_thread.start()
        ao = self._cfg.get("always_on", {})
        max_sec = self._cfg.get("hotkey", {}).get("max_record_seconds", 300)
        self._max_rec_timer.start(max_sec * 1000)

    def _start_always_on_stream(self) -> None:
        """Single unified sounddevice stream — VAD + recording + level."""
        self._ao_stream = _AlwaysOnStream(
            cfg=self._cfg,
            on_audio_ready=lambda p: self._ao_audio_ready.emit(p),
            on_level=lambda lvl: self.level_changed.emit(lvl),
            on_silence_fired=lambda: self._ao_silence_fired.emit(),
        )
        self._ao_stream.start()

    def _on_ao_silence_fired(self) -> None:
        """Always-on stream finished — update recording state."""
        if not self._recording:
            return
        self._recording = False
        self._ao_stream = None
        self.level_changed.emit(0)
        self.stopped_recording.emit()

    def _on_ao_audio_ready(self, wav_path: pathlib.Path) -> None:
        """Always-on: WAV is ready, kick off transcription."""
        if not wav_path.exists():
            self.error.emit("No audio recorded")
            return
        self._worker = _TranscribeWorker(self._cfg, wav_path, self._transcriber, self)
        self._worker.transcriber_ready.connect(lambda t: setattr(self, "_transcriber", t))
        self._worker.done.connect(self._on_transcribed)
        self._worker.error.connect(self.error)
        self._worker.start()

    # ── Manual stop ───────────────────────────────────────────────────────────

    def stop_recording(self) -> None:
        if not self._recording:
            return
        self._recording = False
        self._max_rec_timer.stop()

        if self._ao_stream:
            self._ao_stream.stop()
            self._ao_stream = None
            # _on_ao_silence_fired already emits stopped_recording via signal;
            # but since we forced stop, emit directly
            self.level_changed.emit(0)
            self.stopped_recording.emit()
            return

        # Manual mode: stop arecord
        if self._level_thread:
            self._level_thread.stop()
            self._level_thread = None
        wav = self._recorder.stop()
        self.level_changed.emit(0)
        self.stopped_recording.emit()

        if wav and wav.exists():
            self._worker = _TranscribeWorker(self._cfg, wav, self._transcriber, self)
            self._worker.transcriber_ready.connect(lambda t: setattr(self, "_transcriber", t))
            self._worker.done.connect(self._on_transcribed)
            self._worker.error.connect(self.error)
            self._worker.start()
        else:
            self.error.emit("No audio recorded")

    def _emit_level(self, level: int) -> None:
        self.level_changed.emit(level)

    def _on_transcribed(self, text: str) -> None:
        if text:
            self.transcribed.emit(text)
        else:
            self.error.emit("No se detectó voz")
