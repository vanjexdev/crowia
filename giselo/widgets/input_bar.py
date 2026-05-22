from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QPlainTextEdit, QPushButton, QLabel, QSizePolicy)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeyEvent
from giselo.app.theme import MUTE


class InputBar(QWidget):
    message_submitted = pyqtSignal(str)
    camera_toggled    = pyqtSignal()
    voice_toggled     = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("input-bar")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 6, 10, 6)
        root.setSpacing(4)

        # Text field
        self._field = _InputField(self)
        self._field.setObjectName("input-field")
        self._field.setPlaceholderText("› escribe o habla...  (@ adjuntar · / comandos)")
        self._field.setFixedHeight(52)
        self._field.submitted.connect(self._on_submit)
        root.addWidget(self._field)

        # Controls row
        ctrl = QHBoxLayout()
        ctrl.setContentsMargins(0, 0, 0, 0)
        ctrl.setSpacing(6)

        hint = QLabel("⌘K palette")
        hint.setStyleSheet(f"color: {MUTE}; font-family: 'JetBrains Mono', monospace; font-size: 9px;")
        ctrl.addWidget(hint)

        sep = QLabel("|")
        sep.setStyleSheet(f"color: {MUTE}; font-size: 10px;")
        ctrl.addWidget(sep)

        ctrl.addStretch()

        self._btn_cam = QPushButton("◐ cam")
        self._btn_cam.setProperty("inputBtnCam", True)
        self._btn_cam.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cam.clicked.connect(self.camera_toggled)
        ctrl.addWidget(self._btn_cam)

        self._btn_voz = QPushButton("◉ voz")
        self._btn_voz.setProperty("inputBtnVoz", True)
        self._btn_voz.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_voz.clicked.connect(self.voice_toggled)
        ctrl.addWidget(self._btn_voz)

        self._btn_send = QPushButton("enviar ↵")
        self._btn_send.setProperty("inputBtnAccent", True)
        self._btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_send.clicked.connect(self._on_submit)
        ctrl.addWidget(self._btn_send)

        root.addLayout(ctrl)

    def text(self) -> str:
        return self._field.toPlainText().strip()

    def clear(self) -> None:
        self._field.clear()

    def _on_submit(self) -> None:
        text = self.text()
        if text:
            self.message_submitted.emit(text)
            self.clear()


class _InputField(QPlainTextEdit):
    submitted = pyqtSignal()

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
           e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.submitted.emit()
        else:
            super().keyPressEvent(e)
