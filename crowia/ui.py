import math
import pathlib
import threading

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox,
    QLabel, QTextBrowser, QVBoxLayout, QWidget,
)

from . import prefs as prefs_mod

IMAGES_DIR = pathlib.Path(__file__).parent.parent / "images"

STATE_IMAGE = {
    "idle":       "normal.png",
    "recording":  "open.png",
    "processing": "normal.png",
    "done":       "like.png",
}

CROW_SIZE = 360


class _Signals(QObject):
    state    = pyqtSignal(str)
    response = pyqtSignal(str)


class AudioBars(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(CROW_SIZE, 40)
        self._heights = [0.2] * 5
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._active = False

    def start(self):
        self._active = True
        self._timer.start(50)

    def stop(self):
        self._active = False
        self._timer.stop()
        self._heights = [0.2] * 5
        self.update()

    def _tick(self):
        self._phase += 0.3
        for i in range(5):
            self._heights[i] = 0.3 + 0.7 * abs(math.sin(self._phase + i * 0.8))
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bar_w = self.width() // (5 * 2 - 1)
        gap = bar_w
        p.setBrush(QColor(100, 200, 255, 220))
        p.setPen(Qt.PenStyle.NoPen)
        for i, h in enumerate(self._heights):
            bar_h = int(self.height() * h)
            x = i * (bar_w + gap) + gap // 2
            y = self.height() - bar_h
            p.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)


class PrefsDialog(QDialog):
    def __init__(self, prefs: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Giselo — Preferencias")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(300)
        self._prefs = dict(prefs)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self._cb_text = QCheckBox("Mostrar respuesta en texto")
        self._cb_text.setChecked(prefs.get("show_response_text", True))
        layout.addWidget(self._cb_text)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_prefs(self) -> dict:
        return {**self._prefs, "show_response_text": self._cb_text.isChecked()}


class CrowiaOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self._prefs = prefs_mod.load()

        self.setWindowTitle("Giselo")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._pixmaps: dict[str, QPixmap] = {}
        for state, fname in STATE_IMAGE.items():
            path = IMAGES_DIR / fname
            if path.exists():
                px = QPixmap(str(path))
                self._pixmaps[state] = px.scaledToWidth(
                    CROW_SIZE, Qt.TransformationMode.SmoothTransformation
                )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self._crow = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self._crow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._crow)

        self._backend_label = QLabel("Claude", alignment=Qt.AlignmentFlag.AlignCenter)
        self._backend_label.setStyleSheet(
            "color: rgba(180,220,255,200); font-size: 13px; font-weight: bold; letter-spacing: 2px;"
        )
        self._backend_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._backend_label)

        self._bars = AudioBars()
        self._bars.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._bars)

        self._response_box = QTextBrowser()
        self._response_box.setFont(QFont("Sans", 10))
        self._response_box.setMaximumHeight(180)
        self._response_box.setMinimumWidth(CROW_SIZE)
        self._response_box.setOpenExternalLinks(False)
        self._response_box.setStyleSheet(
            "QTextBrowser {"
            "  background: rgba(10, 10, 20, 180);"
            "  color: rgba(220, 235, 255, 230);"
            "  border-radius: 8px;"
            "  padding: 8px;"
            "  border: 1px solid rgba(100, 150, 255, 80);"
            "}"
        )
        layout.addWidget(self._response_box)

        self._signals = _Signals()
        self._signals.state.connect(self._apply_state)
        self._signals.response.connect(self._apply_response)

        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self._set_image("idle")
        self._apply_prefs(save=False)
        self.adjustSize()
        self._move_bottom_right()

    # ── public thread-safe API ────────────────────────────────────────────────

    def notify(self, state: str):
        self._signals.state.emit(state)

    def set_backend(self, name: str):
        self._signals.state.emit(f"backend:{name}")

    def set_response(self, text: str):
        self._signals.response.emit(text)

    # ── slots (main thread) ───────────────────────────────────────────────────

    def _apply_state(self, state: str):
        if state.startswith("backend:"):
            self._backend_label.setText(state[8:].upper())
            return
        self._set_image(state)
        if state in ("recording", "processing"):
            self._bars.start()
        else:
            self._bars.stop()
        if state == "done":
            QTimer.singleShot(3000, lambda: self._apply_state("idle"))
        self.show()

    def _apply_response(self, text: str):
        self._response_box.setPlainText(text)
        if self._prefs.get("show_response_text", True) and text:
            self._response_box.show()
            self.adjustSize()

    def _apply_prefs(self, save: bool = True):
        show = self._prefs.get("show_response_text", True)
        if show and self._response_box.toPlainText():
            self._response_box.show()
        else:
            self._response_box.hide()
        if save:
            prefs_mod.save(self._prefs)
        self.adjustSize()

    def _set_image(self, state: str):
        px = self._pixmaps.get(state, self._pixmaps.get("idle"))
        if px:
            self._crow.setPixmap(px)

    def _move_bottom_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(screen.width() - self.width() - 24, screen.height() - self.height() - 48)

    # ── mouse / keyboard ──────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, _event):
        self.hide()

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)

        show_text = self._prefs.get("show_response_text", True)
        toggle_label = "Ocultar texto de respuesta" if show_text else "Mostrar texto de respuesta"
        menu.addAction(toggle_label, self._toggle_response_text)

        menu.addAction("Preferencias…", self._open_prefs_dialog)
        menu.addSeparator()
        menu.addAction("Ocultar", self.hide)
        menu.addSeparator()
        menu.addAction("Salir", QApplication.quit)
        menu.exec(event.globalPos())

    def _toggle_response_text(self):
        self._prefs["show_response_text"] = not self._prefs.get("show_response_text", True)
        self._apply_prefs()

    def _open_prefs_dialog(self):
        dlg = PrefsDialog(self._prefs, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._prefs = dlg.result_prefs()
            self._apply_prefs()
