import pathlib
import yaml
from PyQt6.QtWidgets import (QLabel, QVBoxLayout, QHBoxLayout, QComboBox,
                              QCheckBox, QLineEdit, QPushButton, QFrame,
                              QWidget, QSpinBox)
from PyQt6.QtCore import Qt
from giselo.app.theme import LIME, CYAN, ORANGE, MUTE, INK, RED, CHROME

CONFIG_PATH = pathlib.Path(__file__).parents[2] / "config.yaml"


def _load() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _save(cfg: dict) -> None:
    CONFIG_PATH.write_text(
        yaml.dump(cfg, allow_unicode=True, default_flow_style=False,
                  sort_keys=False),
        encoding="utf-8",
    )


def _section_title(layout: QVBoxLayout, text: str) -> None:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color: {MUTE}; font-size: 9px; font-family: 'JetBrains Mono', monospace;"
        f"letter-spacing: 1px; margin-top: 6px;"
    )
    layout.insertWidget(layout.count() - 1, lbl)


def _sep(layout: QVBoxLayout) -> None:
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: rgba(93,107,133,0.25);")
    layout.insertWidget(layout.count() - 1, f)


def _row_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFixedWidth(88)
    lbl.setStyleSheet(f"color: {MUTE}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
    return lbl


def _combo(options: list[str], current: str) -> QComboBox:
    cb = QComboBox()
    cb.addItems(options)
    cb.setStyleSheet(f"""
        QComboBox {{
            background: rgba(15,26,46,0.8); color: {INK};
            border: 1px solid rgba(93,107,133,0.4); border-radius: 4px;
            font-size: 10px; font-family: 'JetBrains Mono', monospace;
            padding: 2px 6px;
        }}
        QComboBox::drop-down {{ border: none; width: 16px; }}
        QComboBox QAbstractItemView {{
            background: #0f1a2e; color: {INK};
            selection-background-color: rgba(136,201,58,0.15);
        }}
    """)
    idx = cb.findText(current)
    if idx >= 0:
        cb.setCurrentIndex(idx)
    return cb


def _lineedit(value: str) -> QLineEdit:
    le = QLineEdit(value)
    le.setStyleSheet(f"""
        QLineEdit {{
            background: rgba(15,26,46,0.8); color: {INK};
            border: 1px solid rgba(93,107,133,0.4); border-radius: 4px;
            font-size: 10px; font-family: 'JetBrains Mono', monospace;
            padding: 2px 6px;
        }}
        QLineEdit:focus {{ border-color: {LIME}; }}
    """)
    return le


def _spinbox(value: int, min_: int, max_: int) -> QSpinBox:
    sb = QSpinBox()
    sb.setRange(min_, max_)
    sb.setValue(value)
    sb.setStyleSheet(f"""
        QSpinBox {{
            background: rgba(15,26,46,0.8); color: {INK};
            border: 1px solid rgba(93,107,133,0.4); border-radius: 4px;
            font-size: 10px; font-family: 'JetBrains Mono', monospace;
            padding: 2px 6px;
        }}
        QSpinBox:focus {{ border-color: {LIME}; }}
        QSpinBox::up-button, QSpinBox::down-button {{ width: 14px; }}
    """)
    return sb


def _add_row(layout: QVBoxLayout, label: str, widget: QWidget) -> None:
    row = QWidget()
    rl = QHBoxLayout(row)
    rl.setContentsMargins(0, 1, 0, 1)
    rl.setSpacing(6)
    rl.addWidget(_row_label(label))
    rl.addWidget(widget, stretch=1)
    layout.insertWidget(layout.count() - 1, row)


def build(layout: QVBoxLayout) -> None:
    try:
        cfg = _load()
    except Exception as e:
        lbl = QLabel(f"Error leyendo config:\n{e}")
        lbl.setStyleSheet(f"color: {RED}; font-size: 10px;")
        lbl.setWordWrap(True)
        layout.insertWidget(layout.count() - 1, lbl)
        return

    # ── TTS ──────────────────────────────────────────────────────────────────
    _section_title(layout, "TTS")
    tts_toggle = QCheckBox("Hablar respuestas")
    tts_toggle.setChecked(cfg["output"].get("tts_enabled", False))
    tts_toggle.setStyleSheet(
        f"color: {INK}; font-size: 10px; font-family: 'JetBrains Mono', monospace;"
    )
    layout.insertWidget(layout.count() - 1, tts_toggle)

    _sep(layout)

    # ── Whisper ───────────────────────────────────────────────────────────────
    _section_title(layout, "Whisper / STT")
    wh_model  = _combo(["tiny","base","small","medium","large"],
                       cfg["whisper"].get("model","small"))
    wh_lang   = _lineedit(cfg["whisper"].get("language") or "es")
    wh_lang.setMaxLength(5)
    wh_device = _combo(["cpu","cuda"], cfg["whisper"].get("device","cpu"))

    _add_row(layout, "modelo",    wh_model)
    _add_row(layout, "idioma",    wh_lang)
    _add_row(layout, "dispositivo", wh_device)

    _sep(layout)

    # ── Backend ───────────────────────────────────────────────────────────────
    _section_title(layout, "Backend")
    bk_backend = _combo(["claude","codex","opencode"],
                        cfg.get("backend","claude"))
    cl_model   = _combo(
        ["claude-haiku-4-5","claude-sonnet-4-6","claude-opus-4-7",
         "claude-haiku-3-5","claude-sonnet-3-7"],
        cfg["claude"].get("model","claude-haiku-4-5"),
    )
    _add_row(layout, "backend",   bk_backend)
    _add_row(layout, "claude model", cl_model)

    _sep(layout)

    # ── Historial ─────────────────────────────────────────────────────────────
    _section_title(layout, "Historial")
    hist_enabled = QCheckBox("Guardar historial")
    hist_enabled.setChecked(cfg["history"].get("enabled", True))
    hist_enabled.setStyleSheet(
        f"color: {INK}; font-size: 10px; font-family: 'JetBrains Mono', monospace;"
    )
    layout.insertWidget(layout.count() - 1, hist_enabled)

    hist_turns = _spinbox(cfg["history"].get("max_turns", 10), 1, 100)
    _add_row(layout, "max turnos", hist_turns)

    _sep(layout)

    # ── Save button ───────────────────────────────────────────────────────────
    status_lbl = QLabel("")
    status_lbl.setStyleSheet(f"font-size: 10px; font-family: 'JetBrains Mono', monospace;")
    status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    save_btn = QPushButton("▶ Guardar")
    save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    save_btn.setStyleSheet(f"""
        QPushButton {{
            background: rgba(136,201,58,0.12); color: {LIME};
            border: 1px solid {LIME}; border-radius: 4px;
            font-size: 10px; font-family: 'JetBrains Mono', monospace;
            padding: 5px 0;
        }}
        QPushButton:hover {{ background: rgba(136,201,58,0.22); }}
        QPushButton:pressed {{ background: rgba(136,201,58,0.35); }}
    """)

    def _on_save():
        try:
            cfg["output"]["tts_enabled"]       = tts_toggle.isChecked()
            cfg["whisper"]["model"]            = wh_model.currentText()
            cfg["whisper"]["language"]         = wh_lang.text().strip() or None
            cfg["whisper"]["device"]           = wh_device.currentText()
            cfg["backend"]                     = bk_backend.currentText()
            cfg["claude"]["model"]             = cl_model.currentText()
            cfg["history"]["enabled"]          = hist_enabled.isChecked()
            cfg["history"]["max_turns"]        = hist_turns.value()
            _save(cfg)
            status_lbl.setStyleSheet(f"color: {LIME}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
            status_lbl.setText("✓ guardado")
        except Exception as e:
            status_lbl.setStyleSheet(f"color: {RED}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
            status_lbl.setText(f"✗ {e}")

    save_btn.clicked.connect(_on_save)
    layout.insertWidget(layout.count() - 1, save_btn)
    layout.insertWidget(layout.count() - 1, status_lbl)
