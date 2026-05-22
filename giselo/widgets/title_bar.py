from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont


class TitleBar(QWidget):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.setObjectName("title-bar")
        self._main_window = window
        self.setFixedHeight(30)
        self._drag_pos: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)

        # Traffic lights
        self._btn_close = self._traffic("traffic-close")
        self._btn_min   = self._traffic("traffic-min")
        self._btn_max   = self._traffic("traffic-max")
        layout.addWidget(self._btn_close)
        layout.addWidget(self._btn_min)
        layout.addWidget(self._btn_max)
        layout.addSpacing(10)

        # Title
        lbl = QLabel("GISELO")
        lbl.setObjectName("title-label")
        layout.addWidget(lbl)

        # Size hint (hidden in MIN)
        self._hint = QLabel()
        self._hint.setObjectName("title-hint")
        layout.addWidget(self._hint)

        layout.addStretch()

        # Fullscreen hint
        hint_fs = QLabel("⌘F")
        hint_fs.setObjectName("title-hint")
        layout.addWidget(hint_fs)

        self._btn_close.clicked.connect(self._main_window.close)
        self._btn_min.clicked.connect(self._main_window.showMinimized)
        self._btn_max.clicked.connect(self._main_window.toggle_fullscreen)

    def _traffic(self, obj_name: str) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName(obj_name)
        btn.setFixedSize(10, 10)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def update_size_hint(self, w: int, h: int, visible: bool) -> None:
        self._hint.setText(f"· puente · {w}×{h}")
        self._hint.setVisible(visible)

    # ── Drag to move (frameless) ───────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._main_window.windowHandle()
            if handle:
                handle.startSystemMove()
            else:
                self._drag_pos = event.globalPosition().toPoint() - self._main_window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self._main_window.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
