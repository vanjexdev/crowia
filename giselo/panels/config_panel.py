import pathlib
from ruamel.yaml import YAML
from PyQt6.QtWidgets import (QLabel, QVBoxLayout, QHBoxLayout, QComboBox,
                              QCheckBox, QLineEdit, QPushButton, QFrame,
                              QWidget, QSpinBox)
from PyQt6.QtCore import Qt
from giselo.app.theme import LIME, CYAN, ORANGE, MUTE, INK, RED, CHROME

CONFIG_PATH = pathlib.Path(__file__).parents[2] / "config.yaml"
_yaml = YAML()
_yaml.preserve_quotes = True


def _load() -> dict:
    return _yaml.load(CONFIG_PATH.read_text(encoding="utf-8"))


def _save(cfg) -> None:
    import io
    buf = io.StringIO()
    _yaml.dump(cfg, buf)
    CONFIG_PATH.write_text(buf.getvalue(), encoding="utf-8")


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


def _list_piper_voices() -> list[tuple[str, str]]:
    """Return [(display_name, model_path)] for every .onnx in ~/.local/share/piper/."""
    import pathlib
    piper_dir = pathlib.Path.home() / ".local/share/piper"
    voices = []
    for f in sorted(piper_dir.glob("*.onnx")):
        display = f.stem  # e.g. es_ES-davefx-medium
        voices.append((display, str(f)))
    return voices or [("(ninguna instalada)", "")]


def _list_input_devices() -> list[tuple[str, str]]:
    """Return [(display_name, sounddevice_key)].
    Uses pactl alsa.card to map hw:X device names to friendly descriptions.
    Webcam/Bluetooth only reachable via 'pipewire' device.
    """
    # Parse pactl sources: build card_desc (alsa card→desc) + via_pipewire (non-ALSA sources)
    card_desc: dict[int, str] = {}
    via_pipewire: list[tuple[str, str]] = []  # (display, pactl_source_name)
    try:
        import subprocess, re as _re
        r = subprocess.run(["pactl", "list", "sources"],
                           capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            name = desc = card = None
            for line in r.stdout.splitlines():
                s = line.strip()
                if _re.match(r'Name:', s):
                    name = s.split(":", 1)[1].strip()
                elif _re.match(r'Description:', s):
                    desc = s.split(":", 1)[1].strip()
                elif _re.match(r'alsa\.card\s*=', s):
                    m = _re.search(r'"(\d+)"', s)
                    if m:
                        card = int(m.group(1))
                elif s == "" and name:
                    if not name.endswith(".monitor") and desc and "Monitor of" not in desc:
                        if card is not None:
                            card_desc[card] = desc
                        else:
                            # Bluetooth, USB-audio not exposed as ALSA card → via PipeWire
                            kind = "bluetooth" if name.startswith("bluez_") else "usb"
                            via_pipewire.append((f"{desc}  ({kind}, via PipeWire)", name))
                    name = desc = card = None
    except Exception:
        pass

    items: list[tuple[str, str]] = [("default (sistema)", "default")]
    try:
        import sounddevice as sd, re as _re
        seen: set[str] = set()
        for d in sd.query_devices():
            if d["max_input_channels"] <= 0:
                continue
            sd_name = d["name"]
            if sd_name in seen or sd_name in ("default", "sysdefault"):
                continue
            seen.add(sd_name)
            if sd_name == "pipewire":
                display = "PipeWire  –  predeterminado del sistema"
            elif sd_name == "pulse":
                display = "PulseAudio  –  predeterminado del sistema"
            else:
                m = _re.search(r'\(hw:(\d+)', sd_name)
                if m and int(m.group(1)) in card_desc:
                    display = f"{card_desc[int(m.group(1))]}  (hw:{m.group(1)})"
                else:
                    display = sd_name
            items.append((display, sd_name))
    except Exception:
        pass

    # Append specific Bluetooth/USB devices (accessed via PULSE_SOURCE trick)
    for display, pactl_name in via_pipewire:
        items.append((display, pactl_name))

    return items


def build(layout: QVBoxLayout) -> None:
    try:
        cfg = _load()
    except Exception as e:
        lbl = QLabel(f"Error leyendo config:\n{e}")
        lbl.setStyleSheet(f"color: {RED}; font-size: 10px;")
        lbl.setWordWrap(True)
        layout.insertWidget(layout.count() - 1, lbl)
        return

    # ── Micrófono ─────────────────────────────────────────────────────────────
    _section_title(layout, "Micrófono")
    mic_devices  = _list_input_devices()           # [(display, key), ...]
    current_mic  = cfg.get("audio", {}).get("monitor_device", "default")

    mic_combo = QComboBox()
    mic_combo.setStyleSheet(f"""
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
    for display, key in mic_devices:
        mic_combo.addItem(display, userData=key)
    # Select current saved device
    for i in range(mic_combo.count()):
        if mic_combo.itemData(i) == current_mic:
            mic_combo.setCurrentIndex(i)
            break

    _add_row(layout, "dispositivo", mic_combo)

    _sep(layout)

    # ── TTS ──────────────────────────────────────────────────────────────────
    _section_title(layout, "TTS")
    tts_toggle = QCheckBox("Hablar respuestas")
    tts_toggle.setChecked(cfg["output"].get("tts_enabled", False))
    tts_toggle.setStyleSheet(
        f"color: {INK}; font-size: 10px; font-family: 'JetBrains Mono', monospace;"
    )
    layout.insertWidget(layout.count() - 1, tts_toggle)

    # Voice selector
    tts_voices = _list_piper_voices()
    # detect current model path from tts_command list
    _tts_cmd = cfg["output"].get("tts_command", [])
    _current_model = next(
        (s for s in _tts_cmd if s.endswith(".onnx")), ""
    )
    tts_voice_combo = QComboBox()
    tts_voice_combo.setStyleSheet(f"""
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
    for display, path in tts_voices:
        tts_voice_combo.addItem(display, userData=path)
    for i in range(tts_voice_combo.count()):
        if tts_voice_combo.itemData(i) == _current_model:
            tts_voice_combo.setCurrentIndex(i)
            break
    _add_row(layout, "voz", tts_voice_combo)

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

    # ── Backend (instancia activa) ────────────────────────────────────────────
    from giselo.app.state import state
    instance = state.active_instance
    backend  = state.INSTANCE_BACKENDS.get(instance, instance)

    _section_title(layout, f"Instancia: {instance} ({backend})")

    backend_widgets: dict = {}

    if backend == "claude":
        cl_model = _combo(
            ["claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-7",
             "claude-haiku-3-5", "claude-sonnet-3-7"],
            cfg["claude"].get("model", "claude-haiku-4-5"),
        )
        _add_row(layout, "modelo", cl_model)
        backend_widgets["cl_model"] = cl_model

    elif backend == "codex":
        cx_model   = _lineedit(cfg["codex"].get("model") or "")
        cx_model.setPlaceholderText("dejar vacío = default")
        cx_sandbox = _combo(
            ["read-only", "workspace-write", "danger-full-access"],
            cfg["codex"].get("sandbox", "danger-full-access"),
        )
        cx_workdir = _lineedit(cfg["codex"].get("working_dir") or "")
        cx_workdir.setPlaceholderText("vacío = dir del archivo")
        _add_row(layout, "modelo",    cx_model)
        _add_row(layout, "sandbox",   cx_sandbox)
        _add_row(layout, "work dir",  cx_workdir)
        backend_widgets.update(cx_model=cx_model, cx_sandbox=cx_sandbox,
                               cx_workdir=cx_workdir)

    elif backend == "opencode":
        oc_model = _lineedit(cfg["opencode"].get("model", ""))
        _add_row(layout, "modelo", oc_model)
        backend_widgets["oc_model"] = oc_model

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
            if "audio" not in cfg:
                cfg["audio"] = {}
            cfg["audio"]["monitor_device"] = mic_combo.currentData()
            cfg["output"]["tts_enabled"]  = tts_toggle.isChecked()
            # Update tts_command model path
            _new_model = tts_voice_combo.currentData()
            if _new_model and "tts_command" in cfg["output"]:
                _cmd = list(cfg["output"]["tts_command"])
                for i, part in enumerate(_cmd):
                    if str(part).endswith(".onnx"):
                        _cmd[i] = _new_model
                        break
                cfg["output"]["tts_command"] = _cmd
            cfg["whisper"]["model"]       = wh_model.currentText()
            cfg["whisper"]["language"]    = wh_lang.text().strip() or None
            cfg["whisper"]["device"]      = wh_device.currentText()
            cfg["history"]["enabled"]     = hist_enabled.isChecked()
            cfg["history"]["max_turns"]   = hist_turns.value()

            if backend == "claude" and "cl_model" in backend_widgets:
                cfg["claude"]["model"] = backend_widgets["cl_model"].currentText()
            elif backend == "codex":
                cfg["codex"]["model"]       = backend_widgets["cx_model"].text().strip()
                cfg["codex"]["sandbox"]     = backend_widgets["cx_sandbox"].currentText()
                cfg["codex"]["working_dir"] = backend_widgets["cx_workdir"].text().strip()
            elif backend == "opencode":
                cfg["opencode"]["model"] = backend_widgets["oc_model"].text().strip()

            _save(cfg)
            status_lbl.setStyleSheet(f"color: {LIME}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
            status_lbl.setText("✓ guardado")
        except Exception as e:
            status_lbl.setStyleSheet(f"color: {RED}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
            status_lbl.setText(f"✗ {e}")

    save_btn.clicked.connect(_on_save)
    layout.insertWidget(layout.count() - 1, save_btn)
    layout.insertWidget(layout.count() - 1, status_lbl)
