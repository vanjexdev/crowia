import logging
import pathlib
import threading
import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal

log = logging.getLogger(__name__)


class _TranscribeWorker(QThread):
    done  = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, cfg: dict, wav_path: pathlib.Path, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._wav_path = wav_path

    def run(self) -> None:
        try:
            from crowia.transcriber import Transcriber
            t = Transcriber(self._cfg)
            text = t.transcribe(self._wav_path)
            self.done.emit(text.strip())
        except Exception as e:
            log.exception("Transcription failed")
            self.error.emit(str(e))


class _LevelThread(threading.Thread):
    """Runs a sounddevice InputStream in a daemon thread; calls `on_level(int 0-100)`."""

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

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._recording = False
        self._wav_path: pathlib.Path | None = None
        self._level_thread: _LevelThread | None = None
        self._worker: _TranscribeWorker | None = None

        from crowia.recorder import Recorder
        self._recorder = Recorder(cfg)

    @property
    def recording(self) -> bool:
        return self._recording

    def start_recording(self) -> None:
        if self._recording:
            return
        self._recording = True
        self._wav_path = self._recorder.start()
        self._level_thread = _LevelThread(self._emit_level)
        self._level_thread.start()
        self.started.emit()
        log.info("VoiceService: recording started")

    def stop_recording(self) -> None:
        if not self._recording:
            return
        self._recording = False
        wav = self._recorder.stop()
        if self._level_thread:
            self._level_thread.stop()
            self._level_thread = None
        self.level_changed.emit(0)
        self.stopped_recording.emit()

        if wav and wav.exists():
            self._worker = _TranscribeWorker(self._cfg, wav, self)
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
