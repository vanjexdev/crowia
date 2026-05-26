#!/usr/bin/env python3
"""
giselo_app.py — Orquestador nueva UI PyQt6 (cockpit unificado).
"""
import sys
import os
import argparse
import logging
import pathlib

# Ensure we can import from project root
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from giselo.app.window import MainWindow

_ICON = os.path.join(os.path.dirname(__file__), "giselo", "assets", "icon.png")


def setup_logging(debug: bool = False):
    level = logging.DEBUG if debug else logging.INFO
    log_dir = pathlib.Path("/tmp/crowia")
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "giselo.log"),
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="Giselo — new cockpit UI")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose (debug) logging")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--always-on", action="store_true", help="Start with Always-On mode enabled")
    args = parser.parse_args()

    setup_logging(args.verbose or args.debug)

    app = QApplication(sys.argv)
    app.setApplicationName("Giselo")
    if os.path.exists(_ICON):
        app.setWindowIcon(QIcon(_ICON))

    window = MainWindow()

    if args.always_on:
        # We can't call toggle_always_on() directly if it relies on UI state
        # but window._always_on = True + _resume_always_on() should work.
        # However, toggle_always_on() also updates the UI button state.
        window.toggle_always_on()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
