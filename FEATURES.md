# Features implementadas y roadmap

## Implementado

### Core pipeline
- Grabación de audio con arecord (ALSA)
- Transcripción local con faster-whisper (modelo en memoria, sin subprocess por llamada)
- Integración con Claude CLI via OAuth (suscripción, sin costo de API)
- Notificaciones de estado con notify-send

### Modos de activación
- **Hotkey**: Right-Ctrl + ` (configurable), modo toggle o push-to-talk
- **Always-on**: wake word ("oye pepito") + VAD automático con webrtcvad
  - Queue + processor thread único (sin race conditions)
  - Fuzzy matching para wake word (difflib, tolerante a errores de Whisper)
  - Pre-roll de 500ms para no perder inicio de utterance

### Intents detectados en español
- Screenshot + análisis visual ("mira la pantalla")
- Control de volumen ("sube/baja el volumen", "volumen al X%", "silencia")
- Lectura de archivos (detección de rutas en transcripción)
- Limpiar historial ("borra el historial")

### Visión / pantalla
- Captura con spectacle (KDE Wayland) con fallback a grim (wlroots)
- Imagen enviada via Anthropic API (solo cuando hay screenshot)
- Texto normal usa Claude CLI (OAuth, sin costo)

### TTS
- piper-tts con modelo es_ES-davefx-medium (voz natural)
- Pipeline: piper → raw audio → aplay
- Strip de markdown antes de hablar (sin "asterisco asterisco")
- System prompt fuerza respuestas sin markdown/emojis

### Historial de conversación
- Últimos 10 turnos guardados en /tmp/crowia/history.json
- Contexto inyectado en llamadas al CLI como texto
- Historial completo enviado en llamadas API (vision)

### Herramientas de Claude habilitadas
- WebSearch (internet en tiempo real)
- Bash(git *) sin push
- Bash(zeditor*), Bash(alacritty*), Bash(firefox*)
- Read, Edit, Write en /home/jesusu/
- --dangerously-skip-permissions (sin prompts de confirmación)

### Audio / transcripción
- condition_on_previous_text=False (elimina alucinaciones/repeticiones)
- temperature=0 (determinístico)
- vad_filter=True (ignora silencios)
- initial_prompt con vocabulario esperado

---

## Features posibles a futuro

### Voz / TTS
- [ ] Voz más natural: kokoro-tts, coqui-tts, o edge-tts (Microsoft online)
- [ ] Interrumpir respuesta TTS al hablar de nuevo
- [ ] Indicador sonoro al activar/desactivar (beep)

### Transcripción
- [ ] Probar modelo `medium` o `large-v3-turbo` para mejor calidad
- [ ] Whisper en GPU si se añade tarjeta dedicada
- [ ] Streaming de transcripción (mostrar texto mientras se transcribe)

### Wake word
- [ ] Modelo dedicado de wake word (openwakeword) para menor latencia
- [ ] Wake word personalizado entrenado con voz propia
- [ ] Feedback visual/sonoro al detectar wake word

### Capacidades del sistema
- [ ] Control de brillo (brightnessctl)
- [ ] Control de reproducción multimedia (playerctl)
- [ ] Manejo de ventanas KDE (qdbus / wmctrl)
- [ ] Abrir URLs específicas en Firefox
- [ ] Notificaciones de calendario / recordatorios
- [ ] Integración con clipboard (wl-paste)

### Contexto / memoria
- [ ] Contexto persistente entre reinicios (no solo /tmp)
- [ ] Memoria de proyectos activos
- [ ] Perfil de usuario (preferencias, nombre, proyectos frecuentes)

### Infraestructura
- [ ] Servicio systemd habilitado y probado
- [ ] Logging rotation (logrotate)
- [ ] pyproject.toml para instalación via pip
- [ ] Rotación de API key (la actual fue expuesta en chat)
- [ ] Soporte multi-usuario (quitar paths hardcodeados)

### UX
- [ ] Overlay visual flotante con estado (grabando / procesando / respondiendo)
- [ ] Historial de conversaciones persistente con búsqueda
- [ ] Modo "proyectos" (cambiar working directory por voz)
