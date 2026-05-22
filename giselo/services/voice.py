import logging
import pathlib
import threading
import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal

log = logging.getLogger(__name__)


class _VADThread(threading.Thread):
    """Monitors mic via webrtcvad; calls on_silence() after sustained silence following speech."""

    def __init__(self, on_silence, rate: int = 16000,
                 silence_ms: int = 1000, min_speech_ms: int = 400,
                 aggressiveness: int = 2, device: str | None = None):
        super().__init__(daemon=True)
        self._on_silence     = on_silence
        self._rate           = rate
        self._silence_ms     = silence_ms
        self._min_speech_ms  = min_speech_ms
        self._aggressiveness = aggressiveness
        self._device, self._pulse_source = _sd_device(device)
        self._stop_ev        = threading.Event()

    def run(self) -> None:
        try:
            import webrtcvad
            import sounddevice as sd
        except ImportError as e:
            log.warning("VAD unavailable: %s", e)
            return

        vad = webrtcvad.Vad(self._aggressiveness)
        frame_ms      = 20
        frame_samples = self._rate * frame_ms // 1000      # 320 @ 16kHz
        frame_bytes   = frame_samples * 2                  # int16 = 2 bytes/sample

        min_speech_frames = self._min_speech_ms // frame_ms
        max_silence_frames = self._silence_ms // frame_ms

        speech_frames  = 0
        silence_frames = 0
        had_speech     = False
        triggered      = False
        buf            = b""  # accumulate until we have a full 20ms chunk
        consec_speech  = 0    # consecutive speech frames after had_speech (noise filter)

        def _cb(indata, frames, _time, _status):
            nonlocal speech_frames, silence_frames, had_speech, triggered, buf, consec_speech
            if triggered or self._stop_ev.is_set():
                return
            # Flatten to mono int16 bytes regardless of device block size
            mono = indata[:, 0] if indata.ndim > 1 else indata.ravel()
            buf += mono.astype(np.int16).tobytes()
            # Process as many complete 20ms frames as available
            while len(buf) >= frame_bytes and not triggered:
                chunk, buf = buf[:frame_bytes], buf[frame_bytes:]
                try:
                    is_speech = vad.is_speech(chunk, self._rate)
                except Exception as e:
                    log.debug("VAD frame skip: %s", e)
                    continue
                if is_speech:
                    speech_frames += 1
                    if speech_frames >= min_speech_frames:
                        had_speech = True
                    if had_speech:
                        consec_speech += 1
                        # Only reset silence counter if sustained re-speech (>80ms),
                        # not a noise blip (1-3 frames = 20-60ms)
                        if consec_speech > 4:
                            silence_frames = 0
                else:
                    consec_speech = 0
                    if had_speech:
                        silence_frames += 1
                        if silence_frames >= max_silence_frames:
                            triggered = True
                            self._stop_ev.set()
                            self._on_silence()

        import os
        if self._pulse_source:
            os.environ["PULSE_SOURCE"] = self._pulse_source
        try:
            # blocksize=0 lets the device choose its natural frame size;
            # we buffer internally to always feed webrtcvad exact 20ms chunks
            devices = [self._device]
            if self._device is not None:
                devices.append(None)  # fallback to system default
            for dev in devices:
                try:
                    with sd.InputStream(samplerate=self._rate, channels=1, device=dev,
                                        dtype="int16", blocksize=0, callback=_cb):
                        self._stop_ev.wait()
                    break
                except Exception as e:
                    if dev is devices[-1]:
                        log.warning("VAD stream error: %s", e)
                    else:
                        log.debug("VAD: device %r failed (%s), trying system default", dev, e)
        finally:
            if self._pulse_source:
                os.environ.pop("PULSE_SOURCE", None)

    def stop(self) -> None:
        self._stop_ev.set()


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
    """Return (sd_device, pulse_source_env) for the configured device.
    sd_device = value for sd.InputStream(device=...), None = system default.
    pulse_source_env = value to set in PULSE_SOURCE env var, or None.
    Pactl source names (alsa_input.*, bluez_input.*) are routed via pulse+PULSE_SOURCE.
    """
    if not cfg_device or cfg_device == "default":
        return None, None
    if cfg_device.startswith(("alsa_input.", "bluez_input.")):
        return "pulse", cfg_device
    return cfg_device, None


class _LevelThread(threading.Thread):
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
    _vad_silence       = pyqtSignal()  # cross-thread safe trigger for auto-stop

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._recording = False
        self._wav_path: pathlib.Path | None = None
        self._level_thread: _LevelThread | None = None
        self._vad_thread: _VADThread | None = None
        self._worker: _TranscribeWorker | None = None
        self._transcriber = None
        self._vad_silence.connect(self.stop_recording)

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

    def start_recording(self, auto_stop: bool = False) -> None:
        if self._recording:
            return
        self._recording = True
        self._wav_path = self._recorder.start()
        audio_cfg  = self._cfg.get("audio", {})
        cfg_device = audio_cfg.get("monitor_device") or audio_cfg.get("device", "default")
        rate       = audio_cfg.get("rate", 16000)
        self._level_thread = _LevelThread(self._emit_level, rate=rate, device=cfg_device)
        self._level_thread.start()
        if auto_stop:
            ao = self._cfg.get("always_on", {})
            self._vad_thread = _VADThread(
                on_silence=self._vad_silence.emit,
                rate=rate,
                silence_ms=ao.get("silence_duration_ms", 1000),
                min_speech_ms=ao.get("min_speech_ms", 400),
                aggressiveness=ao.get("vad_aggressiveness", 2),
                device=cfg_device,
            )
            self._vad_thread.start()
        self.started.emit()
        log.info("VoiceService: recording started (auto_stop=%s)", auto_stop)

    def stop_recording(self) -> None:
        if not self._recording:
            return
        self._recording = False
        if self._vad_thread:
            self._vad_thread.stop()
            self._vad_thread = None
        wav = self._recorder.stop()
        if self._level_thread:
            self._level_thread.stop()
            self._level_thread = None
        self.level_changed.emit(0)
        self.stopped_recording.emit()

        if wav and wav.exists():
            self._worker = _TranscribeWorker(
                self._cfg, wav, self._transcriber, self
            )
            self._worker.transcriber_ready.connect(
                lambda t: setattr(self, "_transcriber", t)
            )
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
