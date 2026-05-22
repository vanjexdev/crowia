from PyQt6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QWidget, QFrame
from giselo.app.theme import MUTE, LIME, ORANGE, CYAN, INK
from giselo.app.state import state


def _row(label: str, value: str, color: str, layout: QVBoxLayout) -> None:
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(8)
    lbl = QLabel(label)
    lbl.setStyleSheet(f"color: {MUTE}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
    val = QLabel(value)
    val.setStyleSheet(f"color: {color}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
    hl.addWidget(lbl)
    hl.addStretch()
    hl.addWidget(val)
    layout.insertWidget(layout.count() - 1, row)


def _sep(layout: QVBoxLayout) -> None:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {INK};")
    layout.insertWidget(layout.count() - 1, line)


def build(layout: QVBoxLayout) -> None:
    backend = state.INSTANCE_BACKENDS.get(state.active_instance, state.active_instance)

    proc_state = state.giselo_state
    state_color = {
        "idle":     MUTE,
        "thinking": ORANGE,
        "speaking": CYAN,
        "success":  LIME,
        "error":    "#cc4040",
    }.get(proc_state, MUTE)
    state_label = {
        "idle":     "en reposo",
        "thinking": "procesando…",
        "speaking": "respondiendo…",
        "success":  "listo",
        "error":    "error",
    }.get(proc_state, proc_state)

    _row("estado",    state_label,            state_color, layout)
    _row("instancia", state.active_instance,  LIME,        layout)
    _row("backend",   backend,                CYAN,        layout)

    _sep(layout)

    pending = [m for m in state.messages if m.get("role") == "user"]
    pending_lbl = QLabel(f"mensajes pendientes: {len(pending)}")
    pending_lbl.setStyleSheet(
        f"color: {ORANGE if pending else MUTE}; font-size: 10px; "
        f"font-family: 'JetBrains Mono', monospace;"
    )
    layout.insertWidget(layout.count() - 1, pending_lbl)

    tok_color = LIME if state.mem_tokens < 50000 else (ORANGE if state.mem_tokens < 150000 else "#cc4040")
    _row("tokens ctx", f"{state.mem_tokens:,}", tok_color, layout)

    _sep(layout)

    flags = []
    if state.voice_active:
        flags.append(("◉ voz activa",    LIME))
    if state.camera_active:
        flags.append(("◐ cámara activa", CYAN))
    if not flags:
        flags.append(("sin actividad",   MUTE))

    for text, color in flags:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 10px; font-family: 'JetBrains Mono', monospace;"
        )
        layout.insertWidget(layout.count() - 1, lbl)
