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

from giselo.panels import memoria, historial, sistema, cola, notif


DRAWER_BUILDERS = {
    "memoria":   (memoria.build,   LIME,   "Memoria"),
    "historial": (historial.build, CYAN,   "Historial"),
    "sistema":   (sistema.build,   "#e8c33a", "Sistema"),
    "cola":      (cola.build,      ORANGE, "Cola"),
    "notif":     (notif.build,     MUTE,   "Notificaciones"),
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Giselo")
        self.setMinimumSize(500, 600)
        self.resize(820, 640)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(build_qss(state.accent))

        self._fullscreen = False
        self._drawers: dict[str, Drawer] = {}
        self._response_buf = ""
        self._build_ui()
        self._connect_signals()
        self._apply_breakpoint(self.width())

        self._svc = InstanceService(self)
        self._svc.chunk_received.connect(self._on_chunk)
        self._svc.response_complete.connect(self._on_response_done)
        self._svc.response_error.connect(self._on_response_error)
        self._svc.busy_changed.connect(self._on_busy_changed)

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
        state.voice_active = not state.voice_active
        self._status_bar.set_voice(state.voice_active)

    def toggle_camera(self) -> None:
        if self._camera_pip.active:
            self._camera_pip.stop()
        else:
            compact = state.breakpoint == "MIN"
            self._camera_pip.start(compact)
            state.camera_active = True
            self._status_bar.set_camera(True)
            self._reposition_pip()

    def open_palette(self) -> None:
        pass  # Phase E

    def close_drawer(self) -> None:
        if self._drawer.is_open():
            self._drawer.close_drawer()
            self._rail_left.set_active(None)
            state.active_drawer = None

    def switch_instance(self, name: str) -> None:
        state.active_instance = name
        self._tab_dock.set_active(name)
        self._status_bar.set_instance(name)

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
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: (
            self._giselo_core.set_state("idle"),
            self._giselo_core.set_pill_text("● ESCUCHANDO · LVL 0%"),
        ))

    def _on_response_error(self, msg: str) -> None:
        self._giselo_core.set_state("error")
        self._giselo_core.set_pill_text("● ERROR")
        self._chat_preview.update_giselo(f"Error: {msg}", "--:--")

    def _on_pip_closed(self) -> None:
        state.camera_active = False
        self._status_bar.set_camera(False)

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
