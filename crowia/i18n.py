_lang: str = "es"

_STRINGS: dict[str, dict[str, str]] = {
    "es": {
        # TextInputPanel
        "input_placeholder": "Escribe tu mensaje… @ para adjuntar archivo/carpeta",
        "send_btn": "Enviar ↩",
        "memory_btn": "💾 Memoria",
        "export_btn": "📋 Exportar",
        "pick_file": "📄 Archivo",
        "pick_folder": "📁 Carpeta",
        # PrefsDialog
        "prefs_title": "Giselo — Preferencias",
        "prefs_backend_label": "Backend activo:",
        "prefs_scale_label": "Escala de interfaz (requiere reinicio):",
        "prefs_language_label": "Idioma / Language:",
        "prefs_show_text": "Mostrar respuesta en texto",
        "prefs_tts": "Activar respuesta por voz (TTS)",
        "prefs_markdown": "Renderizar markdown en respuesta",
        "prefs_markdown_tip": "pip install markdown para habilitar",
        "prefs_hotkey_label": "Hotkey (nombres evdev, separados por coma):",
        "prefs_hotkey_placeholder": "ej: KEY_RIGHTCTRL,KEY_GRAVE",
        "prefs_hotkey_hint": "Teclas: KEY_RIGHTCTRL, KEY_LEFTALT, KEY_GRAVE, KEY_F1…F12, KEY_1…KEY_0",
        "prefs_hotkey_invalid": "Desconocidas: {keys}",
        "prefs_hotkey_empty": "Ingresa al menos una tecla.",
        # Tooltips
        "tooltip_cancel": "Cancelar",
        "tooltip_skip": "Saltar audio",
        "tooltip_tts": "Activar/desactivar voz",
        "tooltip_layout": "Cambiar orientación",
        "tooltip_panel": "Mostrar/ocultar panel",
        # Context menu
        "menu_hide_text": "Ocultar texto de respuesta",
        "menu_show_text": "Mostrar texto de respuesta",
        "menu_mute_voice": "Silenciar voz",
        "menu_unmute_voice": "Activar voz",
        "menu_prefs": "Preferencias…",
        "menu_clear_chat": "Limpiar chat",
        "menu_hide": "Ocultar",
        "menu_quit": "Salir",
        # Chat labels
        "chat_user": "Tú",
        "chat_assistant": "Giselo",
        # File preview
        "preview_lines": "… ({n} líneas)",
        # crowia.py messages
        "audio_disabled": "Audio desactivado.",
        "audio_enabled": "Audio activado.",
        "history_cleared": "Historial borrado.",
        "scale_saved": "Escala guardada ({pct}%). Reinicia Giselo para aplicar.",
        "lang_saved": "Idioma guardado. Reinicia Giselo para aplicar completamente.",
        "transcribing": "Transcribiendo…",
        "nothing_heard": "No se escuchó nada.",
        "taking_screenshot": "Capturando pantalla…",
        "asking_backend": "Preguntando a {backend}: {text}…",
        "thinking": "⏳ Pensando…",
        "no_history_memory": "No hay historial que recordar.",
        "memory_saved": "Memoria guardada: {name}",
        "no_history_export": "No hay historial que exportar.",
        "exported": "Exportado: {path}",
        # assistant.py messages
        "backend_not_found": "Backend '{name}' no disponible. Registrados: {list}",
        "backend_switched": "Ahora uso {name}.",
        "all_rate_limited": "[crowia] Todos los backends alcanzaron su límite. Sin respuesta.",
        "failover_prefix": "[Límite alcanzado en {old}, respondiendo con {new}]",
        "skill_not_found": "Skill '{name}' no encontrada. Disponibles: {list}",
        "skill_already_on": "Skill '{name}' ya estaba activa.",
        "skill_enabled": "Skill '{name}' activada.",
        "skill_already_off": "Skill '{name}' ya estaba desactivada.",
        "skill_disabled": "Skill '{name}' desactivada.",
        "skills_list": "Skills activas: {enabled}. Desactivadas: {disabled}.",
        "skills_none": "ninguna",
        # System prompt language instruction
        "lang_instruction": "Responde siempre en español.",
        # Whisper
        "whisper_lang": "es",
        "whisper_initial_prompt": "Giselo, oye giselo, hey giselo, abre Firefox, abre la terminal, busca, qué es, cómo se hace, mira la pantalla, sube el volumen, baja el volumen.",
        # Launcher
        "launcher_title": "Giselo Launcher",
        "launcher_create_btn": "+ Crear instancia",
        "launcher_empty": "Sin instancias. Haz clic en '+ Crear instancia'.",
        "launcher_dialog_new": "Nueva instancia",
        "launcher_dialog_edit": "Editar instancia",
        "launcher_name_placeholder": "Ej: Claude Principal",
        "launcher_name_label": "Nombre:",
        "launcher_backend_label": "Backend:",
        "launcher_hotkey_label": "Hotkey:",
        "launcher_hotkey_hint": "Selecciona una combinación o escribe teclas evdev separadas por coma.",
        "launcher_hotkey_empty_error": "El hotkey no puede estar vacío.",
        "launcher_btn_start": "Iniciar",
        "launcher_btn_stop": "Detener",
        "launcher_btn_delete": "Eliminar",
    },
    "en": {
        # TextInputPanel
        "input_placeholder": "Type your message… @ to attach file/folder",
        "send_btn": "Send ↩",
        "memory_btn": "💾 Memory",
        "export_btn": "📋 Export",
        "pick_file": "📄 File",
        "pick_folder": "📁 Folder",
        # PrefsDialog
        "prefs_title": "Giselo — Preferences",
        "prefs_backend_label": "Active backend:",
        "prefs_scale_label": "UI scale (requires restart):",
        "prefs_language_label": "Idioma / Language:",
        "prefs_show_text": "Show response text",
        "prefs_tts": "Enable voice response (TTS)",
        "prefs_markdown": "Render markdown in response",
        "prefs_markdown_tip": "pip install markdown to enable",
        "prefs_hotkey_label": "Hotkey (evdev names, comma-separated):",
        "prefs_hotkey_placeholder": "e.g. KEY_RIGHTCTRL,KEY_GRAVE",
        "prefs_hotkey_hint": "Keys: KEY_RIGHTCTRL, KEY_LEFTALT, KEY_GRAVE, KEY_F1…F12, KEY_1…KEY_0",
        "prefs_hotkey_invalid": "Unknown: {keys}",
        "prefs_hotkey_empty": "Enter at least one key.",
        # Tooltips
        "tooltip_cancel": "Cancel",
        "tooltip_skip": "Skip audio",
        "tooltip_tts": "Toggle voice",
        "tooltip_layout": "Toggle layout",
        "tooltip_panel": "Show/hide panel",
        # Context menu
        "menu_hide_text": "Hide response text",
        "menu_show_text": "Show response text",
        "menu_mute_voice": "Mute voice",
        "menu_unmute_voice": "Unmute voice",
        "menu_prefs": "Preferences…",
        "menu_clear_chat": "Clear chat",
        "menu_hide": "Hide",
        "menu_quit": "Quit",
        # Chat labels
        "chat_user": "You",
        "chat_assistant": "Giselo",
        # File preview
        "preview_lines": "… ({n} lines)",
        # crowia.py messages
        "audio_disabled": "Audio disabled.",
        "audio_enabled": "Audio enabled.",
        "history_cleared": "History cleared.",
        "scale_saved": "Scale saved ({pct}%). Restart Giselo to apply.",
        "lang_saved": "Language saved. Restart Giselo to fully apply.",
        "transcribing": "Transcribing…",
        "nothing_heard": "Nothing heard.",
        "taking_screenshot": "Taking screenshot…",
        "asking_backend": "Asking {backend}: {text}…",
        "thinking": "⏳ Thinking…",
        "no_history_memory": "No history to save.",
        "memory_saved": "Memory saved: {name}",
        "no_history_export": "No history to export.",
        "exported": "Exported: {path}",
        # assistant.py messages
        "backend_not_found": "Backend '{name}' not available. Registered: {list}",
        "backend_switched": "Now using {name}.",
        "all_rate_limited": "[crowia] All backends rate-limited. No response.",
        "failover_prefix": "[Rate limit on {old}, responding with {new}]",
        "skill_not_found": "Skill '{name}' not found. Available: {list}",
        "skill_already_on": "Skill '{name}' was already active.",
        "skill_enabled": "Skill '{name}' activated.",
        "skill_already_off": "Skill '{name}' was already inactive.",
        "skill_disabled": "Skill '{name}' deactivated.",
        "skills_list": "Active skills: {enabled}. Inactive: {disabled}.",
        "skills_none": "none",
        # System prompt language instruction
        "lang_instruction": "Always respond in English.",
        # Whisper
        "whisper_lang": "en",
        "whisper_initial_prompt": "Giselo, hey Giselo, open Firefox, open terminal, search, what is, how to, look at screen, volume up, volume down.",
        # Launcher
        "launcher_title": "Giselo Launcher",
        "launcher_create_btn": "+ Create instance",
        "launcher_empty": "No instances. Click '+ Create instance'.",
        "launcher_dialog_new": "New instance",
        "launcher_dialog_edit": "Edit instance",
        "launcher_name_placeholder": "E.g. Claude Main",
        "launcher_name_label": "Name:",
        "launcher_backend_label": "Backend:",
        "launcher_hotkey_label": "Hotkey:",
        "launcher_hotkey_hint": "Select a combination or type evdev keys separated by comma.",
        "launcher_hotkey_empty_error": "Hotkey cannot be empty.",
        "launcher_btn_start": "Start",
        "launcher_btn_stop": "Stop",
        "launcher_btn_delete": "Delete",
    },
}

_LANG_OPTIONS = [
    ("Español", "es"),
    ("English", "en"),
]


def set_lang(lang: str) -> None:
    global _lang
    _lang = lang if lang in _STRINGS else "es"


def get_lang() -> str:
    return _lang


def t(key: str, **kwargs) -> str:
    s = _STRINGS.get(_lang, _STRINGS["es"]).get(key)
    if s is None:
        s = _STRINGS["es"].get(key, key)
    if kwargs:
        s = s.format(**kwargs)
    return s
