import math
import pathlib
import threading

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QPixmap, QPainter, QColor, QKeySequence
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout

IMAGES_DIR = pathlib.Path(__file__).parent.parent / "images"

STATE_IMAGE = {
    "idle":       "normal.png",
    "recording":  "open.png",
    "processing": "normal.png",
    "done":       "like.png",
}

CROW_SIZE = 360  # px width


class _Signals(QObject):
    state = pyqtSignal(str)


class AudioBars(QWidget):
    """Animated sound bars — 5 bars that pulse while recording."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(CROW_SIZE, 40)
        self._heights = [0.2] * 5
        self._targets = [0.2] * 5
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
        color = QColor(100, 200, 255, 220)
        p.setBrush(color)
        p.setPen(Qt.PenStyle.NoPen)
        for i, h in enumerate(self._heights):
            bar_h = int(self.height() * h)
            x = i * (bar_w + gap) + gap // 2
            y = self.height() - bar_h
            p.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)


class CrowiaOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pepito")
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
        layout.addWidget(self._crow)

        self._bars = AudioBars()
        layout.addWidget(self._bars)

        self._signals = _Signals()
        self._signals.state.connect(self._apply_state)

        self._drag_pos = None
        # Hijos transparentes a mouse → todos los eventos van al parent
        self._crow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._bars.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        self._set_image("idle")
        self.adjustSize()
        self._move_bottom_right()

    def notify(self, state: str):
        """Thread-safe state update."""
        self._signals.state.emit(state)

    def _apply_state(self, state: str):
        self._set_image(state)
        if state in ("recording", "processing"):
            self._bars.start()
        else:
            self._bars.stop()
        if state == "done":
            QTimer.singleShot(3000, lambda: self._apply_state("idle"))
        self.show()

    def _set_image(self, state: str):
        px = self._pixmaps.get(state, self._pixmaps.get("idle"))
        if px:
            self._crow.setPixmap(px)

    def _move_bottom_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(screen.width() - self.width() - 24, screen.height() - self.height() - 48)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Wayland requiere startSystemMove() — el compositor maneja el drag
            self.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, _event):
        self.hide()

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.addAction("Ocultar", self.hide)
        menu.addSeparator()
        menu.addAction("Salir", QApplication.quit)
        menu.exec(event.globalPos())
