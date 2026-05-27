from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QPlainTextEdit, QPushButton, QLabel, QSizePolicy,
                              QFileDialog)
from PyQt6.QtCore import pyqtSignal, Qt, QUrl
from PyQt6.QtGui import QKeyEvent, QDragEnterEvent, QDragLeaveEvent, QDropEvent
from giselo.app.theme import MUTE


class InputBar(QWidget):
    message_submitted  = pyqtSignal(str, list)  # text, file_paths
    camera_toggled     = pyqtSignal()
    voice_toggled      = pyqtSignal()
    always_on_toggled  = pyqtSignal()
    drawer_requested   = pyqtSignal(str)   # emitted by compact menu button

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("input-bar")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._active_drawer: str | None = None
        self._always_on_active: bool = False
        self._attached_files: list[str] = []
        self.setAcceptDrops(True)

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

        # File chips row — hidden until files attached
        self._chips_row = QWidget()
        self._chips_layout = QHBoxLayout(self._chips_row)
        self._chips_layout.setContentsMargins(2, 0, 2, 0)
        self._chips_layout.setSpacing(6)
        self._chips_clear = QPushButton("✕ limpiar")
        self._chips_clear.setStyleSheet(
            f"color: {MUTE}; border: none; background: transparent;"
            "font-family: 'JetBrains Mono', monospace; font-size: 9px;"
        )
        self._chips_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._chips_clear.clicked.connect(self._clear_files)
        self._chips_layout.addStretch()
        self._chips_layout.addWidget(self._chips_clear)
        self._chips_row.hide()
        root.addWidget(self._chips_row)

        # Controls row
        ctrl = QHBoxLayout()
        ctrl.setContentsMargins(0, 0, 0, 0)
        ctrl.setSpacing(6)

        self._hint = QLabel("⌘K palette")
        self._hint.setStyleSheet(f"color: {MUTE}; font-family: 'JetBrains Mono', monospace; font-size: 9px;")
        ctrl.addWidget(self._hint)

        self._sep = QLabel("|")
        self._sep.setStyleSheet(f"color: {MUTE}; font-size: 10px;")
        ctrl.addWidget(self._sep)

        # Compact drawer menu — visible only in MIN breakpoint
        self._btn_menu = QPushButton("☰ menú")
        self._btn_menu.setProperty("inputBtnMenu", True)
        self._btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_menu.setToolTip("Paneles")
        self._btn_menu.clicked.connect(self._show_drawer_menu)
        self._btn_menu.hide()
        ctrl.addWidget(self._btn_menu)

        ctrl.addStretch()

        self._btn_always = QPushButton("◎ siempre")
        self._btn_always.setProperty("inputBtnAlways", True)
        self._btn_always.setProperty("alwaysActive", False)
        self._btn_always.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_always.clicked.connect(self.always_on_toggled)
        ctrl.addWidget(self._btn_always)

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

        self._btn_attach = QPushButton("📎 adjuntar")
        self._btn_attach.setProperty("inputBtnMute", True)
        self._btn_attach.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_attach.setToolTip("Adjuntar archivos")
        self._btn_attach.clicked.connect(self._attach_files)
        ctrl.addWidget(self._btn_attach)

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

    def set_compact(self, compact: bool) -> None:
        """MIN breakpoint: show menu btn, hide decorative/secondary buttons."""
        self._btn_menu.setVisible(compact)
        self._hint.setVisible(not compact)
        self._sep.setVisible(not compact)
        self._btn_always.setVisible(not compact)
        self._btn_cam.setVisible(not compact)

    def set_active_drawer(self, name: str | None) -> None:
        """Track which drawer is open — used to show close option in menu."""
        self._active_drawer = name
        if name:
            self._btn_menu.setText("✕ cerrar")
        else:
            self._btn_menu.setText("☰ menú")

    def _show_drawer_menu(self) -> None:
        # If a drawer is open, close it directly without showing the menu
        if self._active_drawer:
            self.drawer_requested.emit(self._active_drawer)
            return

        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QCursor, QAction
        _DRAWERS = [
            ("◆", "memoria",   "Memoria"),
            ("⊟", "historial", "Historial"),
            ("◑", "sistema",   "Sistema"),
            ("⊞", "cola",      "Cola"),
            ("◔", "notif",     "Notificaciones"),
            ("⬡", "tokens",    "Tokens"),
            ("⚙", "config",    "Configuración"),
        ]
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #0f1a2e; color: #cfd6e6;
                    border: 1px solid rgba(93,107,133,0.5);
                    font-family: 'JetBrains Mono', monospace; font-size: 10px; }
            QMenu::item { padding: 5px 14px; }
            QMenu::item:selected { background: rgba(136,201,58,0.15); color: #88c93a; }
            QMenu::separator { height: 1px; background: rgba(93,107,133,0.4); margin: 3px 8px; }
        """)

        # Actions
        always_glyph = "◉" if self._always_on_active else "◎"
        act_always = menu.addAction(f"{always_glyph}  Siempre activo")
        act_cam    = menu.addAction("◐  Cámara")
        menu.addSeparator()

        drawer_actions: dict[QAction, str] = {}
        for glyph, name, label in _DRAWERS:
            drawer_actions[menu.addAction(f"{glyph}  {label}")] = name

        chosen = menu.exec(QCursor.pos())
        if chosen == act_always:
            self.always_on_toggled.emit()
        elif chosen == act_cam:
            self.camera_toggled.emit()
        elif chosen in drawer_actions:
            self.drawer_requested.emit(drawer_actions[chosen])

    def set_always_on(self, active: bool) -> None:
        self._always_on_active = active
        self._btn_always.setText("◉ siempre" if active else "◎ siempre")
        self._btn_always.setProperty("alwaysActive", active)
        self._btn_always.style().unpolish(self._btn_always)
        self._btn_always.style().polish(self._btn_always)

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasUrls():
            local = [u for u in e.mimeData().urls() if u.isLocalFile()]
            if local:
                e.acceptProposedAction()
                self._field.setStyleSheet("border: 1px solid #88c93a;")
                return
        e.ignore()

    def dragLeaveEvent(self, e: QDragLeaveEvent) -> None:
        self._field.setStyleSheet("")

    def dropEvent(self, e: QDropEvent) -> None:
        self._field.setStyleSheet("")
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self._attached_files.extend(p for p in paths if p not in self._attached_files)
            self._refresh_chips()
            e.acceptProposedAction()
            self._on_submit()

    def _attach_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Adjuntar archivos")
        if paths:
            self._attached_files.extend(p for p in paths if p not in self._attached_files)
            self._refresh_chips()
            self._on_submit()

    def _clear_files(self) -> None:
        self._attached_files.clear()
        self._refresh_chips()

    def _open_file(self, path: str) -> None:
        import subprocess, shutil, yaml, pathlib
        try:
            cfg_path = pathlib.Path(__file__).parents[2] / "config.yaml"
            cfg = yaml.safe_load(cfg_path.read_text())
            editor = cfg.get("editor", "")
        except Exception:
            editor = ""
        if editor and shutil.which(editor):
            subprocess.Popen([editor, path], start_new_session=True)
        else:
            subprocess.Popen(["xdg-open", path], start_new_session=True)

    def _refresh_chips(self) -> None:
        import os
        # Clear all items and rebuild
        while self._chips_layout.count():
            item = self._chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self._attached_files:
            self._chips_row.hide()
            return
        for path in self._attached_files:
            name = os.path.basename(path)
            btn = QPushButton(f"📄 {name}")
            btn.setToolTip(path)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { color: #88c93a; background: rgba(136,201,58,0.08); "
                "border: 1px solid rgba(136,201,58,0.3); border-radius: 3px; "
                "font-family: 'JetBrains Mono', monospace; font-size: 9px; padding: 2px 6px; }"
                "QPushButton:hover { background: rgba(136,201,58,0.18); }"
            )
            btn.clicked.connect(lambda checked, p=path: self._open_file(p))
            self._chips_layout.addWidget(btn)
        self._chips_layout.addStretch()
        self._chips_clear = QPushButton("✕ limpiar")
        self._chips_clear.setStyleSheet(
            f"color: #5d6b85; border: none; background: transparent;"
            "font-family: 'JetBrains Mono', monospace; font-size: 9px;"
        )
        self._chips_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._chips_clear.clicked.connect(self._clear_files)
        self._chips_layout.addWidget(self._chips_clear)
        self._chips_row.show()

    def _on_submit(self) -> None:
        import os
        text = self.text()
        files = list(self._attached_files)
        if not text and not files:
            return
        if not text and files:
            names = "\n".join(f"- {os.path.basename(f)}" for f in files)
            text = f"Adjunté los siguientes archivos:\n{names}\n\n¿Qué deseas que haga con ellos?"
        elif files:
            names = ", ".join(os.path.basename(f) for f in files)
            text = f"[📎 {names}] {text}"
        self.message_submitted.emit(text, files)
        self.clear()
        self._clear_files()


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
