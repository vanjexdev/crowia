from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from giselo.app.theme import LIME, MUTE


class StatusBar(QWidget):
    def __init__(self, version: str = "v0.5.0", build: str = "phase-a", parent=None):
        super().__init__(parent)
        self.setObjectName("status-bar")
        self.setFixedHeight(22)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(0)

        self._online    = self._lbl("● online", online=True)
        self._instance  = self._lbl("claude")
        self._mem       = self._lbl("mem 0k")
        self._cam_lbl   = self._lbl("○ cam")
        self._voz_lbl   = self._lbl("voz off")

        for w in (self._online, self._sep(), self._instance, self._sep(),
                  self._mem, self._sep(), self._cam_lbl, self._sep(), self._voz_lbl):
            layout.addWidget(w)

        layout.addStretch()

        ver = self._lbl(f"{version} · build {build}")
        ver.setProperty("statusVersion", True)
        layout.addWidget(ver)

    def _lbl(self, text: str, online: bool = False) -> QLabel:
        lbl = QLabel(text)
        if online:
            lbl.setProperty("statusOnline", True)
        else:
            lbl.setProperty("statusItem", True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        return lbl

    def _sep(self) -> QLabel:
        s = QLabel("·")
        s.setProperty("statusItem", True)
        s.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        return s

    def set_instance(self, name: str) -> None:
        self._instance.setText(name)

    def set_mem(self, tokens: int) -> None:
        self._mem.setText(f"mem {tokens // 1000}k" if tokens >= 1000 else f"mem {tokens}")

    def set_camera(self, active: bool) -> None:
        self._cam_lbl.setText("● cam" if active else "○ cam")
        self._cam_lbl.setStyleSheet(f"color: {LIME};" if active else "")

    def set_voice(self, active: bool) -> None:
        self._voz_lbl.setText("voz on" if active else "voz off")
