from PyQt6.QtWidgets import QLabel, QVBoxLayout
from giselo.app.theme import MUTE


def build(layout: QVBoxLayout) -> None:
    lbl = QLabel("Sin notificaciones")
    lbl.setStyleSheet(f"color: {MUTE}; font-size: 11px;")
    layout.insertWidget(layout.count() - 1, lbl)
