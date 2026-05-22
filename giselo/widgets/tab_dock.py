from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal
from giselo.app.theme import LIME, CYAN, ORANGE, MUTE, INK


INSTANCE_META = {
    "opencode": {"color": LIME,   "shortcut": "⌃⇧1"},
    "claude":   {"color": CYAN,   "shortcut": "⌃`"},
    "codex":    {"color": ORANGE, "shortcut": "⌃⇧⌥1"},
}


class TabDock(QWidget):
    instance_changed     = pyqtSignal(str)
    instance_add_requested = pyqtSignal()

    def __init__(self, instances: list[str], active: str, parent=None):
        super().__init__(parent)
        self.setObjectName("tab-dock")
        self.setFixedHeight(44)
        self._buttons: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(2)

        for inst in instances:
            btn = self._make_tab(inst)
            self._buttons[inst] = btn
            layout.addWidget(btn)

        add_btn = QPushButton("+ instancia")
        add_btn.setProperty("tabAdd", True)
        add_btn.setFixedHeight(44)
        add_btn.setCursor(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.instance_add_requested)
        layout.addWidget(add_btn)
        layout.addStretch()

        self.set_active(active)

    def _make_tab(self, name: str) -> QPushButton:
        meta = INSTANCE_META.get(name, {"color": MUTE, "shortcut": ""})
        dot  = "●"
        btn  = QPushButton(f"{dot} {name}")
        btn.setProperty("tabButton", True)
        btn.setFixedHeight(44)
        btn.setCursor(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _, n=name: self.instance_changed.emit(n))
        return btn

    def add_instance(self, name: str) -> None:
        btn = self._make_tab(name)
        self._buttons[name] = btn
        layout = self.layout()
        layout.insertWidget(layout.count() - 2, btn)
        self.set_active(name)

    def set_active(self, name: str) -> None:
        for inst, btn in self._buttons.items():
            btn.setProperty("tabActive", inst == name)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
