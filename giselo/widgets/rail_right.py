from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt


ITEMS = [
    ("◉", "voz"),
    ("◐", "camara"),
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

        self._buttons: dict[str, QPushButton] = {}
        for glyph, name in ITEMS:
            btn = QPushButton(glyph)
            btn.setProperty("railBtn", True)
            btn.setToolTip(name.capitalize())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, n=name: self.action_triggered.emit(n))
            layout.addWidget(btn)
            self._buttons[name] = btn

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def set_active(self, name: str | None) -> None:
        for n, btn in self._buttons.items():
            active = (n == name)
            btn.setProperty("railActive", active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
