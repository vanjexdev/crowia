#!/usr/bin/env python3
"""
giselo_app.py — Orquestador nueva UI PyQt6 (cockpit unificado).

Uso:
    python giselo_app.py

No reemplaza crowia.py — ambos coexisten.
La nueva UI se conectará al backend de crowia/ en Phase C.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from giselo.app.window import MainWindow

_ICON = os.path.join(os.path.dirname(__file__), "giselo", "assets", "icon.png")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Giselo")
    if os.path.exists(_ICON):
        app.setWindowIcon(QIcon(_ICON))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
