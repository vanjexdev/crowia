from PyQt6.QtWidgets import QLabel, QVBoxLayout, QFrame, QSizePolicy
from PyQt6.QtCore import Qt
from giselo.app.theme import ORANGE, CYAN, MUTE, INK, PANEL


def build(layout: QVBoxLayout) -> None:
    from giselo.services import memory as mem_svc
    messages = mem_svc.get_messages()

    if not messages:
        lbl = QLabel("Sin historial aún")
        lbl.setStyleSheet(f"color: {MUTE}; font-size: 11px;")
        layout.insertWidget(layout.count() - 1, lbl)
        return

    for msg in messages:
        role    = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            )

        color  = ORANGE if role == "user" else CYAN
        author = "tú" if role == "user" else "giselo"

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: rgba(15,26,46,0.6);
                border-left: 2px solid {color};
                border-radius: 4px;
                margin-bottom: 2px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 5, 8, 5)
        card_layout.setSpacing(3)

        author_lbl = QLabel(author)
        author_lbl.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 700;"
            f"font-family: 'JetBrains Mono', monospace;"
        )
        card_layout.addWidget(author_lbl)

        body_lbl = QLabel(content)
        body_lbl.setStyleSheet(f"color: {INK}; font-size: 11px;")
        body_lbl.setWordWrap(True)
        body_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        card_layout.addWidget(body_lbl)

        layout.insertWidget(layout.count() - 1, card)
