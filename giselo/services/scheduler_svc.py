import logging
import pathlib

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

_PENDING_FILE = pathlib.Path("/tmp/crowia/pending_reminder")
_POLL_MS = 5000

log = logging.getLogger(__name__)


class SchedulerService(QObject):
    """Polls /tmp/crowia/pending_reminder for messages written by giselo-remind-fire."""

    reminder_due = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(_POLL_MS)

    def _poll(self) -> None:
        if not _PENDING_FILE.exists():
            return
        try:
            text = _PENDING_FILE.read_text(encoding="utf-8").strip()
            _PENDING_FILE.unlink(missing_ok=True)
        except Exception as e:
            log.warning("scheduler_svc poll error: %s", e)
            return
        for line in text.splitlines():
            msg = line.strip()
            if msg:
                log.info("Reminder due: %r", msg)
                self.reminder_due.emit(msg)
