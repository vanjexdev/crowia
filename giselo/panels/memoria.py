from PyQt6.QtWidgets import QLabel, QVBoxLayout
from giselo.app.theme import LIME, MUTE, INK


def build(layout: QVBoxLayout) -> None:
    for title, sub in [
        ("Projecto Giselo UI", "42 entradas · activo"),
        ("Preferencias",       "idioma, acceso"),
        ("Sesión actual",      "contexto: 0 tokens"),
        ("Workspace",          "–"),
        ("Secretos",           "vault · 0 entradas"),
    ]:
        t = QLabel(title)
        t.setStyleSheet(f"color: {INK}; font-size: 11px; font-weight: 700;")
        s = QLabel(sub)
        s.setStyleSheet(f"color: {MUTE}; font-size: 10px;")
        layout.insertWidget(layout.count() - 1, t)
        layout.insertWidget(layout.count() - 1, s)
