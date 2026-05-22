from PyQt6.QtWidgets import QLabel, QVBoxLayout, QFrame, QSizePolicy
from PyQt6.QtCore import Qt
from giselo.app.theme import LIME, MUTE, INK, CYAN


def _row(layout, label: str, value: str, color: str = INK) -> None:
    lbl = QLabel(f"<span style='color:{MUTE}'>{label}</span>  "
                 f"<span style='color:{color}'>{value}</span>")
    lbl.setStyleSheet("font-size: 11px;")
    lbl.setTextFormat(Qt.TextFormat.RichText)
    layout.insertWidget(layout.count() - 1, lbl)


def build(layout: QVBoxLayout) -> None:
    from giselo.services import memory as mem_svc
    from giselo.app.state import state

    messages = mem_svc.get_messages()
    total    = len(messages)
    user_c   = sum(1 for m in messages if m.get("role") == "user")
    asst_c   = total - user_c

    # Approximate token count (4 chars ≈ 1 token)
    all_text = " ".join(
        m.get("content", "") if isinstance(m.get("content"), str)
        else " ".join(p.get("text","") for p in m.get("content",[]) if isinstance(p,dict))
        for m in messages
    )
    tokens = len(all_text) // 4

    _row(layout, "backend activo",  state.active_instance,  LIME)
    _row(layout, "mensajes totales", str(total))
    _row(layout, "  ↳ usuario",     str(user_c),            LIME if user_c else MUTE)
    _row(layout, "  ↳ giselo",      str(asst_c),            CYAN if asst_c else MUTE)
    _row(layout, "tokens aprox.",   f"{tokens:,}",          LIME if tokens > 0 else MUTE)

    # Separator
    sep = QFrame()
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background: rgba(93,107,133,0.4);")
    layout.insertWidget(layout.count() - 1, sep)

    # Recent phrases
    title = QLabel("frases recientes")
    title.setStyleSheet(f"color: {MUTE}; font-size: 9px; font-family: 'JetBrains Mono', monospace; letter-spacing:1px;")
    layout.insertWidget(layout.count() - 1, title)

    user_msgs = [
        m.get("content","") if isinstance(m.get("content"), str)
        else " ".join(p.get("text","") for p in m.get("content",[]) if isinstance(p,dict))
        for m in messages if m.get("role") == "user"
    ]
    recent = user_msgs[-3:] if user_msgs else []

    if not recent:
        lbl = QLabel("–")
        lbl.setStyleSheet(f"color: {MUTE}; font-size: 11px;")
        layout.insertWidget(layout.count() - 1, lbl)
    else:
        for phrase in recent:
            short = phrase[:60] + ("…" if len(phrase) > 60 else "")
            lbl = QLabel(f""{short}"")
            lbl.setStyleSheet(f"color: {INK}; font-size: 10px; font-style: italic;")
            lbl.setWordWrap(True)
            layout.insertWidget(layout.count() - 1, lbl)
