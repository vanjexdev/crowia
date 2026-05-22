from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, pyqtSignal, Qt, QSize
from giselo.app.theme import ACCENT_DEFAULT


DRAWER_WIDTH = 260


class Drawer(QWidget):
    closed = pyqtSignal()

    def __init__(self, title: str, color: str = ACCENT_DEFAULT, parent=None):
        super().__init__(parent)
        self.setObjectName("drawer")
        self.setFixedWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._color = color
        self._open = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("drawer-header")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 6, 8, 6)

        self._title_lbl = QLabel(f"▾ {title.upper()}")
        self._title_lbl.setObjectName("drawer-title")
        h_layout.addWidget(self._title_lbl)
        h_layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setObjectName("drawer-close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close_drawer)
        h_layout.addWidget(close_btn)

        root.addWidget(header)

        # Scroll content
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(12, 8, 12, 8)
        self._content_layout.setSpacing(6)
        self._content_layout.addStretch()
        self._scroll.setWidget(self._content)
        root.addWidget(self._scroll)

        # Animation
        self._anim = QPropertyAnimation(self, b"minimumWidth")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_title(self, title: str) -> None:
        self._title_lbl.setText(f"▾ {title.upper()}")

    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def open_drawer(self) -> None:
        if self._open:
            return
        self._open = True
        self.show()
        self._anim.stop()
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(DRAWER_WIDTH)
        self._anim.start()

    def close_drawer(self) -> None:
        if not self._open:
            return
        self._open = False
        self._anim.stop()
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(0)
        self._anim.finished.connect(self._on_close_done)
        self._anim.start()
        self.closed.emit()

    def _on_close_done(self) -> None:
        if not self._open:
            self.hide()
        try:
            self._anim.finished.disconnect(self._on_close_done)
        except RuntimeError:
            pass

    def scroll_to_bottom(self) -> None:
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def is_open(self) -> bool:
        return self._open
