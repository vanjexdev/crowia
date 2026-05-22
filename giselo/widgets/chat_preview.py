from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QSizePolicy
from PyQt6.QtCore import Qt
from giselo.app.theme import ORANGE, CYAN, MUTE, INK, PANEL


class ChatCard(QFrame):
    def __init__(self, author: str, timestamp: str, body: str, is_user: bool, parent=None):
        super().__init__(parent)
        self.setProperty("chatCard", True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(72)

        color = ORANGE if is_user else CYAN
        self.setStyleSheet(
            f"QFrame[chatCard='true'] {{ border-left: 3px solid {color}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        # Header row
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(6)

        author_lbl = QLabel(author)
        author_lbl.setProperty("cardAuthor", True)
        author_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700;")

        time_lbl = QLabel(timestamp)
        time_lbl.setProperty("cardTime", True)

        h_layout.addWidget(author_lbl)
        h_layout.addStretch()
        h_layout.addWidget(time_lbl)
        layout.addWidget(header)

        # Body
        body_lbl = QLabel(body)
        body_lbl.setProperty("cardBody", True)
        body_lbl.setWordWrap(False)
        body_lbl.setText(body if len(body) <= 60 else body[:57] + "...")
        layout.addWidget(body_lbl)
        layout.addStretch()


class ChatPreview(QWidget):
    """Two side-by-side chat cards (last user msg + last giselo response)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chat-preview")
        self.setFixedHeight(80)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        self._user_card   = ChatCard("tú",     "–:––", "escribe o habla…",        is_user=True)
        self._giselo_card = ChatCard("giselo", "–:––", "esperando respuesta…",    is_user=False)

        layout.addWidget(self._user_card)
        layout.addWidget(self._giselo_card)

    def update_user(self, text: str, timestamp: str) -> None:
        self._user_card = self._refresh(self._user_card, "tú", timestamp, text, True)

    def update_giselo(self, text: str, timestamp: str) -> None:
        self._giselo_card = self._refresh(self._giselo_card, "giselo", timestamp, text, False)

    def _refresh(self, old: ChatCard, author, ts, body, is_user) -> ChatCard:
        layout = self.layout()
        idx = layout.indexOf(old)
        layout.removeWidget(old)
        old.deleteLater()
        new = ChatCard(author, ts, body, is_user, self)
        layout.insertWidget(idx, new)
        return new
