import math
import pathlib
import shutil
import subprocess
import threading

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox,
    QHBoxLayout, QLabel, QMenu, QPlainTextEdit, QPushButton,
    QTextBrowser, QVBoxLayout, QWidget,
)

_SCRIPTS_DIR = pathlib.Path(__file__).parent.parent / "scripts"

from . import prefs as prefs_mod

IMAGES_DIR = pathlib.Path(__file__).parent.parent / "images"

STATE_IMAGE = {
    "idle":       "normal.png",
    "recording":  "open.png",
    "processing": "normal.png",
    "done":       "like.png",
}

CROW_SIZE = 360


class _Signals(QObject):
    state     = pyqtSignal(str)
    response  = pyqtSignal(str)
    cancel    = pyqtSignal()
    tts_state = pyqtSignal(bool)


class AudioBars(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(CROW_SIZE, 40)
        self._heights = [0.2] * 5
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._active = False

    def start(self):
        self._active = True
        self._timer.start(50)

    def stop(self):
        self._active = False
        self._timer.stop()
        self._heights = [0.2] * 5
        self.update()

    def _tick(self):
        self._phase += 0.3
        for i in range(5):
            self._heights[i] = 0.3 + 0.7 * abs(math.sin(self._phase + i * 0.8))
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bar_w = self.width() // (5 * 2 - 1)
        gap = bar_w
        p.setBrush(QColor(100, 200, 255, 220))
        p.setPen(Qt.PenStyle.NoPen)
        for i, h in enumerate(self._heights):
            bar_h = int(self.height() * h)
            x = i * (bar_w + gap) + gap // 2
            y = self.height() - bar_h
            p.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)


# ── text input components ─────────────────────────────────────────────────────

class _TextEdit(QPlainTextEdit):
    """Plain-text edit that intercepts Enter (submit) and @ (file picker)."""
    at_triggered     = pyqtSignal()
    submit_triggered = pyqtSignal()

    def keyPressEvent(self, event):
        if (event.key() == Qt.Key.Key_Return
                and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)):
            self.submit_triggered.emit()
            return
        super().keyPressEvent(event)
        if event.text() == "@":
            c = self.textCursor()
            c.deletePreviousChar()
            self.setTextCursor(c)
            self.at_triggered.emit()


_INPUT_STYLE = (
    "QPlainTextEdit {"
    "  background: rgba(10, 10, 20, 200);"
    "  color: rgba(220, 235, 255, 230);"
    "  border-radius: 6px;"
    "  padding: 6px;"
    "  border: 1px solid rgba(100, 150, 255, 80);"
    "  font-size: 12px;"
    "}"
)

_CHIP_STYLE = (
    "QPushButton {"
    "  background: rgba(50, 70, 130, 180);"
    "  color: rgba(200, 220, 255, 220);"
    "  border: none; border-radius: 4px;"
    "  padding: 2px 7px; font-size: 10px;"
    "}"
    "QPushButton:hover { background: rgba(140, 40, 40, 180); }"
)

_SEND_STYLE = (
    "QPushButton {"
    "  background: rgba(55, 110, 230, 180);"
    "  color: white; border: none; border-radius: 5px;"
    "  padding: 4px 12px; font-size: 11px; font-weight: bold;"
    "}"
    "QPushButton:hover { background: rgba(75, 130, 255, 210); }"
    "QPushButton:pressed { background: rgba(35, 80, 180, 220); }"
)


class TextInputPanel(QWidget):
    submitted  = pyqtSignal(str, list)  # (text, [str paths])
    _file_ready = pyqtSignal(str)       # thread → main: path string

    def __init__(self, resp_width: int, parent=None):
        super().__init__(parent)
        self._files: list[pathlib.Path] = []
        self._file_ready.connect(lambda p: self._add_chip(pathlib.Path(p)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(4)

        self._edit = _TextEdit()
        self._edit.setPlaceholderText("Escribe tu mensaje… @ para adjuntar archivo/carpeta")
        self._edit.setFixedHeight(72)
        self._edit.setMinimumWidth(resp_width)
        self._edit.setStyleSheet(_INPUT_STYLE)
        layout.addWidget(self._edit)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(4)

        self._chips = QHBoxLayout()
        self._chips.setContentsMargins(0, 0, 0, 0)
        self._chips.setSpacing(3)
        bottom.addLayout(self._chips)
        bottom.addStretch()

        send_btn = QPushButton("Enviar ↩")
        send_btn.setStyleSheet(_SEND_STYLE)
        send_btn.clicked.connect(self._submit)
        bottom.addWidget(send_btn)

        layout.addLayout(bottom)

        self._edit.at_triggered.connect(self._pick_files)
        self._edit.submit_triggered.connect(self._submit)

    def focus(self):
        self._edit.setFocus()

    def _pick_files(self):
        menu = QMenu(self)
        menu.addAction("📄 Archivo", lambda: self._launch_picker(folder=False))
        menu.addAction("📁 Carpeta", lambda: self._launch_picker(folder=True))
        menu.exec(self._edit.mapToGlobal(self._edit.rect().bottomLeft()))

    def _launch_picker(self, folder: bool):
        def _run():
            picker = shutil.which("giselo-pick") or str(_SCRIPTS_DIR / "giselo-pick")
            cmd = [picker, "--dir"] if folder else [picker]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0 and result.stdout.strip():
                    self._file_ready.emit(result.stdout.strip())
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

    def _add_chip(self, path: pathlib.Path):
        if path in self._files:
            return
        self._files.append(path)
        btn = QPushButton(f"📎 {path.name} ✕")
        btn.setStyleSheet(_CHIP_STYLE)
        btn.clicked.connect(lambda checked=False, p=path, b=btn: self._remove_chip(p, b))
        self._chips.addWidget(btn)

    def _remove_chip(self, path: pathlib.Path, btn: QPushButton):
        if path in self._files:
            self._files.remove(path)
        btn.deleteLater()

    def _submit(self):
        text = self._edit.toPlainText().strip()
        if not text:
            return
        files = [str(f) for f in self._files]
        self.submitted.emit(text, files)
        self._edit.clear()
        self._files.clear()
        for i in reversed(range(self._chips.count())):
            w = self._chips.itemAt(i).widget()
            if w:
                w.deleteLater()


# ── preferences dialog ────────────────────────────────────────────────────────

class PrefsDialog(QDialog):
    def __init__(self, prefs: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Giselo — Preferencias")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(300)
        self._prefs = dict(prefs)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self._cb_text = QCheckBox("Mostrar respuesta en texto")
        self._cb_text.setChecked(prefs.get("show_response_text", True))
        layout.addWidget(self._cb_text)

        self._cb_tts = QCheckBox("Activar respuesta por voz (TTS)")
        self._cb_tts.setChecked(prefs.get("tts_enabled", True))
        layout.addWidget(self._cb_tts)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_prefs(self) -> dict:
        return {
            **self._prefs,
            "show_response_text": self._cb_text.isChecked(),
            "tts_enabled": self._cb_tts.isChecked(),
        }


# ── main overlay ──────────────────────────────────────────────────────────────

_BTN_BASE = (
    "QPushButton {"
    "  background: rgba({r}, {g}, {b}, 180);"
    "  color: white; border: none; border-radius: 6px;"
    "  padding: 5px 10px; font-size: 12px; font-weight: bold;"
    "}"
    "QPushButton:hover {{ background: rgba({rh}, {gh}, {bh}, 210); }}"
    "QPushButton:pressed {{ background: rgba({rp}, {gp}, {bp}, 220); }}"
)


def _btn_style(r, g, b, dr=40, dg=40, db=40):
    return (
        f"QPushButton {{ background: rgba({r},{g},{b},180); color: white; border: none;"
        f" border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: bold; }}"
        f"QPushButton:hover {{ background: rgba({min(r+dr,255)},{min(g+dg,255)},{min(b+db,255)},210); }}"
        f"QPushButton:pressed {{ background: rgba({max(r-20,0)},{max(g-20,0)},{max(b-20,0)},220); }}"
    )


class CrowiaOverlay(QWidget):
    text_submitted = pyqtSignal(str, list)   # (text, [str paths]) — from UI thread
    tts_toggled    = pyqtSignal(bool)        # new tts state — from UI thread

    def __init__(self, cfg: dict | None = None, on_cancel=None):
        super().__init__()
        self._prefs = prefs_mod.load()
        self._on_cancel = on_cancel

        out_cfg = (cfg or {}).get("output", {})
        resp_w = out_cfg.get("response_width", CROW_SIZE)
        resp_h = out_cfg.get("response_height", 220)
        tts_default = out_cfg.get("tts_enabled", True)
        self._tts_enabled = self._prefs.get("tts_enabled", tts_default)

        self.setWindowTitle("Giselo")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._pixmaps: dict[str, QPixmap] = {}
        for state, fname in STATE_IMAGE.items():
            path = IMAGES_DIR / fname
            if path.exists():
                px = QPixmap(str(path))
                self._pixmaps[state] = px.scaledToWidth(
                    CROW_SIZE, Qt.TransformationMode.SmoothTransformation
                )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self._crow = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self._crow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._crow)

        self._backend_label = QLabel("Claude", alignment=Qt.AlignmentFlag.AlignCenter)
        self._backend_label.setStyleSheet(
            "color: rgba(180,220,255,200); font-size: 13px; font-weight: bold; letter-spacing: 2px;"
        )
        self._backend_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._backend_label)

        self._bars = AudioBars()
        self._bars.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._bars)

        # Action buttons row
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 2, 0, 2)
        btn_row.setSpacing(6)

        self._cancel_btn = QPushButton("⏹ Cancelar")
        self._cancel_btn.setStyleSheet(_btn_style(180, 40, 40))
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        self._cancel_btn.hide()
        btn_row.addWidget(self._cancel_btn)

        btn_row.addStretch()

        self._tts_btn = QPushButton(self._tts_icon())
        self._tts_btn.setToolTip("Activar/desactivar voz")
        self._tts_btn.setStyleSheet(_btn_style(40, 80, 140))
        self._tts_btn.setFixedSize(34, 30)
        self._tts_btn.clicked.connect(self._on_tts_clicked)
        btn_row.addWidget(self._tts_btn)

        self._input_toggle_btn = QPushButton("⌨")
        self._input_toggle_btn.setToolTip("Escribir mensaje")
        self._input_toggle_btn.setStyleSheet(_btn_style(40, 100, 60))
        self._input_toggle_btn.setFixedSize(34, 30)
        self._input_toggle_btn.clicked.connect(self._toggle_input_panel)
        btn_row.addWidget(self._input_toggle_btn)

        layout.addLayout(btn_row)

        # Response box
        self._response_box = QTextBrowser()
        self._response_box.setFont(QFont("Sans", 10))
        self._response_box.setMinimumWidth(resp_w)
        self._response_box.setMaximumWidth(resp_w + 40)
        self._response_box.setMinimumHeight(60)
        self._response_box.setMaximumHeight(resp_h)
        self._response_box.setOpenExternalLinks(False)
        self._response_box.setStyleSheet(
            "QTextBrowser {"
            "  background: rgba(10, 10, 20, 180);"
            "  color: rgba(220, 235, 255, 230);"
            "  border-radius: 8px;"
            "  padding: 8px;"
            "  border: 1px solid rgba(100, 150, 255, 80);"
            "}"
        )
        layout.addWidget(self._response_box)

        # Text input panel (hidden by default)
        self._input_panel = TextInputPanel(resp_width=resp_w)
        self._input_panel.hide()
        self._input_panel.submitted.connect(self._on_text_submitted)
        layout.addWidget(self._input_panel)

        self._signals = _Signals()
        self._signals.state.connect(self._apply_state)
        self._signals.response.connect(self._apply_response)
        self._signals.cancel.connect(self._on_cancel_clicked)
        self._signals.tts_state.connect(self._apply_tts_state)

        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self._set_image("idle")
        self._apply_prefs(save=False)
        self.adjustSize()
        self._move_bottom_right()

    # ── public thread-safe API ────────────────────────────────────────────────

    def notify(self, state: str):
        self._signals.state.emit(state)

    def set_backend(self, name: str):
        self._signals.state.emit(f"backend:{name}")

    def set_response(self, text: str):
        self._signals.response.emit(text)

    def set_tts_state(self, enabled: bool):
        """Called from worker thread when voice command changes TTS state."""
        self._signals.tts_state.emit(enabled)

    # ── slots (main thread) ───────────────────────────────────────────────────

    def _apply_state(self, state: str):
        if state.startswith("backend:"):
            self._backend_label.setText(state[8:].upper())
            return
        self._set_image(state)
        if state in ("recording", "processing"):
            self._bars.start()
            self._cancel_btn.show()
        else:
            self._bars.stop()
            self._cancel_btn.hide()
        if state == "done":
            QTimer.singleShot(3000, lambda: self._apply_state("idle"))
        self.show()
        self.adjustSize()

    def _on_cancel_clicked(self):
        self._cancel_btn.hide()
        self.adjustSize()
        if self._on_cancel:
            threading.Thread(target=self._on_cancel, daemon=True).start()

    def _on_tts_clicked(self):
        self._tts_enabled = not self._tts_enabled
        self._prefs["tts_enabled"] = self._tts_enabled
        prefs_mod.save(self._prefs)
        self._tts_btn.setText(self._tts_icon())
        self.tts_toggled.emit(self._tts_enabled)

    def _apply_tts_state(self, enabled: bool):
        self._tts_enabled = enabled
        self._prefs["tts_enabled"] = enabled
        prefs_mod.save(self._prefs)
        self._tts_btn.setText(self._tts_icon())

    def _tts_icon(self) -> str:
        return "🔊" if self._tts_enabled else "🔇"

    def _toggle_input_panel(self):
        if self._input_panel.isVisible():
            self._input_panel.hide()
        else:
            self._input_panel.show()
            self._input_panel.focus()
        self.adjustSize()

    def _on_text_submitted(self, text: str, files: list):
        self.text_submitted.emit(text, files)

    def _apply_response(self, text: str):
        self._response_box.setPlainText(text)
        if self._prefs.get("show_response_text", True) and text:
            self._response_box.show()
            self.adjustSize()

    def _apply_prefs(self, save: bool = True):
        show = self._prefs.get("show_response_text", True)
        if show and self._response_box.toPlainText():
            self._response_box.show()
        else:
            self._response_box.hide()
        self._tts_enabled = self._prefs.get("tts_enabled", True)
        self._tts_btn.setText(self._tts_icon())
        if save:
            prefs_mod.save(self._prefs)
        self.adjustSize()

    def _set_image(self, state: str):
        px = self._pixmaps.get(state, self._pixmaps.get("idle"))
        if px:
            self._crow.setPixmap(px)

    def _move_bottom_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(screen.width() - self.width() - 24, screen.height() - self.height() - 48)

    # ── mouse / keyboard ──────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self._input_panel.isVisible():
                self._input_panel.hide()
                self.adjustSize()
            else:
                self.hide()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, _event):
        self.hide()

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)

        show_text = self._prefs.get("show_response_text", True)
        toggle_label = "Ocultar texto de respuesta" if show_text else "Mostrar texto de respuesta"
        menu.addAction(toggle_label, self._toggle_response_text)

        tts_label = "Silenciar voz" if self._tts_enabled else "Activar voz"
        menu.addAction(tts_label, self._on_tts_clicked)

        menu.addAction("Preferencias…", self._open_prefs_dialog)
        menu.addSeparator()
        menu.addAction("Ocultar", self.hide)
        menu.addSeparator()
        menu.addAction("Salir", QApplication.quit)
        menu.exec(event.globalPos())

    def _toggle_response_text(self):
        self._prefs["show_response_text"] = not self._prefs.get("show_response_text", True)
        self._apply_prefs()

    def _open_prefs_dialog(self):
        dlg = PrefsDialog(self._prefs, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_prefs = dlg.result_prefs()
            tts_changed = new_prefs.get("tts_enabled") != self._prefs.get("tts_enabled")
            self._prefs = new_prefs
            self._apply_prefs()
            if tts_changed:
                self.tts_toggled.emit(self._tts_enabled)
