import logging
import sys
import os

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from crowia.assistant import Assistant
from crowia.config import load as load_config

log = logging.getLogger(__name__)


class _AskWorker(QObject):
    chunk    = pyqtSignal(str)
    done     = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, assistant: Assistant, text: str, history: list[dict],
                 image_path: str | None = None):
        super().__init__()
        self._assistant  = assistant
        self._text       = text
        self._history    = history
        self._image_path = image_path
        self._cancelled  = False

    def cancel(self) -> None:
        self._cancelled = True
        self._assistant.cancel()

    @pyqtSlot()
    def run(self) -> None:
        import pathlib
        img = pathlib.Path(self._image_path) if self._image_path else None
        try:
            full = self._assistant.ask(
                text=self._text,
                history=self._history,
                image_path=img,
                on_chunk=lambda c: self.chunk.emit(c) if not self._cancelled else None,
            )
            if not self._cancelled:
                self.done.emit(full)
            else:
                self.error.emit("cancelado")
        except Exception as exc:
            log.exception("Ask worker error: %s", exc)
            self.error.emit(str(exc))


class InstanceService(QObject):
    """Bridge between the UI and crowia's Assistant backend."""

    chunk_received    = pyqtSignal(str)   # streaming chunk
    response_complete = pyqtSignal(str)   # full response text
    response_error    = pyqtSignal(str)   # error message
    busy_changed      = pyqtSignal(bool)  # True=processing, False=idle

    def __init__(self, instance_name: str = "", parent=None):
        super().__init__(parent)
        self._cfg = load_config()
        inst_cfgs = self._cfg.get("instances", {}).get("config", {})
        self._instance_cfg = inst_cfgs.get(instance_name, {}) or {}
        self._assistant = Assistant(self._cfg, instance_config=self._instance_cfg)
        self._thread: QThread | None  = None
        self._worker: _AskWorker | None = None
        self._busy = False
        self._inject_backend_name(self._cfg.get("backend", "claude"))

    # ── Public ────────────────────────────────────────────────────────────────

    @property
    def busy(self) -> bool:
        return self._busy

    @property
    def current_backend(self) -> str:
        return self._assistant.current_backend_name

    def switch_backend(self, name: str) -> str:
        result = self._assistant.switch_backend(name)
        self._inject_backend_name(name)
        return result

    def _inject_backend_name(self, name: str) -> None:
        import yaml, pathlib
        base = self._assistant._base_prompt
        persona_line = ""
        try:
            _cfg = yaml.safe_load(
                (pathlib.Path(__file__).parents[2] / "config.yaml").read_text(encoding="utf-8")
            )
            asst = _cfg.get("assistant", {})
            gender = asst.get("gender", "male")
            persona_name = asst.get("name_female" if gender == "female" else "name_male", "Giselo")
            base = base.replace("Giselo", persona_name)
            if gender == "female":
                persona_line = f" Actúa con personalidad femenina. Tu nombre es {persona_name}."
        except Exception:
            pass
        self._assistant.system_prompt = (
            f"{base}\n\nEstás corriendo sobre el backend '{name}'.{persona_line}"
        )

    def ask(self, text: str, history: list[dict] | None = None,
            image_path: str | None = None) -> None:
        if self._busy:
            log.warning("Already processing — ignoring ask")
            return
        history = history or []

        self._busy = True
        self.busy_changed.emit(True)

        self._thread = QThread()
        self._worker = _AskWorker(self._assistant, text, history, image_path)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.chunk.connect(self.chunk_received)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)

        self._thread.start()

    def cancel(self) -> None:
        if not self._worker:
            return
        self._worker.cancel()
        # Fallback: if subprocess exits cleanly without raising, done/error won't fire
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(5000, self._force_cleanup)

    def _force_cleanup(self) -> None:
        if self._busy:
            self._cleanup()
            self.response_error.emit("cancelado")
            self.busy_changed.emit(False)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _on_done(self, full_response: str) -> None:
        self._cleanup()
        self.response_complete.emit(full_response)
        self.busy_changed.emit(False)

    def _on_error(self, msg: str) -> None:
        self._cleanup()
        self.response_error.emit(msg)
        self.busy_changed.emit(False)

    def _cleanup(self) -> None:
        self._busy = False
        if self._thread:
            self._thread.quit()
            self._thread.wait(3000)
        self._thread = None
        self._worker = None
