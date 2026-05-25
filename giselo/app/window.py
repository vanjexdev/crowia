import logging
log = logging.getLogger(__name__)

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QSizePolicy, QApplication, QFrame, QPushButton,
                              QStackedWidget)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor

from giselo.app.theme import build_qss, LIME, CYAN, ORANGE, MUTE, RED
from giselo.app.state import state
from giselo.widgets.title_bar    import TitleBar
from giselo.widgets.tab_dock     import TabDock
from giselo.widgets.rail_left    import RailLeft
from giselo.widgets.rail_right   import RailRight
from giselo.widgets.drawer       import Drawer
from giselo.widgets.giselo_core  import GiseloCore
from giselo.widgets.stream_chat import StreamChatArea
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
        self.setMinimumSize(465, 600)
        self.resize(920, 640)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
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
        # Maps instance name → context name (usually same; shared if user chose to link)
        self._context_map: dict[str, str] = {n: n for n in state.INSTANCES}
        self._tts_streaming = False
        self._always_on = False
        self._tts_active = False
        self._cancelling = False
        self._voice_is_auto = False    # True only when recording was started by always-on
        self._wake_triggered = False   # True = next auto-recording skips wake word check
        self._palette = PalettePopup(self)
        self._palette.accent_selected.connect(self._on_accent)
        self._build_ui()
        self._connect_signals()
        self._apply_breakpoint(self.width())

        self._services: dict[str, "InstanceService"] = {}
        self._response_bufs: dict[str, str] = {n: "" for n in state.INSTANCES}
        self._sentence_bufs: dict[str, str] = {n: "" for n in state.INSTANCES}
        for _inst_name in state.INSTANCES:
            self._make_service(_inst_name)

        from crowia.config import load as load_cfg
        _cfg = load_cfg()

        from giselo.services.tts import TTSService
        self._tts = TTSService(_cfg, self)
        self._tts.started.connect(lambda: self._set_state("speaking"))
        self._tts.started.connect(lambda: setattr(self, "_tts_active", True))
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

        from giselo.app.resize_grip import ResizeFilter
        self._resize_filter = ResizeFilter(self)
        self._resize_filter.install()

        from giselo.widgets.floating_orb import FloatingOrb
        self._orb = FloatingOrb(self)

        from giselo.services.scheduler_svc import SchedulerService
        self._scheduler = SchedulerService(self)
        self._scheduler.reminder_due.connect(self._on_reminder_due)

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
        self._core_container = QWidget()
        self._core_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._giselo_core = GiseloCore(self._core_container)
        self._giselo_core.setGeometry(0, 0, 600, 400)
        from PyQt6.QtGui import QColor as _QColor
        self._giselo_core.set_accent(_QColor(state.accent))

        self._camera_pip = CameraPip(self._core_container)
        self._camera_pip.closed.connect(self._on_pip_closed)

        self._core_container.resizeEvent = self._on_core_container_resize
        center_layout.addWidget(self._core_container, stretch=1)

        # Cancel bar — visible while LLM is processing
        self._cancel_bar = QWidget()
        self._cancel_bar.setFixedHeight(26)
        _cb_lay = QHBoxLayout(self._cancel_bar)
        _cb_lay.setContentsMargins(10, 2, 12, 2)
        _cb_lay.addStretch()
        self._cancel_btn = QPushButton("✕ cancelar")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setFixedHeight(20)
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                color: {RED}; border: 1px solid {RED}; border-radius: 3px;
                background: transparent; font-size: 9px;
                font-family: 'JetBrains Mono', monospace; padding: 0px 8px;
            }}
            QPushButton:hover {{ background: rgba(230,57,70,0.15); }}
            QPushButton:pressed {{ background: rgba(230,57,70,0.30); }}
        """)
        self._cancel_btn.clicked.connect(self._on_cancel)
        _cb_lay.addWidget(self._cancel_btn)
        self._cancel_bar.hide()
        center_layout.addWidget(self._cancel_bar)

        self._chats: dict[str, StreamChatArea] = {}
        self._stacked_chat = QStackedWidget()
        for name in state.INSTANCES:
            chat = StreamChatArea()
            self._chats[name] = chat
            self._stacked_chat.addWidget(chat)
        active = state.active_instance
        self._stream_chat = self._chats.get(active, next(iter(self._chats.values())))
        self._stacked_chat.setCurrentWidget(self._stream_chat)
        center_layout.addWidget(self._stacked_chat)

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
        self._input_bar.always_on_toggled.connect(self.toggle_always_on)
        self._input_bar.drawer_requested.connect(self.toggle_drawer)
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
        self._stacked_chat.setVisible(is_compact)
        _active_svc = self._services.get(state.active_instance) if hasattr(self, '_services') else None
        self._cancel_bar.setVisible(is_compact and bool(_active_svc and _active_svc.busy))
        self._input_bar.set_compact(is_min)

        # Close drawer if we drop below MEDIUM
        if not is_medium and self._drawer.is_open():
            self._drawer.close_drawer()

        # PIP adapts via _on_core_container_resize — no explicit compact toggle needed

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
            self._voice_is_auto = False   # manual press — no wake word gate
            self._voice.start_recording()

    def toggle_always_on(self) -> None:
        self._always_on = not self._always_on
        self._input_bar.set_always_on(self._always_on)
        if self._always_on:
            if not self._voice.recording and not self._tts_active:
                self._voice_is_auto = True
                self._voice.start_recording(auto_stop=True)
            if hasattr(self, "_orb"):
                self._orb.show()
        else:
            self._wake_triggered = False
            if self._voice.recording:
                self._voice.stop_recording()
            if hasattr(self, "_orb") and not self.isMinimized():
                self._orb.hide()

    def _resume_always_on(self) -> None:
        if not self._always_on:
            return
        if self._voice.busy or self._tts_active or not self._input_bar.isEnabled():
            return
        self._voice_is_auto = True
        self._voice.start_recording(auto_stop=True)

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
        self._camera_pip.start(cam_index=index)
        state.camera_active = True
        self._status_bar.set_camera(True)
        self._rail_right.set_active("camara")
        self._reposition_pip()
        notif.push(f"Cámara [{index}] activada", "info")

    def open_palette(self) -> None:
        center = self.geometry().center()
        from PyQt6.QtCore import QPoint
        self._palette.show_at(QPoint(center.x(), center.y()))

    def _on_accent(self, color: str) -> None:
        state.accent = color
        self.setStyleSheet(build_qss(color))
        from PyQt6.QtGui import QColor
        self._giselo_core.set_accent(QColor(color))
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
            self._input_bar.set_active_drawer(None)
            state.active_drawer = None

    def switch_instance(self, name: str) -> None:
        from giselo.services import memory as mem_svc
        state.active_instance = name
        mem_svc.set_active(self._context_map.get(name, name))
        self._tab_dock.set_active(name)
        self._status_bar.set_instance(name)
        if name in self._chats:
            self._stream_chat = self._chats[name]
            self._stacked_chat.setCurrentWidget(self._stream_chat)
        svc = self._services.get(name)
        if svc:
            self._on_busy_changed(svc.busy)
        backend = state.INSTANCE_BACKENDS.get(name, "claude")
        notif.push(f"Instancia: {name} ({backend})", "info")
        self._refresh_drawer_if_open("config")

    def _make_service(self, name: str) -> "InstanceService":
        from giselo.services.instances import InstanceService
        svc = InstanceService(self)
        backend = state.INSTANCE_BACKENDS.get(name, "claude")
        svc.switch_backend(backend)
        svc.chunk_received.connect(lambda c, n=name: self._on_chunk_for(n, c))
        svc.response_complete.connect(lambda f, n=name: self._on_done_for(n, f))
        svc.response_error.connect(lambda e, n=name: self._on_error_for(n, e))
        svc.busy_changed.connect(lambda b, n=name: self._on_busy_for(n, b))
        self._services[name] = svc
        return svc

    def _on_add_instance(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "Nueva instancia", "Nombre:",
            text=f"claude-{len(state.INSTANCES) + 1}"
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in state.INSTANCES:
            return
        backend, ok2 = QInputDialog.getItem(
            self, "Backend", f"Backend para '{name}':",
            ["claude", "codex", "opencode", "gemini"], 0, False
        )
        if not ok2:
            return
        # Ask: fresh context or share with existing?
        ctx_options = ["Nuevo contexto"] + list(state.INSTANCES)
        ctx_choice, ok3 = QInputDialog.getItem(
            self, "Contexto", f"Contexto para '{name}':",
            ctx_options, 0, False
        )
        if not ok3:
            return

        state.INSTANCES = list(state.INSTANCES) + [name]
        state.INSTANCE_BACKENDS[name] = backend
        from giselo.app.state import save_instances
        save_instances(state.INSTANCES, state.INSTANCE_BACKENDS)
        self._make_service(name)
        self._response_bufs[name] = ""
        self._sentence_bufs[name] = ""

        if ctx_choice == "Nuevo contexto":
            chat = StreamChatArea()
            self._chats[name] = chat
            self._stacked_chat.addWidget(chat)
            self._context_map[name] = name
        else:
            # Share chat widget and history of the chosen instance
            self._chats[name] = self._chats[ctx_choice]
            self._context_map[name] = self._context_map.get(ctx_choice, ctx_choice)

        self._tab_dock.add_instance(name)
        self.switch_instance(name)
        notif.push(f"Instancia '{name}' ({backend}) creada", "ok")

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
        self._input_bar.set_active_drawer(name)
        self._drawer.open_drawer()
        if name == "historial":
            self._drawer.scroll_to_bottom()

    # ── TTS slots ─────────────────────────────────────────────────────────────

    def _on_tts_done(self) -> None:
        self._tts_active = False
        self._set_state("idle")
        self._giselo_core.set_pill_text("● ESCUCHANDO · LVL 0%")
        self._resume_always_on()

    # ── Voice slots ───────────────────────────────────────────────────────────

    def _on_voice_started(self) -> None:
        state.voice_active = True
        self._status_bar.set_voice(True)
        self._rail_right.set_active("voz")
        self._set_state("listening")
        self._giselo_core.set_pill_text("● GRABANDO · LVL 0%")
        notif.push("Grabación iniciada", "info")

    def _on_voice_stopped(self) -> None:
        self._rail_right.set_active(None)
        self._giselo_core.set_pill_text("● PROCESANDO VOZ...")

    def _on_voice_transcribed(self, text: str) -> None:
        state.voice_active = False
        self._status_bar.set_voice(False)
        was_auto = self._voice_is_auto
        self._voice_is_auto = False
        if was_auto:
            if self._wake_triggered:
                # Previous utterance was wake-word-only — process this one directly
                self._wake_triggered = False
            else:
                wake_words = self._get_wake_words()
                clean, triggered = self._check_wake_word(text, wake_words)
                if not triggered:
                    log.info("Always-on: no wake word in %r, resuming", text[:60])
                    preview = text[:30] if text.strip() else "(vacío)"
                    self._giselo_core.set_pill_text(f"● oí: {preview}")
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(2000, lambda: self._giselo_core.set_pill_text("● ESCUCHANDO · LVL 0%"))
                    QTimer.singleShot(2200, self._resume_always_on)
                    return
                text = clean
                if not text.strip():
                    # Name only — activate next utterance without wake word
                    self._wake_triggered = True
                    self._set_state("listening")
                    self._giselo_core.set_pill_text("● TE ESCUCHO...")
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(200, self._resume_always_on)
                    return
        notif.push(f"Voz: {text[:40]}", "ok")
        self._on_message(text)

    def _get_wake_words(self) -> list[str]:
        try:
            import yaml, pathlib
            cfg = yaml.safe_load(
                (pathlib.Path(__file__).parents[2] / "config.yaml").read_text(encoding="utf-8")
            )
            asst = cfg.get("assistant", {})
            ao = cfg.get("always_on", {})
            static = [p.lower() for p in ao.get("wake_phrases", [])]
            # Always include both name variants regardless of gender config
            names = {
                asst.get("name_male", "Giselo").lower(),
                asst.get("name_female", "Gisela").lower(),
            }
            dynamic = []
            for n in sorted(names):
                dynamic += [n, f"oye {n}", f"hey {n}", f"hola {n}"]
            return list(dict.fromkeys(static + dynamic))
        except Exception:
            return ["giselo", "gisela", "oye giselo", "hey giselo", "oye gisela", "hey gisela"]

    def _check_wake_word(self, text: str, wake_words: list[str]) -> tuple[str, bool]:
        import re
        low = text.lower().strip()
        for phrase in wake_words:
            if phrase in low:
                # Strip wake phrase from start of string
                cleaned = re.sub(rf'^\W*{re.escape(phrase)}\W*', '', low, flags=re.IGNORECASE).strip()
                return cleaned, True
        return text, False

    def _on_reminder_due(self, message: str) -> None:
        from datetime import datetime
        notif.push(f"Recordatorio: {message}", "info")
        active = state.active_instance
        chat = self._chats.get(active)
        if chat:
            ts = datetime.now().strftime("%H:%M")
            chat.begin_response(ts)
            chat.finish_response(f"🔔 Recordatorio: {message}", ts)
        self._tts.speak(message)

    def _on_voice_error(self, msg: str) -> None:
        state.voice_active = False
        self._status_bar.set_voice(False)
        self._rail_right.set_active(None)
        self._wake_triggered = False
        from PyQt6.QtCore import QTimer
        if self._always_on and msg == "No se detectó voz":
            # Silence/background noise — resume quietly without error UI
            log.debug("always-on: silent frame, resuming")
            self._set_state("idle")
            self._giselo_core.set_pill_text("● ESCUCHANDO · LVL 0%")
            QTimer.singleShot(500, self._resume_always_on)
            return
        self._set_state("error")
        self._giselo_core.set_pill_text("● ERROR VOZ")
        notif.push(f"Voz error: {msg}", "error")
        QTimer.singleShot(2000, lambda: (
            self._giselo_core.set_pill_text("● ESCUCHANDO · LVL 0%"),
            self._resume_always_on(),
        ))

    def _on_voice_level(self, level: int) -> None:
        if self._voice.recording:
            self._giselo_core.set_pill_text(f"● GRABANDO · LVL {level}%")

    # ── Internal slots ────────────────────────────────────────────────────────

    def _on_drawer_closed(self) -> None:
        self._rail_left.set_active(None)
        state.active_drawer = None
        self._input_bar.set_active_drawer(None)

    def _on_rail_right(self, action: str) -> None:
        if action == "voz":
            self.toggle_voice()
        elif action == "camara":
            self.toggle_camera()

    def _on_message(self, text: str) -> None:
        self._tts.stop()
        from datetime import datetime
        from giselo.services import memory as mem_svc
        ts = datetime.now().strftime("%H:%M")
        active = state.active_instance
        self._response_bufs[active] = ""
        self._sentence_bufs[active] = ""
        self._tts_streaming = False
        self._cancelling = False
        self._stream_chat.add_user(text, ts)
        self._stream_chat.begin_response(ts)
        self._set_state("thinking")
        self._giselo_core.set_pill_text("● PROCESANDO")
        self._input_bar.setEnabled(False)
        ctx = self._context_map.get(active, active)
        mem_svc.set_active(ctx)
        mem_svc.add_user(text)
        history = mem_svc.get_messages()[:-1]
        svc = self._services.get(active)
        if svc:
            svc.ask(text, history)

    def _on_chunk_for(self, instance: str, chunk: str) -> None:
        chat = self._chats.get(instance)
        if not chat:
            return
        prev = self._response_bufs.get(instance, "")
        if chunk.startswith(prev):
            delta = chunk[len(prev):]
            self._response_bufs[instance] = chunk
        else:
            delta = chunk
            self._response_bufs[instance] = prev + chunk
        chat.update_response(self._response_bufs[instance])
        if instance != state.active_instance or not delta:
            return
        self._set_state("speaking")
        self._giselo_core.set_pill_text("● RESPONDIENDO")
        from crowia.output import _split_sentences
        self._sentence_bufs[instance] = self._sentence_bufs.get(instance, "") + delta
        sentences, self._sentence_bufs[instance] = _split_sentences(self._sentence_bufs[instance])
        for sent in sentences:
            if not self._tts_streaming:
                self._tts.begin_stream(sent)
                self._tts_streaming = True
            else:
                self._tts.stream_sentence(sent)

    def _on_done_for(self, instance: str, full: str) -> None:
        from datetime import datetime
        from giselo.services import memory as mem_svc
        ts = datetime.now().strftime("%H:%M")
        ctx = self._context_map.get(instance, instance)
        prev_ctx = mem_svc._active_name
        mem_svc.set_active(ctx)
        mem_svc.add_assistant(full)
        mem_svc.set_active(prev_ctx)
        chat = self._chats.get(instance)
        if chat:
            chat.finish_response(full, ts)
        self._response_bufs[instance] = ""
        if instance != state.active_instance:
            return
        self._set_state("success")
        self._giselo_core.set_pill_text("● LISTO")
        notif.push("Respuesta recibida", "ok")
        self._refresh_drawer_if_open("historial")
        remaining = self._sentence_bufs.get(instance, "").strip()
        self._sentence_bufs[instance] = ""
        if remaining:
            if not self._tts_streaming:
                self._tts.begin_stream(remaining)
                self._tts_streaming = True
            else:
                self._tts.stream_sentence(remaining)
        tts_was_streaming = self._tts_streaming
        if self._tts_streaming:
            self._tts.end_stream()
        self._tts_streaming = False
        if self._always_on and not tts_was_streaming and not self._tts_active:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(600, self._resume_always_on)

    def _on_error_for(self, instance: str, msg: str) -> None:
        chat = self._chats.get(instance)
        if chat:
            chat.error_response(msg)
        self._response_bufs[instance] = ""
        if instance != state.active_instance:
            return
        self._tts_active = False
        if self._cancelling:
            self._cancelling = False
            self._set_state("idle")
            self._giselo_core.set_pill_text("● ESCUCHANDO · LVL 0%")
            self._input_bar.setEnabled(True)
            self._resume_always_on()
            return
        self._set_state("error")
        self._giselo_core.set_pill_text("● ERROR")
        notif.push(f"Error: {msg}", "error")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: (
            self._set_state("idle"),
            self._giselo_core.set_pill_text("● ESCUCHANDO · LVL 0%"),
            self._resume_always_on(),
        ))

    def _on_busy_for(self, instance: str, busy: bool) -> None:
        if instance == state.active_instance:
            self._on_busy_changed(busy)

    def _on_pip_closed(self) -> None:
        state.camera_active = False
        self._status_bar.set_camera(False)
        self._rail_right.set_active(None)
        notif.push("Cámara desactivada", "warn")
        cw, ch = self._core_container.width(), self._core_container.height()
        self._giselo_core.setGeometry(0, 0, cw, ch)

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
        QWidget.resizeEvent(self._core_container, event)
        cw, ch = event.size().width(), event.size().height()
        # GiseloCore always fills the container
        self._giselo_core.setGeometry(0, 0, cw, ch)
        # Clamp PIP so it stays within new container bounds
        if self._camera_pip.active:
            pip = self._camera_pip
            x = max(0, min(pip.x(), cw - pip.width()))
            y = max(0, min(pip.y(), ch - pip.height()))
            pip.move(x, y)

    def _reposition_pip(self) -> None:
        if not self._camera_pip.active:
            return
        cw = self._core_container.width()
        ch = self._core_container.height()
        # PIP: ~45% container width, 16:9, top-right corner
        pip_w = max(220, int(cw * 0.45))
        pip_h = int(pip_w * 9 / 16)
        pip_w = min(pip_w, cw - 24)
        pip_h = min(pip_h, ch - 24)
        pip_x = cw - pip_w - 12
        pip_y = 12
        self._camera_pip.setGeometry(pip_x, pip_y, pip_w, pip_h)
        self._camera_pip.raise_()

    def _on_cancel(self) -> None:
        self._cancelling = True
        svc = self._services.get(state.active_instance)
        if svc:
            svc.cancel()
        self._tts.stop()

    def _on_busy_changed(self, busy: bool) -> None:
        self._input_bar.setEnabled(not busy)
        self._cancel_bar.setVisible(busy)
        if not busy:
            state.giselo_state = "idle"
            if self._always_on and not self._voice.recording and not self._tts_active:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(400, self._resume_always_on)
        state.mem_tokens = len(str(self._response_bufs.get(state.active_instance, ""))) // 4
        self._status_bar.set_mem(state.mem_tokens)

    def _set_state(self, s: str) -> None:
        self._giselo_core.set_state(s)
        if hasattr(self, "_orb"):
            self._orb.set_state(s)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        from PyQt6.QtCore import QEvent
        from PyQt6.QtCore import Qt as _Qt
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, "_orb"):
            minimized = bool(self.windowState() & _Qt.WindowState.WindowMinimized)
            if minimized:
                self._orb.show()
            elif not self._always_on:
                self._orb.hide()

    def sizeHint(self) -> QSize:
        return QSize(920, 640)
