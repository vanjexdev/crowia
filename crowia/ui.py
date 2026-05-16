import logging
import math
import pathlib
import shutil
import subprocess
import threading

try:
    import markdown as _md_lib
    _MD_AVAILABLE = True
except ImportError:
    _MD_AVAILABLE = False

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QObject
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox,
    QHBoxLayout, QLabel, QMenu, QPlainTextEdit, QPushButton,
    QSplitter, QTextBrowser, QVBoxLayout, QWidget,
)

from . import prefs as prefs_mod

log = logging.getLogger(__name__)

_SCRIPTS_DIR = pathlib.Path(__file__).parent.parent / "scripts"
IMAGES_DIR = pathlib.Path(__file__).parent.parent / "images"

STATE_IMAGE = {
    "idle":       "normal.png",
    "recording":  "open.png",
    "processing": "normal.png",
    "done":       "like.png",
}

CROW_SIZE = 320


def _btn_style(r, g, b, dr=40, dg=40, db=40):
    return (
        f"QPushButton {{ background: rgba({r},{g},{b},180); color: white; border: none;"
        f" border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: bold; }}"
        f"QPushButton:hover {{ background: rgba({min(r+dr,255)},{min(g+dg,255)},{min(b+db,255)},210); }}"
        f"QPushButton:pressed {{ background: rgba({max(r-20,0)},{max(g-20,0)},{max(b-20,0)},220); }}"
    )


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

_ACTION_STYLE = (
    "QPushButton {"
    "  background: rgba(55, 110, 230, 180);"
    "  color: white; border: none; border-radius: 5px;"
    "  padding: 4px 10px; font-size: 11px; font-weight: bold;"
    "}"
    "QPushButton:hover { background: rgba(75, 130, 255, 210); }"
    "QPushButton:pressed { background: rgba(35, 80, 180, 220); }"
)

_MEM_STYLE = (
    "QPushButton {"
    "  background: rgba(80, 50, 130, 180);"
    "  color: white; border: none; border-radius: 5px;"
    "  padding: 4px 10px; font-size: 11px;"
    "}"
    "QPushButton:hover { background: rgba(110, 70, 170, 210); }"
)

_EXPORT_STYLE = (
    "QPushButton {"
    "  background: rgba(40, 100, 80, 180);"
    "  color: white; border: none; border-radius: 5px;"
    "  padding: 4px 10px; font-size: 11px;"
    "}"
    "QPushButton:hover { background: rgba(50, 130, 100, 210); }"
)


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

    def start(self):
        self._timer.start(50)

    def stop(self):
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


class _TextEdit(QPlainTextEdit):
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


class TextInputPanel(QWidget):
    submitted   = pyqtSignal(str, list)  # (text, [str paths])
    _file_ready = pyqtSignal(str)        # thread → main: path string

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: list[pathlib.Path] = []
        self._pending_file_path: str | None = None
        self._file_ready.connect(self._on_file_ready)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._edit = _TextEdit()
        self._edit.setPlaceholderText("Escribe tu mensaje… @ para adjuntar archivo/carpeta")
        self._edit.setMinimumHeight(60)
        self._edit.setStyleSheet(_INPUT_STYLE)
        layout.addWidget(self._edit)

        # Chips container — real QWidget so geometry updates propagate
        self._chips_widget = QWidget()
        self._chips_widget.hide()  # hidden until first chip added
        chips_inner = QHBoxLayout(self._chips_widget)
        chips_inner.setContentsMargins(0, 2, 0, 2)
        chips_inner.setSpacing(3)
        self._chips_row = chips_inner
        layout.addWidget(self._chips_widget)

        # Action buttons row
        btns = QHBoxLayout()
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(4)
        btns.addStretch()

        self.send_btn = QPushButton("Enviar ↩")
        self.send_btn.setStyleSheet(_ACTION_STYLE)
        self.send_btn.clicked.connect(self._submit)
        btns.addWidget(self.send_btn)

        self.memory_btn = QPushButton("💾 Memoria")
        self.memory_btn.setStyleSheet(_MEM_STYLE)
        btns.addWidget(self.memory_btn)

        self.export_btn = QPushButton("📋 Exportar")
        self.export_btn.setStyleSheet(_EXPORT_STYLE)
        btns.addWidget(self.export_btn)

        layout.addLayout(btns)

        self._edit.at_triggered.connect(self._pick_files)
        self._edit.submit_triggered.connect(self._submit)

    def focus(self):
        self._edit.setFocus()

    def _pick_files(self):
        menu = QMenu(self)
        menu.addAction("📄 Archivo", lambda: self._launch_picker(folder=False))
        menu.addAction("📁 Carpeta", lambda: self._launch_picker(folder=True))
        menu.exec(self._edit.mapToGlobal(self._edit.rect().bottomLeft()))

    @pyqtSlot(str)
    def _on_file_ready(self, path_str: str):
        self._add_chip(pathlib.Path(path_str))

    def _launch_picker(self, folder: bool):
        def _run():
            picker = shutil.which("giselo-pick") or str(_SCRIPTS_DIR / "giselo-pick")
            cmd = [picker, "--dir"] if folder else [picker]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                path = result.stdout.strip()
                if result.returncode == 0 and path:
                    log.info("Picker returned: %s", path)
                    self._file_ready.emit(path)
                else:
                    log.info("Picker cancelled or empty (rc=%d)", result.returncode)
            except Exception as e:
                log.error("File picker failed: %s", e)
        threading.Thread(target=_run, daemon=True).start()

    def _add_chip(self, path: pathlib.Path):
        if path in self._files:
            return
        self._files.append(path)
        btn = QPushButton(f"📎 {path.name} ✕")
        btn.setStyleSheet(_CHIP_STYLE)
        btn.clicked.connect(lambda checked=False, p=path, b=btn: self._remove_chip(p, b))
        self._chips_row.addWidget(btn)
        self._chips_widget.show()
        log.info("Chip added: %s (total: %d)", path.name, len(self._files))

    def _remove_chip(self, path: pathlib.Path, btn: QPushButton):
        if path in self._files:
            self._files.remove(path)
        btn.deleteLater()
        if not self._files:
            self._chips_widget.hide()

    def _submit(self):
        text = self._edit.toPlainText().strip()
        if not text:
            return
        files = [str(f) for f in self._files]
        self.submitted.emit(text, files)
        self._edit.clear()
        self._files.clear()
        for i in reversed(range(self._chips_row.count())):
            w = self._chips_row.itemAt(i).widget()
            if w:
                w.deleteLater()
        self._chips_widget.hide()


class PrefsDialog(QDialog):
    def __init__(self, prefs: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Giselo — Preferencias")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(320)
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

        self._cb_md = QCheckBox("Renderizar markdown en respuesta")
        self._cb_md.setChecked(prefs.get("render_markdown", False))
        if not _MD_AVAILABLE:
            self._cb_md.setEnabled(False)
            self._cb_md.setToolTip("pip install markdown para habilitar")
        layout.addWidget(self._cb_md)

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
            "render_markdown": self._cb_md.isChecked(),
        }


class CrowiaOverlay(QWidget):
    text_submitted = pyqtSignal(str, list)
    tts_toggled    = pyqtSignal(bool)
    save_memory    = pyqtSignal()
    export_summary = pyqtSignal()
    skip_tts       = pyqtSignal()

    def __init__(self, cfg: dict | None = None, on_cancel=None):
        super().__init__()
        self._prefs = prefs_mod.load()
        self._on_cancel = on_cancel

        out_cfg = (cfg or {}).get("output", {})
        tts_default = out_cfg.get("tts_enabled", True)
        self._tts_enabled = self._prefs.get("tts_enabled", tts_default)
        self._render_md = self._prefs.get("render_markdown", False) and _MD_AVAILABLE

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

        # ── root layout ────────────────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(0)

        layout_mode = self._prefs.get("layout_mode", "horizontal")
        orientation = (Qt.Orientation.Horizontal
                       if layout_mode == "horizontal"
                       else Qt.Orientation.Vertical)
        self._splitter = QSplitter(orientation)
        self._splitter.setHandleWidth(6)
        self._splitter.setStyleSheet(
            "QSplitter::handle { background: rgba(100,150,255,60); border-radius: 2px; }"
        )
        self._splitter.splitterMoved.connect(self._on_splitter_moved)
        root.addWidget(self._splitter)

        # ── left panel (crow + controls) ───────────────────────────────────────
        left = QWidget()
        left.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 4, 0)
        ll.setSpacing(4)

        self._crow = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self._crow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        ll.addWidget(self._crow)

        self._backend_label = QLabel("Claude", alignment=Qt.AlignmentFlag.AlignCenter)
        self._backend_label.setStyleSheet(
            "color: rgba(180,220,255,200); font-size: 13px; font-weight: bold; letter-spacing: 2px;"
        )
        self._backend_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        ll.addWidget(self._backend_label)

        self._bars = AudioBars()
        ll.addWidget(self._bars, alignment=Qt.AlignmentFlag.AlignHCenter)

        left_btns = QHBoxLayout()
        left_btns.setContentsMargins(0, 4, 0, 0)
        left_btns.setSpacing(4)

        self._cancel_btn = QPushButton("⏹")
        self._cancel_btn.setToolTip("Cancelar")
        self._cancel_btn.setStyleSheet(_btn_style(180, 40, 40))
        self._cancel_btn.setFixedSize(34, 30)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        self._cancel_btn.hide()
        left_btns.addWidget(self._cancel_btn)

        self._skip_btn = QPushButton("⏭")
        self._skip_btn.setToolTip("Saltar audio")
        self._skip_btn.setStyleSheet(_btn_style(160, 100, 20))
        self._skip_btn.setFixedSize(34, 30)
        self._skip_btn.clicked.connect(lambda: (self.skip_tts.emit(), self._apply_state("idle")))
        self._skip_btn.hide()
        left_btns.addWidget(self._skip_btn)

        left_btns.addStretch()

        self._tts_btn = QPushButton(self._tts_icon())
        self._tts_btn.setToolTip("Activar/desactivar voz")
        self._tts_btn.setStyleSheet(_btn_style(40, 80, 140))
        self._tts_btn.setFixedSize(34, 30)
        self._tts_btn.clicked.connect(self._on_tts_clicked)
        left_btns.addWidget(self._tts_btn)

        self._mode_btn = QPushButton("⇔" if layout_mode == "horizontal" else "⇕")
        self._mode_btn.setToolTip("Cambiar orientación")
        self._mode_btn.setStyleSheet(_btn_style(60, 60, 120))
        self._mode_btn.setFixedSize(34, 30)
        self._mode_btn.clicked.connect(self._toggle_layout_mode)
        left_btns.addWidget(self._mode_btn)

        self._hide_right_btn = QPushButton()
        self._hide_right_btn.setToolTip("Mostrar/ocultar panel")
        self._hide_right_btn.setStyleSheet(_btn_style(60, 100, 60))
        self._hide_right_btn.setFixedSize(34, 30)
        self._hide_right_btn.clicked.connect(self._toggle_right_panel)
        left_btns.addWidget(self._hide_right_btn)

        ll.addLayout(left_btns)
        self._splitter.addWidget(left)

        # ── right panel (response + input) ─────────────────────────────────────
        self._right_widget = QWidget()
        self._right_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        rl = QVBoxLayout(self._right_widget)
        rl.setContentsMargins(4, 0, 0, 0)
        rl.setSpacing(4)

        self._response_box = QTextBrowser()
        self._response_box.setFont(QFont("Sans", 10))
        self._response_box.setMinimumWidth(500)
        self._response_box.setMinimumHeight(600)
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
        rl.addWidget(self._response_box, stretch=1)

        self._input_panel = TextInputPanel()
        self._input_panel.submitted.connect(self._on_text_submitted)
        self._input_panel.memory_btn.clicked.connect(self.save_memory)
        self._input_panel.export_btn.clicked.connect(self.export_summary)
        rl.addWidget(self._input_panel)

        self._splitter.addWidget(self._right_widget)

        # Restore splitter sizes and right panel visibility
        sizes_key = "splitter_sizes_h" if layout_mode == "horizontal" else "splitter_sizes_v"
        self._splitter.setSizes(self._prefs.get(sizes_key, [380, 340]))

        right_visible = self._prefs.get("right_panel_visible", True)
        self._right_widget.setVisible(right_visible)
        self._update_hide_btn_icon()

        # ── signals ────────────────────────────────────────────────────────────
        self._signals = _Signals()
        self._signals.state.connect(self._apply_state)
        self._signals.response.connect(self._apply_response)
        self._signals.cancel.connect(self._on_cancel_clicked)
        self._signals.tts_state.connect(self._apply_tts_state)

        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self._set_image("idle")
        self._move_bottom_right()

    # ── public thread-safe API ────────────────────────────────────────────────

    def notify(self, state: str):
        self._signals.state.emit(state)

    def set_backend(self, name: str):
        self._signals.state.emit(f"backend:{name}")

    def set_response(self, text: str):
        self._signals.response.emit(text)

    def set_tts_state(self, enabled: bool):
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
            self._skip_btn.hide()
        else:
            self._bars.stop()
            self._cancel_btn.hide()
        if state == "done":
            if self._tts_enabled:
                self._skip_btn.show()
                # keep overlay open long enough for TTS to finish
                QTimer.singleShot(120_000, lambda: self._apply_state("idle"))
            else:
                QTimer.singleShot(3000, lambda: self._apply_state("idle"))
        if state == "idle":
            self._skip_btn.hide()
        self.show()
        self._fit()

    def _on_cancel_clicked(self):
        self._cancel_btn.hide()
        self._fit()
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

    def _toggle_layout_mode(self):
        current = self._prefs.get("layout_mode", "horizontal")
        new_mode = "vertical" if current == "horizontal" else "horizontal"

        # Save current sizes before switching
        cur_key = "splitter_sizes_h" if current == "horizontal" else "splitter_sizes_v"
        self._prefs[cur_key] = self._splitter.sizes()
        self._prefs["layout_mode"] = new_mode

        new_orient = (Qt.Orientation.Horizontal
                      if new_mode == "horizontal"
                      else Qt.Orientation.Vertical)
        self._splitter.setOrientation(new_orient)

        new_key = "splitter_sizes_h" if new_mode == "horizontal" else "splitter_sizes_v"
        defaults = [380, 340] if new_mode == "horizontal" else [300, 360]
        self._splitter.setSizes(self._prefs.get(new_key, defaults))

        self._mode_btn.setText("⇔" if new_mode == "horizontal" else "⇕")
        self._update_hide_btn_icon()
        prefs_mod.save(self._prefs)
        self._move_bottom_right()

    def _toggle_right_panel(self):
        visible = self._right_widget.isVisible()
        self._right_widget.setVisible(not visible)
        self._prefs["right_panel_visible"] = not visible
        self._update_hide_btn_icon()
        prefs_mod.save(self._prefs)
        self._fit()

    def _update_hide_btn_icon(self):
        mode = self._prefs.get("layout_mode", "horizontal")
        visible = self._right_widget.isVisible()
        if mode == "horizontal":
            self._hide_right_btn.setText("◀" if visible else "▶")
        else:
            self._hide_right_btn.setText("▲" if visible else "▼")

    def _on_text_submitted(self, text: str, files: list):
        self.text_submitted.emit(text, files)

    def _apply_response(self, text: str):
        if not text:
            return
        if self._render_md and _MD_AVAILABLE:
            html = _md_lib.markdown(text, extensions=["fenced_code", "tables"])
            md_style = (
                "<style>"
                "body{color:rgba(220,235,255,230);font-family:Sans;font-size:10pt;}"
                "code{background:rgba(255,255,255,15);border-radius:3px;padding:1px 4px;}"
                "pre{background:rgba(0,0,0,50);border-radius:6px;padding:8px;}"
                "</style>"
            )
            self._response_box.setHtml(md_style + html)
        else:
            self._response_box.setPlainText(text)
        if self._prefs.get("show_response_text", True):
            self._response_box.show()
            self._fit()

    def _on_splitter_moved(self, _pos, _index):
        mode = self._prefs.get("layout_mode", "horizontal")
        sizes_key = "splitter_sizes_h" if mode == "horizontal" else "splitter_sizes_v"
        self._prefs[sizes_key] = self._splitter.sizes()
        prefs_mod.save(self._prefs)

    def _set_image(self, state: str):
        px = self._pixmaps.get(state, self._pixmaps.get("idle"))
        if px:
            self._crow.setPixmap(px)

    def _restore_splitter_sizes(self):
        mode = self._prefs.get("layout_mode", "horizontal")
        sizes_key = "splitter_sizes_h" if mode == "horizontal" else "splitter_sizes_v"
        defaults = [340, 720] if mode == "horizontal" else [340, 600]
        self._splitter.setSizes(self._prefs.get(sizes_key, defaults))

    def _preferred_width(self) -> int:
        mode = self._prefs.get("layout_mode", "horizontal")
        if mode == "horizontal":
            sizes = self._prefs.get("splitter_sizes_h", [340, 720])
            return sizes[0] + (sizes[1] if self._right_widget.isVisible() else 0) + 22
        sizes = self._prefs.get("splitter_sizes_v", [340, 600])
        return max(sizes[0], sizes[1] if self._right_widget.isVisible() else sizes[0]) + 22

    def _fit(self):
        """Resize preserving splitter width; only adjust height."""
        w = self._splitter.width() + 16
        if w < 100:
            w = self._preferred_width()
        self.resize(w, self.sizeHint().height())

    def _move_bottom_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(self._preferred_width(), self.sizeHint().height())
        self.move(screen.width() - self.width() - 24, screen.height() - self.height() - 48)

    # ── mouse / keyboard ──────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(50, self._restore_splitter_sizes)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, _event):
        self.hide()

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        show_text = self._prefs.get("show_response_text", True)
        menu.addAction(
            "Ocultar texto de respuesta" if show_text else "Mostrar texto de respuesta",
            self._toggle_response_text,
        )
        menu.addAction(
            "Silenciar voz" if self._tts_enabled else "Activar voz",
            self._on_tts_clicked,
        )
        menu.addAction("Preferencias…", self._open_prefs_dialog)
        menu.addSeparator()
        menu.addAction("Ocultar", self.hide)
        menu.addSeparator()
        menu.addAction("Salir", QApplication.quit)
        menu.exec(event.globalPos())

    def _toggle_response_text(self):
        show = not self._prefs.get("show_response_text", True)
        self._prefs["show_response_text"] = show
        self._response_box.setVisible(show)
        prefs_mod.save(self._prefs)
        self._fit()

    def _open_prefs_dialog(self):
        dlg = PrefsDialog(self._prefs, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_prefs = dlg.result_prefs()
            tts_changed = new_prefs.get("tts_enabled") != self._prefs.get("tts_enabled")
            md_changed = new_prefs.get("render_markdown") != self._prefs.get("render_markdown")
            self._prefs = new_prefs
            self._tts_enabled = new_prefs.get("tts_enabled", True)
            self._tts_btn.setText(self._tts_icon())
            if md_changed:
                self._render_md = new_prefs.get("render_markdown", False) and _MD_AVAILABLE
            prefs_mod.save(self._prefs)
            if tts_changed:
                self.tts_toggled.emit(self._tts_enabled)
