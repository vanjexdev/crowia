from PyQt6.QtWidgets import QLabel, QVBoxLayout, QFrame, QProgressBar, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt
from giselo.app.theme import LIME, CYAN, ORANGE, MUTE, INK, RED

CONTEXT_LIMIT = 200_000  # claude-sonnet context window


def _chars_to_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _row(layout: QVBoxLayout, label: str, value: str, color: str = INK) -> None:
    lbl = QLabel(f"<span style='color:{MUTE}'>{label}</span>  "
                 f"<span style='color:{color}'>{value}</span>")
    lbl.setStyleSheet("font-size: 11px; font-family: 'JetBrains Mono', monospace;")
    lbl.setTextFormat(Qt.TextFormat.RichText)
    layout.insertWidget(layout.count() - 1, lbl)


def _bar(layout: QVBoxLayout, pct: float, color: str) -> None:
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(int(pct))
    bar.setFixedHeight(5)
    bar.setTextVisible(False)
    bar.setStyleSheet(f"""
        QProgressBar {{
            background: rgba(93,107,133,0.2);
            border-radius: 2px;
            border: none;
        }}
        QProgressBar::chunk {{
            background: {color};
            border-radius: 2px;
        }}
    """)
    layout.insertWidget(layout.count() - 1, bar)


def _sep(layout: QVBoxLayout) -> None:
    sep = QFrame()
    sep.setFixedHeight(1)
    sep.setStyleSheet("background: rgba(93,107,133,0.3);")
    layout.insertWidget(layout.count() - 1, sep)


def build(layout: QVBoxLayout) -> None:
    from giselo.services import memory as mem_svc

    messages = mem_svc.get_messages()
    if not messages:
        lbl = QLabel("Sin mensajes aún")
        lbl.setStyleSheet(f"color: {MUTE}; font-size: 11px;")
        layout.insertWidget(layout.count() - 1, lbl)
        return

    user_texts = []
    asst_texts = []
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        if m.get("role") == "user":
            user_texts.append(content)
        else:
            asst_texts.append(content)

    input_tokens  = sum(_chars_to_tokens(t) for t in user_texts)
    output_tokens = sum(_chars_to_tokens(t) for t in asst_texts)
    total_tokens  = input_tokens + output_tokens
    ctx_pct       = min(100.0, total_tokens / CONTEXT_LIMIT * 100)

    # Context window usage
    ctx_color = LIME if ctx_pct < 60 else ORANGE if ctx_pct < 85 else RED
    _row(layout, "contexto usado", f"{total_tokens:,} / {CONTEXT_LIMIT:,}", ctx_color)
    _bar(layout, ctx_pct, ctx_color)

    spacer = QLabel("")
    spacer.setFixedHeight(4)
    layout.insertWidget(layout.count() - 1, spacer)

    # Breakdown
    _row(layout, "input  (usuario)", f"~{input_tokens:,} tok", ORANGE)
    _row(layout, "output (giselo)",  f"~{output_tokens:,} tok", CYAN)
    _row(layout, "total sesión",     f"~{total_tokens:,} tok",  LIME if total_tokens > 0 else MUTE)

    _sep(layout)

    # Per-message breakdown (last 6)
    title = QLabel("por mensaje (recientes)")
    title.setStyleSheet(f"color: {MUTE}; font-size: 9px; font-family: 'JetBrains Mono', monospace; letter-spacing:1px;")
    layout.insertWidget(layout.count() - 1, title)

    recent = messages[-6:]
    for m in recent:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        toks = _chars_to_tokens(content)
        author = "tú" if role == "user" else "giselo"
        color  = ORANGE if role == "user" else CYAN
        lbl = QLabel(f"<span style='color:{color}'>{author}</span>"
                     f"<span style='color:{MUTE}'> {toks:,} tok</span>")
        lbl.setStyleSheet("font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        layout.insertWidget(layout.count() - 1, lbl)
