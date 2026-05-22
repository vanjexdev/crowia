from PyQt6.QtWidgets import QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from giselo.app.theme import MUTE, LIME, CYAN, ORANGE, RED, INK
from datetime import datetime

_log: list[tuple[str, str, str]] = []  # (timestamp, level, message)


def push(message: str, level: str = "info") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    _log.append((ts, level, message))
    if len(_log) > 50:
        _log.pop(0)


def build(layout: QVBoxLayout) -> None:
    if not _log:
        lbl = QLabel("Sin notificaciones")
        lbl.setStyleSheet(f"color: {MUTE}; font-size: 11px;")
        layout.insertWidget(layout.count() - 1, lbl)
        return

    COLOR_MAP = {"info": CYAN, "ok": LIME, "warn": ORANGE, "error": RED}

    for ts, level, msg in reversed(_log[-20:]):
        color = COLOR_MAP.get(level, MUTE)
        lbl = QLabel(f"<span style='color:{MUTE}'>{ts}</span> "
                     f"<span style='color:{color}'>{msg}</span>")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        layout.insertWidget(layout.count() - 1, lbl)
