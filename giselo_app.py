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
from giselo.app.window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Giselo")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
