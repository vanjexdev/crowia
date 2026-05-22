from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt


ITEMS = [
    ("◆", "memoria"),
    ("⊟", "historial"),
    ("◑", "sistema"),
    ("⊞", "cola"),
    ("◔", "notif"),
]


class RailLeft(QWidget):
    drawer_toggled = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rail-left")
        self.setFixedWidth(44)
        self._buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for glyph, name in ITEMS:
            btn = QPushButton(glyph)
            btn.setProperty("railBtn", True)
            btn.setToolTip(name.capitalize())
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, n=name: self.drawer_toggled.emit(n))
            self._buttons[name] = btn
            layout.addWidget(btn)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        config_btn = QPushButton("⚙")
        config_btn.setProperty("railBtn", True)
        config_btn.setToolTip("Configuración")
        config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(config_btn)

    def set_active(self, name: str | None) -> None:
        for n, btn in self._buttons.items():
            btn.setProperty("railActive", n == name)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
