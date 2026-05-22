from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QPlainTextEdit, QPushButton, QLabel, QSizePolicy,
                              QFileDialog)
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self._check_at_trigger)
        self._at_pos: int = -1  # position of last @ that triggered picker

    def keyPressEvent(self, e: QKeyEvent) -> None:
        is_enter = e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        shift    = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        if is_enter and not shift:
            self.submitted.emit()
        else:
            super().keyPressEvent(e)

    def _check_at_trigger(self) -> None:
        text = self.toPlainText()
        cursor = self.textCursor()
        pos = cursor.position()
        if pos < 1 or text[pos - 1] != "@":
            return
        # Only trigger if @ is at start or preceded by whitespace
        if pos >= 2 and text[pos - 2] not in (" ", "\t", "\n"):
            return
        # Avoid re-triggering for same position
        if pos == self._at_pos:
            return
        self._at_pos = pos
        self._open_picker(pos)

    def _open_picker(self, at_pos: int) -> None:
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QCursor
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #0f1a2e; color: #cfd6e6;
                    border: 1px solid rgba(93,107,133,0.5);
                    font-family: 'JetBrains Mono', monospace; font-size: 10px; }
            QMenu::item { padding: 5px 14px; }
            QMenu::item:selected { background: rgba(136,201,58,0.15); color: #88c93a; }
        """)
        act_file   = menu.addAction("📄  Adjuntar archivo")
        act_folder = menu.addAction("📁  Adjuntar carpeta")
        act_screen = menu.addAction("📷  Capturar pantalla")
        chosen = menu.exec(QCursor.pos())
        self._at_pos = -1
        if chosen == act_file:
            path, _ = QFileDialog.getOpenFileName(self, "Adjuntar archivo")
            if path:
                self._insert_path(at_pos, path)
        elif chosen == act_folder:
            path = QFileDialog.getExistingDirectory(self, "Adjuntar carpeta")
            if path:
                self._insert_path(at_pos, path)
        elif chosen == act_screen:
            try:
                import sys, os
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
                from crowia.screen import take_screenshot
                p = take_screenshot()
                if p:
                    self._insert_path(at_pos, str(p))
            except Exception as e:
                self._insert_path(at_pos, f"[screenshot error: {e}]")

    def _insert_path(self, at_pos: int, path: str) -> None:
        doc = self.toPlainText()
        new_text = doc[: at_pos - 1] + path + doc[at_pos:]
        self.setPlainText(new_text)
        cursor = self.textCursor()
        cursor.setPosition(at_pos - 1 + len(path))
        self.setTextCursor(cursor)
