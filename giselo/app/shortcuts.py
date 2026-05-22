from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShortcut


def register(window: QWidget) -> None:
    def _s(seq: str, slot):
        sc = QShortcut(QKeySequence(seq), window)
        sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
        sc.activated.connect(slot)
        return sc

    _s("Ctrl+F",       window.toggle_fullscreen)
    _s("Ctrl+Return",  window.send_message)
    _s("Ctrl+L",       window.toggle_voice)
    _s("Ctrl+Shift+C", window.toggle_camera)
    _s("Ctrl+K",       window.open_palette)
    _s("Escape",       window.close_drawer)

    _s("Ctrl+1", lambda: window.switch_instance("opencode"))
    _s("Ctrl+2", lambda: window.switch_instance("claude"))
    _s("Ctrl+3", lambda: window.switch_instance("codex"))

    _s("Ctrl+Shift+1", lambda: window.toggle_drawer("memoria"))
    _s("Ctrl+Shift+2", lambda: window.toggle_drawer("historial"))
    _s("Ctrl+Shift+3", lambda: window.toggle_drawer("sistema"))
    _s("Ctrl+Shift+4", lambda: window.toggle_drawer("cola"))
    _s("Ctrl+Shift+5", lambda: window.toggle_drawer("notif"))
