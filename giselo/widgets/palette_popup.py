from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor

SWATCHES = [
    ("#88c93a", "Lima"),
    ("#3a9ee0", "Cian"),
    ("#e07a3a", "Naranja"),
    ("#cc4040", "Rojo"),
    ("#9b59b6", "Morado"),
    ("#e03a8c", "Rosa"),
]


class PalettePopup(QWidget):
    accent_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("palette-popup")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet("""
            QWidget#palette-popup {
                background: #0f1a2e;
                border: 1px solid rgba(93,107,133,0.5);
                border-radius: 8px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        title = QLabel("ACENTO")
        title.setStyleSheet(
            "color: rgba(136,150,175,0.7); font-size: 9px;"
            "font-family: 'JetBrains Mono', monospace; letter-spacing: 2px;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(6)

        for hex_color, label in SWATCHES:
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setToolTip(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {hex_color};
                    border-radius: 14px;
                    border: 2px solid transparent;
                }}
                QPushButton:hover {{
                    border: 2px solid white;
                }}
                QPushButton:pressed {{
                    border: 2px solid rgba(255,255,255,0.5);
                }}
            """)
            btn.clicked.connect(lambda _, c=hex_color: self._pick(c))
            row.addWidget(btn)

        root.addLayout(row)

    def _pick(self, color: str) -> None:
        self.accent_selected.emit(color)
        self.hide()

    def show_at(self, global_pos: QPoint) -> None:
        self.adjustSize()
        w, h = self.width(), self.height()
        self.move(global_pos.x() - w // 2, global_pos.y() - h - 8)
        self.show()
        self.raise_()
