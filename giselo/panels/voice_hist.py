import json
import pathlib
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QFrame, QSizePolicy
from PyQt6.QtCore import Qt
from giselo.app.theme import LIME, MUTE, INK

_HISTORY_FILE = pathlib.Path.home() / ".config" / "crowia" / "voice_history.json"


def append(text: str, instance: str) -> None:
    """Save a voice transcription entry. Called from window.py."""
    from datetime import datetime
    try:
        entries = json.loads(_HISTORY_FILE.read_text(encoding="utf-8")) if _HISTORY_FILE.exists() else []
    except Exception:
        entries = []
    entries.append({
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "text": text,
        "instance": instance,
    })
    entries = entries[-200:]
    try:
        _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _HISTORY_FILE.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def build(layout: QVBoxLayout) -> None:
    try:
        entries = json.loads(_HISTORY_FILE.read_text(encoding="utf-8")) if _HISTORY_FILE.exists() else []
    except Exception:
        entries = []

    if not entries:
        lbl = QLabel("Sin historial de voz aún")
        lbl.setStyleSheet(f"color: {MUTE}; font-size: 11px;")
        layout.addWidget(lbl)
        return

    for entry in reversed(entries[-40:]):
        ts = entry.get("ts", "")
        text = entry.get("text", "")
        instance = entry.get("instance", "")

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: rgba(15,26,46,0.6);
                border-left: 2px solid {LIME};
                border-radius: 4px;
                margin-bottom: 2px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 5, 8, 5)
        card_layout.setSpacing(3)

        header = QLabel(f"mic  {ts}  |  {instance}" if instance else f"mic  {ts}")
        header.setStyleSheet(
            f"color: {LIME}; font-size: 10px; font-weight: 700;"
            f"font-family: 'JetBrains Mono', monospace;"
        )
        card_layout.addWidget(header)

        body = QLabel(text)
        body.setStyleSheet(f"color: {INK}; font-size: 11px;")
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        card_layout.addWidget(body)

        layout.insertWidget(layout.count() - 1, card)
