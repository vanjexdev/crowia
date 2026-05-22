from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt


ITEMS = [
    ("◉", "voz"),
    ("◐", "camara"),
    ("⊡", "expandir"),
    ("✎", "editor"),
]


class RailRight(QWidget):
    action_triggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rail-right")
        self.setFixedWidth(44)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for glyph, name in ITEMS:
            btn = QPushButton(glyph)
            btn.setProperty("railBtn", True)
            btn.setToolTip(name.capitalize())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, n=name: self.action_triggered.emit(n))
            layout.addWidget(btn)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def set_active(self, name: str | None) -> None:
        pass
