# TODO — Giselo

## Pendiente

### 1. Pausar audio mientras Giselo habla
- **Actual:** duck baja volumen a 25%, pero el audio sigue corriendo
- **Mejorar:** detectar si hay reproducción activa (Spotify, YouTube, etc.) y pausarla
  completamente durante TTS, reanudar al terminar
- Candidatos: `playerctl pause` / `playerctl play` (funciona con Spotify, Chromium, VLC, etc.)
- Conectar a señales `TTSService.started` → `playerctl pause` y `TTSService.finished` → `playerctl play`
- Hacer configurable: duck (actual) vs pause (nuevo)

### 2. Cancelar interacción en caso de equivocación
- **Problema:** usuario envía mensaje por error o quiere interrumpir respuesta en curso
- **Opciones:**
  - Botón "✕ cancelar" visible mientras LLM está procesando/respondiendo
  - Atajos de teclado: `Escape` cancela respuesta en curso
  - Si modo siempre-on: activar voz mientras responde = cancelar + escuchar nueva entrada
- **Lo que hay que matar:** `InstanceService` query en curso + TTS + VAD restart
- Agregar `cancel()` a `InstanceService` que termine el subprocess Claude
- Conectar al botón/shortcut en `window.py`

### 3. Otros (por definir)
- [ ] ...

---

## Completado esta sesión ✓

- [x] Audio ducking (bajar volumen apps mientras TTS)
- [x] Streaming TTS por frases (audio inicia antes de respuesta completa)
- [x] Modo siempre-on con VAD silence detection
- [x] Selector de micrófono con nombres amigables (pactl + PULSE_SOURCE)
- [x] `giselo-launch-app` — detecta si app corre, enfoca o lanza
- [x] `giselo-activate-profile` — perfiles de trabajo (PDM/Floorp)
- [x] @ picker: carpetas + reset estado al cerrar
- [x] WebSearch para queries informativas (no abre navegador)
- [x] New-tab antes de navegar (no interrumpe música)
- [x] Whisper small (menor latencia)
