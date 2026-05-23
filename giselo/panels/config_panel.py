import pathlib
from ruamel.yaml import YAML
from PyQt6.QtWidgets import (QLabel, QVBoxLayout, QHBoxLayout, QComboBox,
                              QCheckBox, QLineEdit, QPushButton, QFrame,
                              QWidget, QSpinBox, QRadioButton, QButtonGroup)
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


def _rb_style() -> str:
    return f"color: {INK}; font-size: 10px; font-family: 'JetBrains Mono', monospace;"


def _radio_h(options: list[str], current: str):
    """Horizontal radio group. Returns (widget, getter_fn)."""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    group = QButtonGroup(w)
    buttons: list[QRadioButton] = []
    for opt in options:
        rb = QRadioButton(opt)
        rb.setChecked(opt == current)
        rb.setStyleSheet(_rb_style())
        group.addButton(rb)
        lay.addWidget(rb)
        buttons.append(rb)
    def get():
        for rb in buttons:
            if rb.isChecked():
                return rb.text()
        return current
    return w, get


def _radio_v(options: list[tuple[str, str]], current_val: str):
    """Vertical radio group with (display, value) pairs. Returns (widget, getter_fn)."""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 2, 0, 2)
    lay.setSpacing(2)
    group = QButtonGroup(w)
    buttons: list[tuple[QRadioButton, str]] = []
    for display, val in options:
        rb = QRadioButton(display)
        rb.setChecked(val == current_val)
        rb.setStyleSheet(_rb_style())
        group.addButton(rb)
        lay.addWidget(rb)
        buttons.append((rb, val))
    def get():
        for rb, val in buttons:
            if rb.isChecked():
                return val
        return current_val
    return w, get


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
    piper_dir = pathlib.Path.home() / ".local/share/piper"
    voices = []
    for f in sorted(piper_dir.glob("*.onnx")):
        voices.append((f.stem, str(f)))
    return voices or [("(ninguna instalada)", "")]


def _list_input_devices() -> list[tuple[str, str]]:
    """Return [(display_name, sounddevice_key)]."""
    card_desc: dict[int, str] = {}
    via_pipewire: list[tuple[str, str]] = []
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
                display = "PipeWire  -  predeterminado del sistema"
            elif sd_name == "pulse":
                display = "PulseAudio  -  predeterminado del sistema"
            else:
                m = _re.search(r'\(hw:(\d+)', sd_name)
                if m and int(m.group(1)) in card_desc:
                    display = f"{card_desc[int(m.group(1))]}  (hw:{m.group(1)})"
                else:
                    display = sd_name
            items.append((display, sd_name))
    except Exception:
        pass

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

    # ── Perfil / Persona ──────────────────────────────────────────────────────
    _section_title(layout, "Perfil")
    _asst = cfg.get("assistant", {})
    asst_gender_w, get_asst_gender = _radio_h(["male", "female"], _asst.get("gender", "male"))
    asst_name_male   = _lineedit(_asst.get("name_male",   "Giselo"))
    asst_name_female = _lineedit(_asst.get("name_female", "Giseth"))
    _add_row(layout, "genero",    asst_gender_w)
    _add_row(layout, "nombre M",  asst_name_male)
    _add_row(layout, "nombre F",  asst_name_female)

    _sep(layout)

    # ── Micrófono ─────────────────────────────────────────────────────────────
    _section_title(layout, "Microfono")
    mic_devices = _list_input_devices()
    current_mic = cfg.get("audio", {}).get("monitor_device", "default")

    _combo_style = f"""
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
    """
    mic_combo = QComboBox()
    mic_combo.setStyleSheet(_combo_style)
    mic_combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    for display, key in mic_devices:
        mic_combo.addItem(display, userData=key)
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
    tts_toggle.setStyleSheet(_rb_style())
    layout.insertWidget(layout.count() - 1, tts_toggle)

    tts_voices = _list_piper_voices()
    _tts_cmd = cfg["output"].get("tts_command", [])
    _current_model = next((s for s in _tts_cmd if s.endswith(".onnx")), "")
    tts_voice_w, get_tts_voice = _radio_v(tts_voices, _current_model)
    _add_row(layout, "voz", tts_voice_w)

    _sep(layout)

    # ── ElevenLabs ───────────────────────────────────────────────────────────
    _section_title(layout, "ElevenLabs TTS")
    _el = cfg.get("elevenlabs", {})
    el_toggle = QCheckBox("Usar ElevenLabs (reemplaza Piper)")
    el_toggle.setChecked(_el.get("enabled", False))
    el_toggle.setStyleSheet(_rb_style())
    layout.insertWidget(layout.count() - 1, el_toggle)
    el_apikey = _lineedit(_el.get("api_key", ""))
    el_apikey.setEchoMode(el_apikey.EchoMode.Password)
    el_voiceid = _lineedit(_el.get("voice_id", ""))
    _add_row(layout, "api key",  el_apikey)
    _add_row(layout, "voice id", el_voiceid)

    _sep(layout)

    # ── Whisper ───────────────────────────────────────────────────────────────
    _section_title(layout, "Whisper / STT")
    wh_model_w, get_wh_model = _radio_h(
        ["tiny", "base", "small", "medium", "large"],
        cfg["whisper"].get("model", "small"),
    )
    wh_lang = _lineedit(cfg["whisper"].get("language") or "es")
    wh_lang.setMaxLength(5)
    wh_device_w, get_wh_device = _radio_h(
        ["cpu", "cuda"],
        cfg["whisper"].get("device", "cpu"),
    )
    _add_row(layout, "modelo",      wh_model_w)
    _add_row(layout, "idioma",      wh_lang)
    _add_row(layout, "dispositivo", wh_device_w)

    _sep(layout)

    # ── Skills ───────────────────────────────────────────────────────────────
    _section_title(layout, "Skills")
    _skills_dir = pathlib.Path(__file__).parents[2] / "skills"
    _available_skills = sorted(p.stem for p in _skills_dir.glob("*.md")) if _skills_dir.exists() else []
    _enabled_skills = list(cfg.get("skills", {}).get("enabled", []))
    skill_checks: dict[str, QCheckBox] = {}
    for sk in _available_skills:
        cb = QCheckBox(sk)
        cb.setChecked(sk in _enabled_skills)
        cb.setStyleSheet(_rb_style())
        layout.insertWidget(layout.count() - 1, cb)
        skill_checks[sk] = cb

    _sep(layout)

    # ── Backend (instancia activa) ────────────────────────────────────────────
    from giselo.app.state import state
    instance = state.active_instance
    backend  = state.INSTANCE_BACKENDS.get(instance, instance)

    _section_title(layout, f"Instancia: {instance} ({backend})")

    backend_widgets: dict = {}

    if backend == "claude":
        _cl_current = cfg["claude"].get("model", "claude-haiku-4-5")
        cl_model_w, get_cl_model = _radio_v(
            [("haiku-4-5",   "claude-haiku-4-5"),
             ("sonnet-4-6",  "claude-sonnet-4-6"),
             ("opus-4-7",    "claude-opus-4-7"),
             ("haiku-3-5",   "claude-haiku-3-5"),
             ("sonnet-3-7",  "claude-sonnet-3-7")],
            _cl_current,
        )
        _add_row(layout, "modelo", cl_model_w)
        backend_widgets["get_cl_model"] = get_cl_model

    elif backend == "codex":
        cx_model = _lineedit(cfg["codex"].get("model") or "")
        cx_model.setPlaceholderText("dejar vacio = default")
        cx_sandbox_w, get_cx_sandbox = _radio_v(
            [("read-only",          "read-only"),
             ("workspace-write",    "workspace-write"),
             ("danger-full-access", "danger-full-access")],
            cfg["codex"].get("sandbox", "danger-full-access"),
        )
        cx_workdir = _lineedit(cfg["codex"].get("working_dir") or "")
        cx_workdir.setPlaceholderText("vacio = dir del archivo")
        _add_row(layout, "modelo",   cx_model)
        _add_row(layout, "sandbox",  cx_sandbox_w)
        _add_row(layout, "work dir", cx_workdir)
        backend_widgets.update(cx_model=cx_model, get_cx_sandbox=get_cx_sandbox,
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
    hist_enabled.setStyleSheet(_rb_style())
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
            cfg["output"]["tts_enabled"] = tts_toggle.isChecked()

            # Update tts_command model path
            _new_model = get_tts_voice()
            if _new_model and "tts_command" in cfg["output"]:
                _cmd = list(cfg["output"]["tts_command"])
                for i, part in enumerate(_cmd):
                    if str(part).endswith(".onnx"):
                        _cmd[i] = _new_model
                        break
                cfg["output"]["tts_command"] = _cmd

            cfg["whisper"]["model"]    = get_wh_model()
            cfg["whisper"]["language"] = wh_lang.text().strip() or None
            cfg["whisper"]["device"]   = get_wh_device()
            cfg["history"]["enabled"]  = hist_enabled.isChecked()
            cfg["history"]["max_turns"] = hist_turns.value()

            if backend == "claude" and "get_cl_model" in backend_widgets:
                cfg["claude"]["model"] = backend_widgets["get_cl_model"]()
            elif backend == "codex":
                cfg["codex"]["model"]       = backend_widgets["cx_model"].text().strip()
                cfg["codex"]["sandbox"]     = backend_widgets["get_cx_sandbox"]()
                cfg["codex"]["working_dir"] = backend_widgets["cx_workdir"].text().strip()
            elif backend == "opencode":
                cfg["opencode"]["model"] = backend_widgets["oc_model"].text().strip()

            # Skills
            if "skills" not in cfg:
                cfg["skills"] = {}
            cfg["skills"]["enabled"] = [sk for sk, cb in skill_checks.items() if cb.isChecked()]

            # ElevenLabs
            if "elevenlabs" not in cfg:
                cfg["elevenlabs"] = {}
            cfg["elevenlabs"]["enabled"]  = el_toggle.isChecked()
            cfg["elevenlabs"]["api_key"]  = el_apikey.text().strip()
            cfg["elevenlabs"]["voice_id"] = el_voiceid.text().strip()

            # Persona
            if "assistant" not in cfg:
                cfg["assistant"] = {}
            cfg["assistant"]["gender"]      = get_asst_gender()
            cfg["assistant"]["name_male"]   = asst_name_male.text().strip()   or "Giselo"
            cfg["assistant"]["name_female"] = asst_name_female.text().strip() or "Giseth"

            _save(cfg)
            status_lbl.setStyleSheet(f"color: {LIME}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
            status_lbl.setText("✓ guardado")
        except Exception as e:
            status_lbl.setStyleSheet(f"color: {RED}; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
            status_lbl.setText(f"✗ {e}")

    save_btn.clicked.connect(_on_save)
    layout.insertWidget(layout.count() - 1, save_btn)
    layout.insertWidget(layout.count() - 1, status_lbl)
