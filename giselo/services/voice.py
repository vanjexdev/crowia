import logging
import pathlib
import threading
import time
import wave
import numpy as np
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

log = logging.getLogger(__name__)


# ── Phase-1: Wake word detector ───────────────────────────────────────────────

class _WakeDetector(threading.Thread):
    """Phase-1 always-on: webrtcvad detects speech onset → tiny Whisper checks wake word.

    Very lightweight: tiny Whisper only runs when webrtcvad fires (not on silence).
    Tiny Whisper on a 2-3s clip takes ~0.3-0.5s on CPU.
    On wake word confirmed → calls on_wake().
    """

    CLIP_AFTER_SPEECH_MS = 1800   # Increased from 1200 for better context
    PRE_SPEECH_MS        = 500    # Increased from 400

    def __init__(self, cfg: dict, wake_words: list[str], on_wake, on_level):
        super().__init__(daemon=True)
        ao                   = cfg.get("always_on", {})
        audio_cfg            = cfg.get("audio", {})
        self._rate           = audio_cfg.get("rate", 16000)
        self._aggressiveness = ao.get("vad_aggressiveness", 3) # More aggressive VAD (1-3)
        cfg_device           = audio_cfg.get("monitor_device") or audio_cfg.get("device", "default")
        self._sd_device, self._pulse_source = _sd_device(cfg_device)
        self._wake_words     = [w.lower() for w in wake_words]
        self._on_wake        = on_wake   # callback()
        self._on_level       = on_level  # callback(int)
        self._stop_ev        = threading.Event()
        self._tiny_model     = None
        self._model_lock     = threading.Lock()

    def stop(self) -> None:
        self._stop_ev.set()

    def _load_model(self):
        with self._model_lock:
            if self._tiny_model is None:
                from faster_whisper import WhisperModel
                log.info("WakeDetector: loading tiny Whisper…")
                self._tiny_model = WhisperModel("tiny", device="cpu", compute_type="int8")
                log.info("WakeDetector: tiny Whisper ready")

    def _check_clip(self, frames: list[bytes]) -> bool:
        """Run tiny Whisper on the buffered clip. Return True if wake word found."""
        if not frames:
            return False
        audio = np.frombuffer(b"".join(frames), dtype=np.int16).astype(np.float32) / 32768.0
        try:
            segs, _ = self._tiny_model.transcribe(
                audio,
                language="es",
                beam_size=5, # Increased from 1 for better accuracy
                temperature=0,
                vad_filter=True, # Enable internal filter too
                no_speech_threshold=0.5, # Lowered from 0.7 to be less strict
            )
            import re
            raw_text = " ".join(s.text for s in segs).lower().strip()
            # Clean common transcription artifacts like ¿ ? ! . ,
            text = re.sub(r'[¿?!\.,]', '', raw_text).strip()
            log.info("WakeDetector heard: '%s' (raw: %r)", text, raw_text)

            if not text:
                return False

            # Direct match
            for w in self._wake_words:
                if w in text:
                    return True

            # fuzzy phonetic match for common Whisper "tiny" errors on "Giselo/Gisela"
            # remove spaces for the check: "hi se lo" -> "hiselo"
            text_no_space = text.replace(" ", "")
            fuzzy_variants = [
                "jicelo", "jiselo", "diselo", "selo", "iselo", "isela", "icela",
                "hicelo", "hiselo", "ojicelo", "ojiselo", "hiselo", "hicelo"
            ]
            for v in fuzzy_variants:
                if v in text_no_space:
                    log.info("WakeDetector: fuzzy match on '%s' in '%s'", v, text_no_space)
                    return True

            return False
        except Exception as e:
            log.debug("WakeDetector transcribe error: %s", e)
            return False

    def run(self) -> None:
        import os
        try:
            import webrtcvad
            import sounddevice as sd
        except ImportError as e:
            log.error("WakeDetector deps missing: %s", e)
            return

        self._load_model()

        vad          = webrtcvad.Vad(self._aggressiveness)
        frame_ms     = 20
        frame_samp   = self._rate * frame_ms // 1000
        frame_bytes  = frame_samp * 2

        pre_frames   = self.PRE_SPEECH_MS // frame_ms
        post_frames  = self.CLIP_AFTER_SPEECH_MS // frame_ms

        # State
        buf          = b""
        ring         = []            # pre-speech ring buffer
        clip         = []            # current capture (pre + speech + post)
        capturing    = False
        cap_frames   = 0
        triggered    = False

        if self._pulse_source:
            os.environ["PULSE_SOURCE"] = self._pulse_source

        def _cb(indata, n_frames, _time, status):
            nonlocal buf, ring, clip, capturing, cap_frames, triggered

            if triggered or self._stop_ev.is_set():
                raise sd.CallbackStop()

            mono = indata[:, 0] if indata.ndim > 1 else indata.ravel()

            # Level
            rms = float(np.sqrt(np.mean(mono.astype(np.float32) ** 2)))
            self._on_level(min(100, int(rms * 600)))

            buf += mono.astype(np.int16).tobytes()

            while len(buf) >= frame_bytes and not triggered:
                chunk, buf = buf[:frame_bytes], buf[frame_bytes:]

                try:
                    is_speech = vad.is_speech(chunk, self._rate)
                except Exception:
                    continue

                if not capturing:
                    ring.append(chunk)
                    if len(ring) > pre_frames:
                        ring.pop(0)
                    if is_speech:
                        capturing = True
                        cap_frames = 0
                        clip = list(ring) + [chunk]
                else:
                    clip.append(chunk)
                    cap_frames += 1
                    if cap_frames >= post_frames:
                        # Enough audio — transcribe in a side thread
                        triggered = True
                        self._stop_ev.set()
                        raise sd.CallbackStop()

        try:
            devices = [self._sd_device]
            if self._sd_device is not None:
                devices.append(None)
            for dev in devices:
                try:
                    with sd.InputStream(samplerate=self._rate, channels=1, device=dev,
                                        dtype="int16", blocksize=0, callback=_cb):
                        self._stop_ev.wait()
                    break
                except sd.CallbackStop:
                    break
                except Exception as e:
                    if dev is devices[-1]:
                        log.warning("WakeDetector stream error: %s", e)
                    else:
                        log.debug("WakeDetector: device %r failed, trying default", dev)
        finally:
            if self._pulse_source:
                os.environ.pop("PULSE_SOURCE", None)

        if clip and self._check_clip(clip):
            self._on_wake()


# ── Phase-2: Command recorder ─────────────────────────────────────────────────

class _AlwaysOnStream(threading.Thread):
    """Phase-2: captures the user's command after wake word confirmed.
    Single sounddevice stream: VAD + recording + level in one callback.
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
        self._on_audio_ready  = on_audio_ready
        self._on_level        = on_level
        self._on_silence_fired = on_silence_fired
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
        frame_samples = self._rate * frame_ms // 1000
        frame_bytes   = frame_samples * 2

        min_speech_frames  = self._min_speech_ms // frame_ms
        max_silence_frames = self._silence_ms // frame_ms
        max_frames         = int(self._max_sec * 1000 / frame_ms)
        # Warmup: discard first 300ms (speaker echo / mic stabilization)
        warmup_frames      = 300 // frame_ms

        frames_buf      = b""
        recorded_chunks = []
        frames_total    = 0
        speech_frames   = 0
        silence_frames  = 0
        consec_speech   = 0
        had_speech      = False
        done            = False

        def _cb(indata, n_frames, _time, status):
            nonlocal frames_buf, recorded_chunks, frames_total
            nonlocal speech_frames, silence_frames, consec_speech, had_speech, done

            if done or self._stop_ev.is_set():
                raise sd.CallbackStop()

            rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
            self._on_level(min(100, int(rms * 600)))

            mono = indata[:, 0] if indata.ndim > 1 else indata.ravel()
            frames_buf += mono.astype(np.int16).tobytes()

            while len(frames_buf) >= frame_bytes:
                chunk, frames_buf = frames_buf[:frame_bytes], frames_buf[frame_bytes:]
                frames_total += 1

                if frames_total <= warmup_frames:
                    continue

                recorded_chunks.append(chunk)

                if len(recorded_chunks) >= max_frames:
                    log.info("AlwaysOnStream: max_record_seconds reached")
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
                        if consec_speech > 4:
                            silence_frames = 0
                else:
                    consec_speech = 0
                    if had_speech:
                        silence_frames += 1
                        if silence_frames >= max_silence_frames:
                            log.info("AlwaysOnStream: silence after speech")
                            done = True
                            self._stop_ev.set()
                            raise sd.CallbackStop()

        try:
            devices = [self._sd_device]
            if self._sd_device is not None:
                devices.append(None)
            for dev in devices:
                try:
                    with sd.InputStream(samplerate=self._rate, channels=1, device=dev,
                                        dtype="int16", blocksize=0, callback=_cb):
                        self._stop_ev.wait()
                    break
                except sd.CallbackStop:
                    break
                except Exception as e:
                    if dev is devices[-1]:
                        log.warning("AlwaysOnStream error: %s", e)
                    else:
                        log.debug("AlwaysOnStream: device %r failed, trying default", dev)
        finally:
            if self._pulse_source:
                os.environ.pop("PULSE_SOURCE", None)

        if not had_speech:
            log.debug("AlwaysOnStream: no speech, discarding")
            self._on_silence_fired()
            return

        # Trim trailing silence
        frame_ms_f = frame_ms
        trail_frames = int(500 / frame_ms_f)
        last_speech = len(recorded_chunks)
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

        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        wav_path = self._tmp_dir / f"ao_{int(time.time())}.wav"
        try:
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self._rate)
                wf.writeframes(b"".join(keep))
            log.info("AlwaysOnStream: wrote %s (%.1fs)", wav_path, len(keep) * frame_ms / 1000)
        except Exception as e:
            log.error("AlwaysOnStream: WAV write failed: %s", e)
            self._on_silence_fired()
            return

        self._on_silence_fired()
        self._on_audio_ready(wav_path)


# ── Transcription worker ──────────────────────────────────────────────────────

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sd_device(cfg_device: str | None) -> tuple:
    if not cfg_device or cfg_device == "default":
        return None, None
    if cfg_device.startswith(("alsa_input.", "bluez_input.")):
        return "pulse", cfg_device
    return cfg_device, None


class _LevelThread(threading.Thread):
    """Level meter for manual (hotkey) recording."""

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
                self._on_level(min(100, int(rms * 600)))

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
                        log.debug("Level: device %r failed, trying default", dev)
        finally:
            if self._pulse_source:
                os.environ.pop("PULSE_SOURCE", None)

    def stop(self) -> None:
        self._stop.set()


# ── VoiceService ──────────────────────────────────────────────────────────────

class VoiceService(QObject):
    started            = pyqtSignal()
    stopped_recording  = pyqtSignal()
    transcribed        = pyqtSignal(str)
    error              = pyqtSignal(str)
    level_changed      = pyqtSignal(int)
    wake_detected      = pyqtSignal()          # always-on: wake word confirmed
    # Internal cross-thread signals
    _ao_audio_ready    = pyqtSignal(object)    # Path
    _ao_silence_fired  = pyqtSignal()
    _wake_confirmed    = pyqtSignal()          # from WakeDetector thread → main thread

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._recording = False
        self._wav_path: pathlib.Path | None = None
        self._level_thread: _LevelThread | None = None
        self._ao_stream: _AlwaysOnStream | None = None
        self._wake_detector: _WakeDetector | None = None
        self._worker: _TranscribeWorker | None = None
        self._transcriber = None
        self._max_rec_timer = QTimer(self)
        self._max_rec_timer.setSingleShot(True)
        self._max_rec_timer.timeout.connect(self.stop_recording)

        self._ao_audio_ready.connect(self._on_ao_audio_ready)
        self._ao_silence_fired.connect(self._on_ao_silence_fired)
        self._wake_confirmed.connect(self._on_wake_confirmed)

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
        return self._recording or (
            self._worker is not None and self._worker.isRunning()
        )

    @property
    def wake_listening(self) -> bool:
        return self._wake_detector is not None

    # ── Always-on: two-phase ──────────────────────────────────────────────────

    def start_wake_listening(self, wake_words: list[str]) -> None:
        """Phase 1: start lightweight wake word detector."""
        if self._wake_detector is not None:
            return
        log.info("WakeDetector: starting, words=%s", wake_words)
        self._wake_detector = _WakeDetector(
            cfg=self._cfg,
            wake_words=wake_words,
            on_wake=lambda: self._wake_confirmed.emit(),
            on_level=lambda lvl: self.level_changed.emit(lvl),
        )
        self._wake_detector.start()

    def stop_wake_listening(self) -> None:
        if self._wake_detector:
            self._wake_detector.stop()
            self._wake_detector = None
        self.level_changed.emit(0)

    def _on_wake_confirmed(self) -> None:
        """Main thread: wake word detected → stop detector, start command recording."""
        self._wake_detector = None   # thread exits after calling on_wake
        self.level_changed.emit(0)
        self.wake_detected.emit()    # window.py uses this for UI state
        log.info("Wake word confirmed, starting command recording")
        self._start_always_on_stream()
        self._recording = True
        self.started.emit()

    def _start_always_on_stream(self) -> None:
        ao = self._cfg.get("always_on", {})
        max_sec = ao.get("max_record_seconds", 120)
        self._ao_stream = _AlwaysOnStream(
            cfg=self._cfg,
            on_audio_ready=lambda p: self._ao_audio_ready.emit(p),
            on_level=lambda lvl: self.level_changed.emit(lvl),
            on_silence_fired=lambda: self._ao_silence_fired.emit(),
        )
        self._ao_stream.start()
        self._max_rec_timer.start(max_sec * 1000)

    def _on_ao_silence_fired(self) -> None:
        if not self._recording:
            return
        self._recording = False
        self._max_rec_timer.stop()
        self._ao_stream = None
        self.level_changed.emit(0)
        self.stopped_recording.emit()

    def _on_ao_audio_ready(self, wav_path: pathlib.Path) -> None:
        if not wav_path.exists():
            self.error.emit("No audio recorded")
            return
        self._worker = _TranscribeWorker(self._cfg, wav_path, self._transcriber, self)
        self._worker.transcriber_ready.connect(lambda t: setattr(self, "_transcriber", t))
        self._worker.done.connect(self._on_transcribed)
        self._worker.error.connect(self.error)
        self._worker.start()

    # ── Manual recording (hotkey) ─────────────────────────────────────────────

    def start_recording(self, auto_stop: bool = False) -> None:
        """Manual hotkey recording — uses arecord + level thread."""
        if self._recording:
            return
        self._recording = True
        self._wav_path = self._recorder.start()
        audio_cfg  = self._cfg.get("audio", {})
        cfg_device = audio_cfg.get("monitor_device") or audio_cfg.get("device", "default")
        rate       = audio_cfg.get("rate", 16000)
        self._level_thread = _LevelThread(self._emit_level, rate=rate, device=cfg_device)
        self._level_thread.start()
        max_sec = self._cfg.get("hotkey", {}).get("max_record_seconds", 300)
        self._max_rec_timer.start(max_sec * 1000)
        self.started.emit()
        log.info("VoiceService: manual recording started")

    def stop_recording(self) -> None:
        self._max_rec_timer.stop()

        if self._wake_detector:
            self._wake_detector.stop()
            self._wake_detector = None
            self.level_changed.emit(0)
            return

        if not self._recording:
            return
        self._recording = False

        if self._ao_stream:
            self._ao_stream.stop()
            self._ao_stream = None
            self.level_changed.emit(0)
            self.stopped_recording.emit()
            return

        # Manual mode
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
