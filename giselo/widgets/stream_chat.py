import re
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from giselo.app.theme import ORANGE, CYAN, MUTE, INK

_TOOL_RE = re.compile(r'[⏺●]\s*(\w+)\(')


def _now() -> str:
    return datetime.now().strftime("%H:%M")


class _Bubble(QFrame):
    def __init__(self, author: str, is_user: bool, parent=None):
        super().__init__(parent)
        color = ORANGE if is_user else CYAN
        self.setStyleSheet(
            f"QFrame {{ border: none; border-left: 3px solid {color}; "
            f"background: transparent; }}"
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 5, 10, 7)
        lay.setSpacing(2)

        hdr = QWidget()
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        au = QLabel(author)
        au.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 700; "
            f"font-family: 'JetBrains Mono', monospace;"
        )
        self._ts = QLabel(_now())
        self._ts.setStyleSheet(
            f"color: {MUTE}; font-size: 9px; font-family: 'JetBrains Mono', monospace;"
        )
        hl.addWidget(au)
        hl.addStretch()
        hl.addWidget(self._ts)
        lay.addWidget(hdr)

        self._tool = QLabel()
        self._tool.setStyleSheet(
            f"color: {MUTE}; font-size: 9px; font-family: 'JetBrains Mono', monospace; "
            f"padding: 1px 4px; background: rgba(93,107,133,0.12); border-radius: 2px;"
        )
        self._tool.hide()
        lay.addWidget(self._tool)

        self._body = QLabel()
        self._body.setWordWrap(True)
        self._body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._body.setStyleSheet(
            f"color: {INK}; font-size: 10px; "
            f"font-family: 'JetBrains Mono', monospace;"
        )
        lay.addWidget(self._body)

    def set_text(self, text: str, ts: str | None = None) -> None:
        self._body.setText(text)
        if ts:
            self._ts.setText(ts)

    def set_tool(self, name: str | None) -> None:
        if name:
            self._tool.setText(f"⏺  {name}...")
            self._tool.show()
        else:
            self._tool.hide()


class StreamChatArea(QWidget):
    """Scrollable chat area with live streaming support."""

    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(240)
        self.setObjectName("stream-chat-area")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._scrollbar = scroll.verticalScrollBar()

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._msgs = QVBoxLayout(self._content)
        self._msgs.setContentsMargins(8, 4, 8, 6)
        self._msgs.setSpacing(4)
        self._msgs.addStretch()

        scroll.setWidget(self._content)
        root.addWidget(scroll, stretch=1)

        self._active: _Bubble | None = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def add_user(self, text: str, ts: str) -> None:
        b = _Bubble("tú", is_user=True, parent=self._content)
        b.set_text(text, ts)
        self._insert(b)

    def begin_response(self, ts: str) -> None:
        b = _Bubble("giselo", is_user=False, parent=self._content)
        b.set_text("...", ts)
        self._insert(b)
        self._active = b

    def update_response(self, text: str) -> None:
        if not self._active:
            return
        tools = _TOOL_RE.findall(text)
        self._active.set_tool(tools[-1] if tools else None)
        self._active.set_text(text)
        self._scroll_bottom()

    def finish_response(self, text: str, ts: str) -> None:
        if self._active:
            self._active.set_tool(None)
            self._active.set_text(text, ts)
        self._active = None
        self._scroll_bottom()

    def error_response(self, msg: str) -> None:
        self.finish_response(f"⚠ {msg}", _now())

    # ── Internal ───────────────────────────────────────────────────────────────

    def _insert(self, widget: QWidget) -> None:
        idx = self._msgs.count() - 1  # before trailing stretch
        self._msgs.insertWidget(idx, widget)
        self._scroll_bottom()

    def _scroll_bottom(self) -> None:
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(30, lambda: self._scrollbar.setValue(
            self._scrollbar.maximum()
        ))
