from PyQt6.QtWidgets import QLabel, QVBoxLayout
from giselo.app.theme import MUTE, LIME, INK
from giselo.app.state import state


def build(layout: QVBoxLayout) -> None:
    if state.giselo_state in ("thinking", "speaking"):
        lbl = QLabel("● procesando mensaje...")
        lbl.setStyleSheet(f"color: {LIME}; font-size: 11px;")
    else:
        lbl = QLabel("Cola vacía")
        lbl.setStyleSheet(f"color: {MUTE}; font-size: 11px;")
    layout.insertWidget(layout.count() - 1, lbl)

    backend_lbl = QLabel(f"backend: {state.active_instance}")
    backend_lbl.setStyleSheet(
        f"color: {MUTE}; font-size: 10px; font-family: 'JetBrains Mono', monospace;"
    )
    layout.insertWidget(layout.count() - 1, backend_lbl)
