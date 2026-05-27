import logging
import pathlib
import queue
import subprocess
import sys
from PyQt6.QtCore import QObject, QThread, pyqtSignal

_SCRIPTS = pathlib.Path(__file__).resolve().parents[2] / "scripts"

log = logging.getLogger(__name__)


class _SpeakWorker(QThread):
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, handler, text: str, parent=None):
        super().__init__(parent)
        self._handler = handler
        self._text    = text

    def run(self) -> None:
        try:
            self._handler._speak(self._text)
            self.finished.emit()
        except Exception as e:
            log.exception("TTS speak failed")
            self.error.emit(str(e))


class _StreamingTTSWorker(QThread):
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, handler, tts_cmd: list[str], parent=None):
        super().__init__(parent)
        self._handler  = handler
        self._tts_cmd  = tts_cmd
        self._queue: queue.SimpleQueue[str | None] = queue.SimpleQueue()
        self._player   = None

    def enqueue(self, sentence: str) -> None:
        self._queue.put(sentence)

    def finish(self) -> None:
        self._queue.put(None)

    def stop(self) -> None:
        self._queue.put(None)
        if self._player is not None:
            self._player.stop()

    def run(self) -> None:
        from crowia.output import StreamingTTSPlayer
        is_piper = bool(self._tts_cmd) and "piper" in pathlib.Path(self._tts_cmd[0]).name
        use_elevenlabs = (
            getattr(self._handler, "el_enabled", False)
            and getattr(self._handler, "el_api_key", "")
            and getattr(self._handler, "el_voice_id", "")
        )
        try:
            if use_elevenlabs:
                # Speak each sentence individually via ElevenLabs
                while True:
                    sentence = self._queue.get()
                    if sentence is None:
                        break
                    if sentence.strip():
                        self._handler._speak(sentence)
            elif is_piper and sys.platform == "linux":
                self._player = StreamingTTSPlayer(self._tts_cmd)
                while True:
                    sentence = self._queue.get()
                    if sentence is None:
                        break
                    self._player.write(sentence)
                self._player.finish()
            else:
                sentences: list[str] = []
                while True:
                    s = self._queue.get()
                    if s is None:
                        break
                    sentences.append(s)
                if sentences:
                    self._handler._speak(" ".join(sentences))
            self.finished.emit()
        except Exception as e:
            log.exception("Streaming TTS failed")
            self.error.emit(str(e))


class TTSService(QObject):
    started  = pyqtSignal()
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        from crowia.output import OutputHandler
        self._handler  = OutputHandler(cfg)
        self._tts_cmd: list[str] = cfg["output"]["tts_command"]
        self._worker: _SpeakWorker | _StreamingTTSWorker | None = None
        self.enabled: bool = cfg["output"]["tts_enabled"]

    def _duck(self) -> None:
        try:
            subprocess.run([str(_SCRIPTS / "giselo-audio-duck")],
                           capture_output=True, timeout=3)
        except Exception:
            pass

    def _unduck(self) -> None:
        try:
            subprocess.Popen([str(_SCRIPTS / "giselo-audio-unduck")],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _reload_config(self) -> None:
        try:
            import yaml
            _p = pathlib.Path(__file__).parents[2] / "config.yaml"
            _cfg = yaml.safe_load(_p.read_text(encoding="utf-8"))
            _out = _cfg["output"]
            self.enabled = _out["tts_enabled"]
            if _out.get("tts_command"):
                self._tts_cmd = _out["tts_command"]
            _el = _cfg.get("elevenlabs", {})
            self._handler.el_enabled  = _el.get("enabled", False)
            self._handler.el_api_key  = _el.get("api_key", "")
            self._handler.el_voice_id = _el.get("voice_id", "")
            self._handler.el_model_id = _el.get("model_id", "eleven_multilingual_v2")
        except Exception:
            pass

    def speak(self, text: str) -> None:
        """Blocking speak — full text at once (fallback / non-streaming path)."""
        self._reload_config()
        if not self.enabled or not text.strip():
            return
        self.stop()
        self._duck()
        self._worker = _SpeakWorker(self._handler, text, self)
        self._worker.finished.connect(self.finished)
        self._worker.error.connect(self.error)
        # Ensure cleanup on both success and failure
        for sig in (self._worker.finished, self._worker.error):
            sig.connect(self._cleanup)
            sig.connect(self._unduck)
        self._worker.start()
        self.started.emit()

    def begin_stream(self, first_sentence: str) -> None:
        """Start streaming TTS. Call stream_sentence() for subsequent sentences, end_stream() when done."""
        self._reload_config()
        if not self.enabled or not first_sentence.strip():
            return
        self.stop()
        self._duck()
        self._worker = _StreamingTTSWorker(self._handler, self._tts_cmd, self)
        self._worker.finished.connect(self.finished)
        self._worker.error.connect(self.error)
        # Ensure cleanup on both success and failure
        for sig in (self._worker.finished, self._worker.error):
            sig.connect(self._cleanup)
            sig.connect(self._unduck)
        self._worker.enqueue(first_sentence)
        self._worker.start()
        self.started.emit()

    def stream_sentence(self, sentence: str) -> None:
        """Add a sentence to the active streaming session."""
        if not self.enabled or not sentence.strip():
            return
        if isinstance(self._worker, _StreamingTTSWorker) and self._worker.isRunning():
            self._worker.enqueue(sentence)
        else:
            log.warning("stream_sentence: worker not running, sentence dropped: %r", sentence[:60])

    def end_stream(self) -> None:
        """Signal end of stream — worker flushes remaining audio and finishes."""
        if isinstance(self._worker, _StreamingTTSWorker) and self._worker.isRunning():
            self._worker.finish()

    def stop(self) -> None:
        self._handler.stop_tts()
        if self._worker:
            if isinstance(self._worker, _StreamingTTSWorker):
                self._worker.stop()
            if self._worker.isRunning():
                self._worker.wait(500)
        self._unduck()

    def _cleanup(self) -> None:
        self._worker = None
