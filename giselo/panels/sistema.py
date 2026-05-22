from PyQt6.QtWidgets import QLabel, QVBoxLayout
from giselo.app.theme import YELLOW, CYAN, MUTE, INK


def build(layout: QVBoxLayout) -> None:
    for metric in ("CPU", "RAM", "GPU", "NET ↓", "NET ↑"):
        lbl = QLabel(f"{metric}  –")
        lbl.setStyleSheet(f"color: {INK}; font-family: 'JetBrains Mono', monospace; font-size: 10px;")
        layout.insertWidget(layout.count() - 1, lbl)
