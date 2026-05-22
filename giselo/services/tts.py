import logging
from PyQt6.QtCore import QObject, QThread, pyqtSignal

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


class TTSService(QObject):
    started  = pyqtSignal()
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        from crowia.output import OutputHandler
        self._handler = OutputHandler(cfg)
        self._worker: _SpeakWorker | None = None
        self.enabled: bool = cfg["output"]["tts_enabled"]

    def speak(self, text: str) -> None:
        if not self.enabled or not text.strip():
            return
        self.stop()
        self._worker = _SpeakWorker(self._handler, text, self)
        self._worker.finished.connect(self.finished)
        self._worker.error.connect(self.error)
        self._worker.finished.connect(self._cleanup)
        self._worker.start()
        self.started.emit()

    def stop(self) -> None:
        self._handler.stop_tts()
        if self._worker and self._worker.isRunning():
            self._worker.wait(500)

    def _cleanup(self) -> None:
        self._worker = None
