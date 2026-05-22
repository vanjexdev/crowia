from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QSizePolicy
from PyQt6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QColor, QPainter, QRadialGradient

from giselo.app.theme import LIME, BG, INK

PIP_MIN_W = 160
PIP_MIN_H = 100
_GRIP  = 18   # px corner area treated as resize grip
_CLOSE = 26   # px corner area treated as close-button zone (top-right)


class _ResizeHandle(QWidget):
    """Visible grip dots in bottom-right corner — transparent to mouse events."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(LIME)
        c.setAlphaF(0.75)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        for row, col in [(0, 2), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]:
            p.drawEllipse(col * 6, row * 6, 3, 3)
        p.end()


class CameraPip(QWidget):
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("camera-pip")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            #camera-pip {{
                background: #000;
                border: 1.5px solid {LIME};
                border-radius: 6px;
            }}
        """)

        self._session : QMediaCaptureSession | None = None
        self._camera  : QCamera | None = None
        self._active  = False

        self._dragging  = False
        self._drag_off  = QPoint()
        self._resizing  = False
        self._res_start = QPoint()
        self._res_orig  = QSize()

        self._build_ui()
        self.hide()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._video = QVideoWidget(self)
        self._video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._video)

        self._live_badge = QLabel("● LIVE", self)
        self._live_badge.setStyleSheet(f"""
            background: rgba(0,0,0,180);
            color: {LIME};
            font-family: 'JetBrains Mono', monospace;
            font-size: 9px;
            padding: 2px 5px;
            border-radius: 3px;
        """)
        self._live_badge.adjustSize()
        self._live_badge.move(6, 6)

        self._res_badge = QLabel("cam-0 · –", self)
        self._res_badge.setStyleSheet(f"""
            background: rgba(0,0,0,180);
            color: {LIME};
            font-family: 'JetBrains Mono', monospace;
            font-size: 8px;
            padding: 2px 5px;
            border-radius: 3px;
        """)

        self._close_btn = QPushButton("×", self)
        self._close_btn.setFixedSize(18, 18)
        self._close_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0,0,0,160);
                color: {LIME};
                border: 1px solid {LIME};
                border-radius: 3px;
                font-size: 12px;
                padding: 0;
            }}
            QPushButton:hover {{ background: rgba(136,201,58,0.25); }}
        """)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.stop)

        self._grip_handle = _ResizeHandle(self)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._close_btn.move(w - 22, 4)
        self._res_badge.adjustSize()
        self._res_badge.move(w - self._res_badge.width() - 6,
                              h - self._res_badge.height() - 6)
        self._grip_handle.move(w - 20, h - 20)
        self._grip_handle.raise_()

    # ── Mouse: drag + resize ──────────────────────────────────────────────────

    def _in_grip(self, pos: QPoint) -> bool:
        return pos.x() > self.width() - _GRIP and pos.y() > self.height() - _GRIP

    def _in_close_zone(self, pos: QPoint) -> bool:
        return pos.x() > self.width() - _CLOSE and pos.y() < _CLOSE

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            lp = event.position().toPoint()
            if self._in_grip(lp):
                self._resizing  = True
                self._res_start = event.globalPosition().toPoint()
                self._res_orig  = self.size()
            elif not self._in_close_zone(lp):
                self._dragging = True
                self._drag_off = lp
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        gp = event.globalPosition().toPoint()
        lp = event.position().toPoint()

        if self._resizing:
            delta = gp - self._res_start
            nw = max(PIP_MIN_W, self._res_orig.width()  + delta.x())
            nh = max(PIP_MIN_H, self._res_orig.height() + delta.y())
            parent = self.parentWidget()
            if parent:
                nw = min(nw, parent.width()  - self.x())
                nh = min(nh, parent.height() - self.y())
            self.resize(nw, nh)
        elif self._dragging:
            parent = self.parentWidget()
            if parent:
                tl = parent.mapFromGlobal(gp - self._drag_off)
                x  = max(0, min(tl.x(), parent.width()  - self.width()))
                y  = max(0, min(tl.y(), parent.height() - self.height()))
                self.move(x, y)
        else:
            if self._in_grip(lp):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif not self._in_close_zone(lp):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False
        self._resizing = False
        event.accept()

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, cam_index: int = 0) -> None:
        if self._active:
            return
        cameras = QMediaDevices.videoInputs()
        if not cameras:
            return
        idx      = min(cam_index, len(cameras) - 1)
        cam_info = cameras[idx]
        self._res_badge.setText(f"cam-{idx} · {cam_info.description()[:14]}")
        self._camera  = QCamera(cam_info)
        self._session = QMediaCaptureSession()
        self._session.setCamera(self._camera)
        self._session.setVideoOutput(self._video)
        self.setMinimumSize(PIP_MIN_W, PIP_MIN_H)
        self._camera.errorOccurred.connect(self._on_cam_error)
        self._camera.start()
        self._active = True
        self.show()

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        if self._camera:
            self._camera.stop()
            self._camera = None
        self._session = None
        self.hide()
        self.closed.emit()

    @property
    def active(self) -> bool:
        return self._active

    # ── Error ─────────────────────────────────────────────────────────────────

    def _on_cam_error(self, error, msg: str) -> None:
        self._live_badge.setText("● ERROR")
        self._live_badge.setStyleSheet(
            self._live_badge.styleSheet().replace(LIME, "#cc4040")
        )
