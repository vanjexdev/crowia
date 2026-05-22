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
                 aggressiveness: int = 2):
        super().__init__(daemon=True)
        self._on_silence    = on_silence
        self._rate          = rate
        self._silence_ms    = silence_ms
        self._min_speech_ms = min_speech_ms
        self._aggressiveness = aggressiveness
        self._stop_ev       = threading.Event()

    def run(self) -> None:
        try:
            import webrtcvad
            import sounddevice as sd
        except ImportError as e:
            log.warning("VAD unavailable: %s", e)
            return

        vad = webrtcvad.Vad(self._aggressiveness)
        frame_ms      = 20
        frame_samples = self._rate * frame_ms // 1000  # 320 @ 16kHz

        min_speech_frames = self._min_speech_ms // frame_ms
        max_silence_frames = self._silence_ms // frame_ms

        speech_frames  = 0
        silence_frames = 0
        had_speech     = False
        triggered      = False

        def _cb(indata, frames, _time, _status):
            nonlocal speech_frames, silence_frames, had_speech, triggered
            if triggered or self._stop_ev.is_set():
                return
            raw = indata.tobytes()
            try:
                is_speech = vad.is_speech(raw, self._rate)
            except Exception:
                return
            if is_speech:
                speech_frames += 1
                silence_frames = 0
                if speech_frames >= min_speech_frames:
                    had_speech = True
            else:
                if had_speech:
                    silence_frames += 1
                    if silence_frames >= max_silence_frames:
                        triggered = True
                        self._stop_ev.set()
                        self._on_silence()

        try:
            with sd.InputStream(samplerate=self._rate, channels=1,
                                dtype="int16", blocksize=frame_samples,
                                callback=_cb):
                self._stop_ev.wait()
        except Exception as e:
            log.warning("VAD stream error: %s", e)

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


class _LevelThread(threading.Thread):
    def __init__(self, on_level, rate: int = 16000):
        super().__init__(daemon=True)
        self._on_level = on_level
        self._rate = rate
        self._stop = threading.Event()

    def run(self) -> None:
        try:
            import sounddevice as sd

            def _cb(indata, frames, time_info, status):
                rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
                level = min(100, int(rms * 600))
                self._on_level(level)

            with sd.InputStream(samplerate=self._rate, channels=1,
                                dtype="int16", blocksize=1024, callback=_cb):
                self._stop.wait()
        except Exception as e:
            log.warning("Level monitor failed: %s", e)

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
        self._level_thread = _LevelThread(self._emit_level)
        self._level_thread.start()
        if auto_stop:
            ao = self._cfg.get("always_on", {})
            self._vad_thread = _VADThread(
                on_silence=self._vad_silence.emit,
                rate=self._cfg.get("audio", {}).get("rate", 16000),
                silence_ms=ao.get("silence_duration_ms", 1000),
                min_speech_ms=ao.get("min_speech_ms", 400),
                aggressiveness=ao.get("vad_aggressiveness", 2),
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
