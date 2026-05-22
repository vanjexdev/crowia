from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QSizePolicy, QApplication, QFrame)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor

from giselo.app.theme import build_qss, LIME, CYAN, ORANGE, MUTE
from giselo.app.state import state
from giselo.services.instances import InstanceService
from giselo.widgets.title_bar    import TitleBar
from giselo.widgets.tab_dock     import TabDock
from giselo.widgets.rail_left    import RailLeft
from giselo.widgets.rail_right   import RailRight
from giselo.widgets.drawer       import Drawer
from giselo.widgets.giselo_core  import GiseloCore
from giselo.widgets.chat_preview import ChatPreview
from giselo.widgets.input_bar    import InputBar
from giselo.widgets.status_bar   import StatusBar
from giselo.widgets.camera_pip   import CameraPip
from giselo.widgets.palette_popup import PalettePopup

from giselo.panels import memoria, historial, sistema, cola, notif, tokens, config_panel


DRAWER_BUILDERS = {
    "memoria":   (memoria.build,   LIME,      "Memoria"),
    "historial": (historial.build, CYAN,      "Historial"),
    "sistema":   (sistema.build,   "#e8c33a", "Sistema"),
    "cola":      (cola.build,      ORANGE,    "Cola"),
    "notif":     (notif.build,     MUTE,      "Notificaciones"),
    "tokens":    (tokens.build,       LIME,      "Tokens"),
    "config":    (config_panel.build, MUTE,      "Configuración"),
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Giselo")
        self.setMinimumSize(500, 600)
        self.resize(820, 640)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        try:
            import yaml, pathlib as _pl
            _p = _pl.Path(__file__).parents[2] / "config.yaml"
            _accent = yaml.safe_load(_p.read_text(encoding="utf-8")).get("ui", {}).get("accent")
            if _accent:
                state.accent = _accent
        except Exception:
            pass

        self.setStyleSheet(build_qss(state.accent))

        self._fullscreen = False
        self._drawers: dict[str, Drawer] = {}
        self._response_buf = ""
        self._palette = PalettePopup(self)
        self._palette.accent_selected.connect(self._on_accent)
        self._build_ui()
        self._connect_signals()
        self._apply_breakpoint(self.width())

        self._svc = InstanceService(self)
        self._svc.chunk_received.connect(self._on_chunk)
        self._svc.response_complete.connect(self._on_response_done)
        self._svc.response_error.connect(self._on_response_error)
        self._svc.busy_changed.connect(self._on_busy_changed)

        from crowia.config import load as load_cfg
        _cfg = load_cfg()

        from giselo.services.tts import TTSService
        self._tts = TTSService(_cfg, self)
        self._tts.started.connect(lambda: self._giselo_core.set_state("speaking"))
        self._tts.finished.connect(self._on_tts_done)
        self._tts.error.connect(lambda e: notif.push(f"TTS: {e}", "warn"))

        from giselo.services.voice import VoiceService
        self._voice = VoiceService(_cfg, self)
        self._voice.started.connect(self._on_voice_started)
        self._voice.stopped_recording.connect(self._on_voice_stopped)
        self._voice.transcribed.connect(self._on_voice_transcribed)
        self._voice.error.connect(self._on_voice_error)
        self._voice.level_changed.connect(self._on_voice_level)

        from giselo.app import shortcuts
        shortcuts.register(self)

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Title bar
        self._title_bar = TitleBar(self)
        root_layout.addWidget(self._title_bar)

        # Tab dock
        self._tab_dock = TabDock(list(state.INSTANCES), state.active_instance)
        root_layout.addWidget(self._tab_dock)

        # Separator line (replaces tab-dock border-bottom)
        sep = QFrame()
        sep.setObjectName("tab-separator")
        sep.setFixedHeight(1)
        root_layout.addWidget(sep)

        # Body row: [drawer?] [rail-left] [center] [rail-right]
        body = QWidget()
        self._body_layout = QHBoxLayout(body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)

        # Drawer (shared, reused for all panels)
        self._drawer = Drawer("Memoria", color=LIME)
        self._drawer.hide()
        self._body_layout.addWidget(self._drawer)

        self._rail_left  = RailLeft()
        self._body_layout.addWidget(self._rail_left)

        # Center column
        center = QWidget()
        center.setObjectName("center-widget")
        center.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # GiseloCore wrapped in a container so CameraPip can float over it
        core_container = QWidget()
        core_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._giselo_core = GiseloCore(core_container)
        self._giselo_core.setGeometry(0, 0, 600, 400)

        self._camera_pip = CameraPip(core_container)
        self._camera_pip.closed.connect(self._on_pip_closed)

        core_container.resizeEvent = self._on_core_container_resize
        center_layout.addWidget(core_container, stretch=1)

        self._chat_preview = ChatPreview()
        center_layout.addWidget(self._chat_preview)

        self._input_bar = InputBar()
        center_layout.addWidget(self._input_bar)

        self._body_layout.addWidget(center, stretch=1)

        self._rail_right = RailRight()
        self._body_layout.addWidget(self._rail_right)

        root_layout.addWidget(body, stretch=1)

        # Status bar
        self._status_bar = StatusBar(state.version, state.build)
        root_layout.addWidget(self._status_bar)

    # ── Signals ───────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._tab_dock.instance_changed.connect(self.switch_instance)
        self._tab_dock.instance_add_requested.connect(self._on_add_instance)
        self._rail_left.drawer_toggled.connect(self.toggle_drawer)
        self._rail_right.action_triggered.connect(self._on_rail_right)
        self._input_bar.message_submitted.connect(self._on_message)
        self._input_bar.camera_toggled.connect(self.toggle_camera)
        self._input_bar.voice_toggled.connect(self.toggle_voice)
        self._drawer.closed.connect(self._on_drawer_closed)

    # ── Breakpoint / responsive ───────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w = event.size().width()
        self._apply_breakpoint(w)
        self._title_bar.update_size_hint(w, event.size().height(), w > 620)

    def _apply_breakpoint(self, w: int) -> None:
        bp = state.set_breakpoint(w)

        is_min     = bp == "MIN"
        is_compact = bp in ("COMPACT", "MEDIUM", "LARGE")
        is_medium  = bp in ("MEDIUM", "LARGE")

        self._rail_left.setVisible(is_compact)
        self._rail_right.setVisible(is_compact)
        self._chat_preview.setVisible(is_compact)

        # Close drawer if we drop below MEDIUM
        if not is_medium and self._drawer.is_open():
            self._drawer.close_drawer()

        # Adjust PIP size on breakpoint change
        if hasattr(self, "_camera_pip"):
            self._camera_pip.set_compact(is_min)

    # ── Shortcut slots ────────────────────────────────────────────────────────

    def toggle_fullscreen(self) -> None:
        if self._fullscreen:
            self.showNormal()
        else:
            self.showFullScreen()
        self._fullscreen = not self._fullscreen

    def send_message(self) -> None:
        self._input_bar._on_submit()

    def toggle_voice(self) -> None:
        if self._voice.recording:
            self._voice.stop_recording()
        else:
            self._voice.start_recording()

    def toggle_camera(self) -> None:
        if self._camera_pip.active:
            self._camera_pip.stop()
            return

        from PyQt6.QtMultimedia import QMediaDevices
        cameras = QMediaDevices.videoInputs()
        if not cameras:
            return

        if len(cameras) == 1:
            self._start_camera(0)
        else:
            from PyQt6.QtWidgets import QMenu
            from PyQt6.QtGui import QCursor
            menu = QMenu(self)
            menu.setStyleSheet(f"""
                QMenu {{ background: #0f1a2e; color: #cfd6e6; border: 1px solid #cfd6e6;
                         font-family: 'JetBrains Mono', monospace; font-size: 11px; }}
                QMenu::item {{ padding: 5px 16px; }}
                QMenu::item:selected {{ background: rgba(136,201,58,0.15); color: #88c93a; }}
            """)
            for i, cam in enumerate(cameras):
                action = menu.addAction(f"[{i}] {cam.description()}")
                action.setData(i)
            chosen = menu.exec(QCursor.pos())
            if chosen:
                self._start_camera(chosen.data())

    def _start_camera(self, index: int) -> None:
        compact = state.breakpoint == "MIN"
        self._camera_pip.start(compact, cam_index=index)
        state.camera_active = True
        self._status_bar.set_camera(True)
        self._reposition_pip()
        notif.push(f"Cámara [{index}] activada", "info")

    def open_palette(self) -> None:
        center = self.geometry().center()
        from PyQt6.QtCore import QPoint
        self._palette.show_at(QPoint(center.x(), center.y()))

    def _on_accent(self, color: str) -> None:
        state.accent = color
        self.setStyleSheet(build_qss(color))
        try:
            from ruamel.yaml import YAML
            import io, pathlib
            _yaml = YAML(); _yaml.preserve_quotes = True
            p = pathlib.Path(__file__).parents[2] / "config.yaml"
            cfg = _yaml.load(p.read_text(encoding="utf-8"))
            cfg.setdefault("ui", {})["accent"] = color
            buf = io.StringIO(); _yaml.dump(cfg, buf)
            p.write_text(buf.getvalue(), encoding="utf-8")
        except Exception:
            pass

    def close_drawer(self) -> None:
        if self._drawer.is_open():
            self._drawer.close_drawer()
            self._rail_left.set_active(None)
            state.active_drawer = None

    def switch_instance(self, name: str) -> None:
        from giselo.services import memory as mem_svc
        state.active_instance = name
        mem_svc.set_active(name)
        self._tab_dock.set_active(name)
        self._status_bar.set_instance(name)
        self._svc.switch_backend(name)
        notif.push(f"Instancia: {name}", "info")
        self._refresh_drawer_if_open("config")

    def _on_add_instance(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "Nueva instancia", "Nombre:",
            text=f"claude-{len(state.INSTANCES)+1}"
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in state.INSTANCES:
            return
        state.INSTANCES = list(state.INSTANCES) + [name]
        self._tab_dock.add_instance(name)
        self.switch_instance(name)
        notif.push(f"Instancia '{name}' creada", "ok")

    def toggle_drawer(self, name: str) -> None:
        if state.active_drawer == name and self._drawer.is_open():
            self.close_drawer()
            return

        if name not in DRAWER_BUILDERS:
            return

        build_fn, color, title = DRAWER_BUILDERS[name]
        state.active_drawer = name

        # Reset drawer content
        layout = self._drawer.content_layout()
        while layout.count() > 1:  # keep the stretch at the end
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._drawer.set_title(title)
        build_fn(layout)

        self._rail_left.set_active(name)
        self._drawer.open_drawer()
        if name == "historial":
            self._drawer.scroll_to_bottom()

    # ── TTS slots ─────────────────────────────────────────────────────────────

    def _on_tts_done(self) -> None:
        self._giselo_core.set_state("idle")
        self._giselo_core.set_pill_text("● ESCUCHANDO · LVL 0%")

    # ── Voice slots ───────────────────────────────────────────────────────────

    def _on_voice_started(self) -> None:
        state.voice_active = True
        self._status_bar.set_voice(True)
        self._giselo_core.set_pill_text("● GRABANDO · LVL 0%")
        notif.push("Grabación iniciada", "info")

    def _on_voice_stopped(self) -> None:
        self._giselo_core.set_pill_text("● PROCESANDO VOZ...")

    def _on_voice_transcribed(self, text: str) -> None:
        state.voice_active = False
        self._status_bar.set_voice(False)
        notif.push(f"Voz: {text[:40]}", "ok")
        self._on_message(text)

    def _on_voice_error(self, msg: str) -> None:
        state.voice_active = False
        self._status_bar.set_voice(False)
        self._giselo_core.set_state("error")
        self._giselo_core.set_pill_text("● ERROR VOZ")
        notif.push(f"Voz error: {msg}", "error")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self._giselo_core.set_pill_text("● ESCUCHANDO · LVL 0%"))

    def _on_voice_level(self, level: int) -> None:
        if self._voice.recording:
            self._giselo_core.set_pill_text(f"● GRABANDO · LVL {level}%")

    # ── Internal slots ────────────────────────────────────────────────────────

    def _on_drawer_closed(self) -> None:
        self._rail_left.set_active(None)
        state.active_drawer = None

    def _on_rail_right(self, action: str) -> None:
        if action == "voz":
            self.toggle_voice()
        elif action == "camara":
            self.toggle_camera()

    def _on_message(self, text: str) -> None:
        self._tts.stop()
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M")
        self._response_buf = ""
        self._chat_preview.update_user(text, ts)
        self._giselo_core.set_state("thinking")
        self._giselo_core.set_pill_text("● PROCESANDO")
        self._input_bar.setEnabled(False)
        self._svc.ask(text)

    def _on_chunk(self, chunk: str) -> None:
        self._response_buf += chunk
        self._giselo_core.set_state("speaking")
        self._giselo_core.set_pill_text("● RESPONDIENDO")
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M")
        self._chat_preview.update_giselo(self._response_buf, ts)

    def _on_response_done(self, full: str) -> None:
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M")
        self._chat_preview.update_giselo(full, ts)
        self._giselo_core.set_state("success")
        self._giselo_core.set_pill_text("● LISTO")
        notif.push("Respuesta recibida", "ok")
        self._refresh_drawer_if_open("historial")
        self._tts.speak(full)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: (
            self._giselo_core.set_state("speaking" if self._tts._worker else "idle"),
            self._giselo_core.set_pill_text("● HABLANDO" if self._tts._worker else "● ESCUCHANDO · LVL 0%"),
        ))

    def _on_response_error(self, msg: str) -> None:
        self._giselo_core.set_state("error")
        self._giselo_core.set_pill_text("● ERROR")
        self._chat_preview.update_giselo(f"Error: {msg}", "--:--")
        self._input_bar.setEnabled(True)
        notif.push(f"Error: {msg}", "error")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: (
            self._giselo_core.set_state("idle"),
            self._giselo_core.set_pill_text("● ESCUCHANDO · LVL 0%"),
        ))

    def _on_pip_closed(self) -> None:
        state.camera_active = False
        self._status_bar.set_camera(False)
        notif.push("Cámara desactivada", "warn")

    def _refresh_drawer_if_open(self, name: str) -> None:
        if state.active_drawer != name or not self._drawer.is_open():
            return
        if name not in DRAWER_BUILDERS:
            return
        build_fn, _, _ = DRAWER_BUILDERS[name]
        layout = self._drawer.content_layout()
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        build_fn(layout)
        if name == "historial":
            self._drawer.scroll_to_bottom()

    def _on_core_container_resize(self, event) -> None:
        QWidget.resizeEvent(self._giselo_core.parent(), event)
        self._giselo_core.setGeometry(0, 0, event.size().width(), event.size().height())
        self._reposition_pip()

    def _reposition_pip(self) -> None:
        if not self._camera_pip.active:
            return
        cw = self._giselo_core.width()
        pip_w = self._camera_pip.width()
        pip_h = self._camera_pip.height()
        x = (cw - pip_w) // 2
        self._camera_pip.move(x, 12)
        self._camera_pip.raise_()

    def _on_busy_changed(self, busy: bool) -> None:
        self._input_bar.setEnabled(not busy)
        if not busy:
            state.giselo_state = "idle"
        state.mem_tokens = len(str(self._response_buf)) // 4
        self._status_bar.set_mem(state.mem_tokens)

    def sizeHint(self) -> QSize:
        return QSize(820, 640)
