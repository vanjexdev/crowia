from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QSizePolicy
from PyQt6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPainter, QRadialGradient

from giselo.app.theme import LIME, BG, INK


class _Vignette(QWidget):
    """Transparent overlay with radial gradient — dark edges, clear center."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        grad = QRadialGradient(cx, cy, max(w, h) * 0.55)
        grad.setColorAt(0.45, QColor(10, 16, 32, 0))
        grad.setColorAt(0.78, QColor(10, 16, 32, 90))
        grad.setColorAt(1.00, QColor(10, 16, 32, 230))
        p.fillRect(self.rect(), grad)
        p.end()

PIP_W_NORMAL = 220
PIP_H_NORMAL = 135
PIP_W_MIN    = 170
PIP_H_MIN    = 110


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

        self._session  : QMediaCaptureSession | None = None
        self._camera   : QCamera | None = None
        self._active   = False

        self._build_ui()
        self._anim = QPropertyAnimation(self, b"maximumHeight")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.hide()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video widget fills most of the PIP
        self._video = QVideoWidget(self)
        self._video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._video)

        # Badge overlay — LIVE top-left
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

        # Resolution badge — bottom-right
        self._res_badge = QLabel("cam-0 · –", self)
        self._res_badge.setStyleSheet(f"""
            background: rgba(0,0,0,180);
            color: {LIME};
            font-family: 'JetBrains Mono', monospace;
            font-size: 8px;
            padding: 2px 5px;
            border-radius: 3px;
        """)

        # Vignette overlay (circular feathered edge)
        self._vignette = _Vignette(self)
        self._vignette.hide()

        # Close button — top-right
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

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._close_btn.move(w - 22, 4)
        self._res_badge.adjustSize()
        self._res_badge.move(w - self._res_badge.width() - 6,
                              h - self._res_badge.height() - 6)
        self._vignette.setGeometry(0, 0, w, h)
        self._vignette.raise_()

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, compact: bool = False, cam_index: int = 0) -> None:
        if self._active:
            return

        cameras = QMediaDevices.videoInputs()
        if not cameras:
            return

        idx      = min(cam_index, len(cameras) - 1)
        cam_info = cameras[idx]
        res_text = f"cam-{idx} · {cam_info.description()[:14]}"
        self._res_badge.setText(res_text)

        self._camera  = QCamera(cam_info)
        self._session = QMediaCaptureSession()
        self._session.setCamera(self._camera)
        self._session.setVideoOutput(self._video)

        w = PIP_W_MIN if compact else PIP_W_NORMAL
        h = PIP_H_MIN if compact else PIP_H_NORMAL
        self.setFixedSize(w, h)

        self._camera.errorOccurred.connect(self._on_cam_error)
        self._camera.start()
        self._active = True
        self.show()

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self._vignette.hide()
        self.setGraphicsEffect(None)
        if self._camera:
            self._camera.stop()
            self._camera = None
        self._session = None
        self.hide()
        self.closed.emit()

    def expand(self, w: int, h: int, accent: str = "#88c93a") -> None:
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self.resize(w, h)
        self.setGraphicsEffect(None)
        self._vignette.setGeometry(0, 0, w, h)
        self._vignette.show()
        self._vignette.raise_()

    def set_compact(self, compact: bool) -> None:
        if not self._active:
            return
        w = PIP_W_MIN if compact else PIP_W_NORMAL
        h = PIP_H_MIN if compact else PIP_H_NORMAL
        self.setFixedSize(w, h)
        self.setGraphicsEffect(None)

    @property
    def active(self) -> bool:
        return self._active

    # ── Error ─────────────────────────────────────────────────────────────────

    def _on_cam_error(self, error, msg: str) -> None:
        self._live_badge.setText("● ERROR")
        self._live_badge.setStyleSheet(
            self._live_badge.styleSheet().replace(LIME, "#cc4040")
        )
