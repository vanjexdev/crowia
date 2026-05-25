# Giselo · Brief de Diseño para Implementación PyQt6

> **Objetivo**: Reemplazar la UI actual (asistente + launcher separados) por una **única ventana cockpit unificada**, responsive, oscura y cyberpunk, con Giselo (cuervo cyber) como protagonista y voz/cámara como modos de entrada nativos.

---

## 0. Resumen ejecutivo

Una sola `QMainWindow` con layout adaptativo. El usuario puede:
- **Hablar** o **escribir** a Giselo
- Activar la **cámara web** (PIP flotante)
- Cambiar entre **instancias** (Opencode / Claude / Codex) desde un dock superior
- Abrir **módulos** (memoria, historial, sistema, cola, notificaciones) como drawer lateral
- Alternar entre **windowed** (mín 500 px) y **fullscreen** con `Ctrl+F`

La ventana **se adapta a su ancho**: cuanto menos espacio, menos crónica visible, hasta el mínimo que es solo Giselo + ondas + input.

---

## 1. Aesthetic direction

**Cyberpunk minimalista oscuro**. No saturado, no recargado.
- Fondo profundo `#0a1020` (azul casi negro, levemente cálido)
- Acentos neón **suaves** (no fosforescentes); brillan vía `box-shadow`/`QGraphicsDropShadowEffect`
- **Scan lines** tenues sobre el fondo (apenas perceptibles)
- **Glow radial** detrás de Giselo del color de acento activo
- **Líneas finas** (1.5 px) y bordes con esquinas levemente redondeadas (4–6 px)
- Tipografía sin remates + monoespaciada para datos
- Cero gradientes pasteles, cero emoji decorativos

**Referencias mentales**: bridge de una nave (Mass Effect, No Man's Sky), HUD de Iron Man, terminal de Cursor en dark mode.

---

## 2. Design tokens

### Colores

```
/* Superficie */
--bg:           #0a1020   /* fondo principal */
--bg-grid:      rgba(200,220,255,0.04)   /* grid horizontal sutil */
--panel:        rgba(20,30,55,0.55)      /* paneles/cards */
--chrome:       rgba(10,18,40,0.65)      /* title bar + status bar */
--rail:         rgba(15,22,42,0.70)      /* side rails */

/* Texto */
--ink:          #cfd6e6   /* texto primario */
--mute:         #5d6b85   /* texto secundario */

/* Acentos (derivados de Giselo) */
--lime:         #88c93a   /* acento principal · plumas */
--cyan:         #3a9ee0   /* voz · agente */
--yellow:       #e8c33a   /* warnings · GPU */
--orange:       #e07a3a   /* usuario · alarma */
--red:          #cc4040   /* errores · estado closet */
```

**Reglas de uso del acento:**
- `lime` = estados positivos, memoria, "OK"
- `cyan` = voz, agente respondiendo, Claude
- `orange` = mensajes del usuario, advertencias suaves
- `yellow` = warnings de sistema, GPU
- `red` = errores, instancia caída

El **color de acento activo** del HUD es configurable por el usuario (`lime` por defecto). El glow radial, el botón "enviar", los rings y la status pill usan este color.

### Tipografía

| Token | Familia | Uso |
|---|---|---|
| `font-display` | `Caveat` (handwritten) | Solo en wireframes — en hi-fi usar `Space Grotesk` o `Geist Sans` |
| `font-ui` | `Inter` o `Geist Sans` | UI general |
| `font-mono` | `JetBrains Mono` | Telemetría, atajos, timestamps, IDs |

**Tamaños**: 9, 10, 11, 13, 15, 18, 22, 28 px. No usar tamaños arbitrarios fuera de esta escala.

### Espaciado

Escala 4 px: `4, 8, 12, 16, 20, 24, 32, 48`.
**Radio**: 3 / 4 / 6 px (chips, paneles, tarjetas).

### Sombras / glow

```
--glow-soft:    0 0 8px  var(--accent);
--glow-medium:  0 0 12px var(--accent);
--glow-strong:  0 0 16px var(--accent), 0 0 32px var(--accent)/50;
```

En PyQt6: `QGraphicsDropShadowEffect(blurRadius=12, color=QColor(accent), offset=(0,0))`.

---

## 3. Layout system + responsive

### Anatomía

```
┌─────────────────────────────────────────────────────────┐
│  TITLE BAR (30px) · traffic lights · "GISELO" · ⌘F      │
├──┬──────────────────────────────────────────────────┬──┤
│  │  TAB DOCK (instancias)                            │  │
│  ├──────────────────────────────────────────────────┤  │
│ R│                                                  │ R│
│ A│   ┌─── CAMERA PIP (opcional, flota) ───┐         │ A│
│ I│                                                  │ I│
│ L│        ╭──── VOICE RINGS ────╮                   │ L│
│  │        │     ╭── GISELO ──╮   │                  │  │
│ L│        │     │   (open)   │   │                  │ R│
│  │        │     ╰────────────╯   │                  │  │
│  │        ╰────────────────────╯                    │  │
│  │                                                  │  │
│  │   [chat preview cards · 2 últimos mensajes]      │  │
│  │                                                  │  │
│  │   ┌──── INPUT (escribe o habla) ──── [enviar] ┐  │  │
│  │                                                  │  │
├──┴──────────────────────────────────────────────────┴──┤
│  STATUS BAR (22px) · online · cam · voz · v0.4         │
└─────────────────────────────────────────────────────────┘
```

### Breakpoints (ancho de ventana)

| Breakpoint | Rango | Comportamiento |
|---|---|---|
| **MIN** | ≤ 620 px | Solo title bar, una pestaña de instancia, Giselo + rings + input + status bar mínima. **Rails ocultos.** Sin chat preview. PIP de cámara reducido (170×110). |
| **COMPACT** | 621 – 920 px | Aparecen los **2 rails laterales** (44 px c/u). Tabs completas. Chat preview activo. |
| **MEDIUM** | 921 – 1280 px | Rails + un **drawer** puede expandirse (260–280 px). Solo 1 drawer a la vez. |
| **LARGE** | > 1280 px | Igual que medium pero con más holgura. Drawer puede quedar pinned. |

**Altura mínima**: 600 px. Por debajo, el chat preview desaparece primero y el input se compacta.

**Implementación PyQt**: en `QMainWindow.resizeEvent()`, calcular el breakpoint y mostrar/ocultar `QWidget`s. Usar `QStackedWidget` para el chat preview (vacío vs cards). El drawer es un `QDockWidget` con `setFeatures(DockWidgetClosable | DockWidgetMovable)`.

### Reglas de proporciones

- **Voice rings**: diámetro = `min(centerWidth * 0.78, height * 0.55, 460)` px.
- **Giselo dentro de los rings**: `ringSize * 0.62`.
- **Drawer width**: `min(280, windowWidth * 0.32)`.
- **PIP cámara**: 220×135 normal, 170×110 en MIN.
- **Margen lateral del centro**: 18 px (12 en MIN).

---

## 4. Componentes

### 4.1 Title bar
- Altura **30 px**, fondo `--chrome`, borde inferior `1.5px solid --ink`.
- Izquierda: 3 traffic lights (10×10, círculo, borde 1 px `--ink`, sin relleno).
- Texto: `GISELO` en `font-display` 14 px bold + `· puente · {W}×{H}` en mono 9 px `--mute` (oculto en MIN).
- Derecha: `⌘F` mono 9 px (recordatorio de fullscreen).
- **Frameless** (`Qt.FramelessWindowHint`) + drag manual o mantener nativa según preferencia OS.

### 4.2 Tab dock (instancias)
- Posición: top: 38 px, ancho disponible entre rails.
- Cada tab: padding `5 10`, borde `1.5px solid --ink`, radio `6px 6px 0 0`.
- Dot de color (7×7, círculo) + nombre (`font-display` 13 px) + shortcut (mono 9 px `--mute`).
- **Activa**: fondo `--panel`, dot con `box-shadow: 0 0 8px {color}`, border-bottom del color `--bg` (visualmente "fusiona" con el contenido).
- Botón final: `+ instancia` con borde `dashed --mute`.
- En MIN: solo la activa + un selector compacto `⇆ N`.

### 4.3 Rails laterales (44 px)
- Borde interno de `1.5px solid --ink`, fondo `--rail`.
- Iconos en `QPushButton` 32×32, radio 6 px.
- Inactivo: borde `dashed --mute`, color `--ink`.
- Activo: borde `solid {color}`, fondo `{color}/15%`, glow del color, **flecha** apuntando al drawer (triángulo de 4 px).
- **Rail izquierdo** (módulos): `◆ Memoria · ⊟ Historial · ◑ Sistema · ⊞ Cola · ◔ Notif`, `⚙` config al pie.
- **Rail derecho** (acciones): `◉ Voz · ◐ Cámara · ⊡ Expandir · ✎ Editor`.

### 4.4 Drawer lateral
- Ancho `min(280, W*0.32)`, alto entre title bar y status bar.
- Header: título en color del módulo (`▾ MEMORIA` en lime, etc.), borde inferior `dashed {color}`, botón `×` a la derecha.
- Contenido scroll vertical.
- Solo **1 drawer abierto** a la vez.
- Implementación PyQt: `QDockWidget` con custom title bar, o `QFrame` slide-in animado con `QPropertyAnimation` sobre `geometry`.

### 4.5 Núcleo central (Giselo + rings)
- **Voice rings**: 5 anillos concéntricos en SVG, opacidad descendente `0.45 → 0.15`, dashes alternados.
- Outer ring con 24 tick marks radiales.
- En PyQt: `QGraphicsScene` con `QGraphicsEllipseItem`s + `QGraphicsItemAnimation` o un `QPainter` custom widget.
- **Giselo**: `QLabel` con `QPixmap` cargado del PNG correspondiente al estado.
- **Glow radial detrás**: `QGraphicsDropShadowEffect` con blur grande o un `QWidget` con `QRadialGradient`.
- **Status pill** flotando arriba del ring (top: -6 px): borde + texto del color de acento, fondo `--bg`, glow.
- **Spectrum** flotando abajo del ring: 24–28 barras animadas según nivel de audio (usar `QMediaCaptureSession` + `QAudioBufferInput` para leer levels).

### 4.6 Camera PIP
- 220×135 (170×110 en MIN), borde `1.5px solid --lime`, radio 6 px, glow lime.
- Flota sobre el ring (top: 80 px, centrado horizontalmente en el centro).
- Badge `● LIVE` arriba-izquierda (fondo translúcido negro, texto lime mono 9 px).
- Badge mod resolución abajo-derecha (`cam-0 720p · 30fps`, mono 8 px lime).
- Botón cerrar `×` arriba-derecha (18×18, borde 1 px lime, fondo negro 50%).
- **Implementación**: `QCameraViewfinder` (Qt5) o `QVideoWidget` con `QMediaCaptureSession` (Qt6 multimedia). Mostrar/ocultar con animación de opacidad (200 ms).

### 4.7 Chat preview (2 cards)
- Solo en breakpoints ≥ COMPACT.
- 2 tarjetas lado a lado, `flex: 1` cada una.
- Borde `1.5px solid --ink`, **border-left 3 px** del color del autor (orange = tú, cyan = giselo).
- Header: autor + timestamp (display, bold) | tipo (mono, mute).
- Body: 1 línea de texto en display 12 px.
- Chips de acciones inferiores (en cards de respuesta): `dashed --mute`, padding `1 6`.
- En PyQt: `QFrame` con stylesheet, `QHBoxLayout` interno.

### 4.8 Input bar
- Borde **grueso** `2.5px solid --ink`, radio 6 px, fondo `--panel`, padding `10 12`.
- Línea 1: placeholder `› escribe o habla...` + hint `(@ adjuntar · / comandos)` en mute italic.
- Línea 2 (controles, alineados a la derecha):
  - Hint `⌘K palette` mono 9 px mute
  - Separador vertical 1 px
  - Botón **cam** (`◐ cam`): borde y texto = lime si activo / `--ink` si inactivo
  - Botón **voz** (`◉ voz`): cyan, borde + fondo `cyan/15%`
  - Botón **adjuntar** (`📎 @`): `--ink`
  - Botón **enviar** (`enviar ↵`): borde + texto = `--accent`, fondo `--accent/15%`, glow
- Implementación: `QPlainTextEdit` para input + `QHBoxLayout` con `QToolButton`s estilizados.

### 4.9 Status bar
- Altura 22 px, fondo `--chrome`, border-top `1.5px solid --ink`.
- Items mono 9 px separados por gap 10 px:
  - `● online` (lime)
  - `opencode` (mute) — instancia activa
  - `mem 8.3k` (mute)
  - `● cam` (lime si activa, mute `○ cam` si no)
  - `voz on` (mute)
  - Derecha: `v0.4.1 · build 1789`

---

## 5. Estados de Giselo (mascota)

| Estado app | Asset | Cuándo |
|---|---|---|
| `idle` | `giselo-normal.png` | Default, esperando input. Animación: leve respiración (scale 1.0 ↔ 1.03, 3 s loop). |
| `thinking` | `giselo-thinking.png` | Mientras el agente procesa. Rings con dash animado girando lento. |
| `speaking` | `giselo-open.png` | Mientras responde / TTS activo. Spectrum bars activas, rings pulsando al nivel de audio. |
| `success` | `giselo-like.png` | Tras completar acción (200 ms flash de glow lime), vuelve a idle a los 1.5 s. |
| `error` / `off` | `giselo-closet.png` | Falla, instancia caída, o app en background. |

**Transiciones**: crossfade 250 ms entre PNGs (`QPropertyAnimation` sobre opacity de dos `QLabel` apilados).

---

## 6. Interacciones y atajos

| Atajo | Acción |
|---|---|
| `Ctrl+F` | Toggle fullscreen ↔ windowed |
| `Ctrl+Enter` | Enviar mensaje |
| `Ctrl+L` | Activar/desactivar voz |
| `Ctrl+Shift+C` | Toggle cámara |
| `Ctrl+K` | Command palette |
| `Ctrl+/` | Comandos slash |
| `Ctrl+1 / 2 / 3` | Saltar a instancia |
| `Ctrl+Shift+1..5` | Toggle drawer (memoria/historial/sistema/cola/notif) |
| `Esc` | Cerrar drawer activo |
| `@` en input | Selector de archivo/carpeta |
| `/` en input | Selector de comandos |

**Implementación**: `QShortcut` con `Qt.ApplicationShortcut` para que funcionen incluso si el focus no está en el input.

---

## 7. Animaciones / micro-interacciones

- **Voice rings**: dashes con offset animado (rotación visual sutil) cuando hay actividad. Duración 12 s loop.
- **Status pill**: pulso del glow al ritmo del audio level (escalar `boxShadow` blur 8 ↔ 14 px).
- **Drawer open/close**: slide horizontal 220 ms, easing `OutCubic`.
- **Tab switch**: fade 150 ms del contenido + glow del dot a 1.5× brevemente.
- **Camera open**: opacity 0→1 + scale 0.92→1.0, 200 ms.
- **Giselo state transition**: crossfade 250 ms.
- **Spectrum bars**: actualizar a 30 fps mientras voz activa.
- **Scan lines**: estáticas (no animadas; mover causa fatiga visual).

---

## 8. Cámara web · integración

### Qt6
- `QMediaCaptureSession` + `QCamera` + `QVideoWidget`
- El `QVideoWidget` va dentro de un `QWidget` overlay con `WA_TranslucentBackground` para los bordes redondeados con glow.
- **Privacidad**: indicador `● LIVE` siempre visible cuando la cámara está activa. Status bar muestra `● cam` en lime.
- **Permisos**: pedir con `QCamera.start()` y manejar `errorOccurred`.
- **Estados**:
  - off → no PIP, botón `◐ cam` inactivo
  - requesting → PIP placeholder con loader
  - live → PIP con feed
  - error → PIP con borde rojo + mensaje

### Uso previsto por Giselo
La cámara permite a Giselo "ver" (gestos, presencia, expresión) para:
- Pausar TTS cuando el usuario habla por gestos
- Activarse al detectar mirada (opcional, opt-in)
- Snapshots de contexto visual para enviar al modelo

---

## 9. Voz · integración

- Captura: `QMediaCaptureSession` + `QAudioBufferInput`.
- Niveles → spectrum bars (FFT cliente o magnitud RMS por barra).
- Pipeline: wake word ("hey giselo") → STT (Whisper local o servicio) → texto al input → enviar al agente de la instancia activa.
- Indicador visual: status pill arriba del ring cambia entre `● ESCUCHANDO · LVL XX%` y `● PROCESANDO`.
- TTS de respuesta: mientras suena, Giselo en estado `speaking` y rings/spectrum animados.

---

## 10. Estructura sugerida del código (PyQt6)

```
giselo/
├── main.py
├── app/
│   ├── window.py            # QMainWindow + responsive logic
│   ├── theme.py             # tokens (colors, fonts) + QSS string
│   ├── shortcuts.py         # QShortcut registry
│   └── state.py             # estado global (instancia activa, drawer, camera, ...)
├── widgets/
│   ├── title_bar.py
│   ├── tab_dock.py
│   ├── rail_left.py
│   ├── rail_right.py
│   ├── drawer.py            # QDockWidget custom
│   ├── giselo_core.py       # rings + sprite + spectrum
│   ├── camera_pip.py
│   ├── chat_preview.py
│   ├── input_bar.py
│   └── status_bar.py
├── panels/
│   ├── memoria.py
│   ├── historial.py
│   ├── sistema.py
│   ├── cola.py
│   └── notif.py
├── services/
│   ├── voice.py             # captura + STT + TTS
│   ├── camera.py            # QMediaCaptureSession wrapper
│   ├── instances.py         # Opencode/Claude/Codex bridge
│   └── memory.py            # persistencia de contexto
└── assets/
    ├── giselo-normal.png
    ├── giselo-thinking.png
    ├── giselo-open.png
    ├── giselo-like.png
    └── giselo-closet.png
```

---

## 11. Acceptance criteria (definición de "hecho")

- [ ] Una sola ventana, sin Launcher separado.
- [ ] Funciona en `windowed` (mín 500×600) y `fullscreen` con `Ctrl+F`.
- [ ] Tabs de instancia conmutan sin recargar la ventana.
- [ ] Layout cambia en los 3 breakpoints (MIN / COMPACT / MEDIUM+).
- [ ] Los 5 módulos abren/cierran como drawer (animado).
- [ ] Voz capta audio y dispara estados visuales en Giselo.
- [ ] Cámara muestra PIP con `● LIVE` y se puede cerrar.
- [ ] Los 5 estados de Giselo se ven y transicionan suavemente.
- [ ] Todos los atajos de la tabla §6 funcionan.
- [ ] Cero pop-ups extra; todo dentro de la ventana cockpit.
- [ ] Tema oscuro por defecto con glow del acento configurable (lime/cyan/orange).

---

## 12. Anti-patterns (NO hacer)

- ❌ Ventanas hijas/separadas para módulos (es lo que estamos eliminando).
- ❌ Gradientes saturados o fondos animados.
- ❌ Emojis decorativos en la UI.
- ❌ Iconografía de Material/Bootstrap genérica — usar glifos unicode simples (`◆ ⊟ ◑ ◉ ◐`) o íconos custom que coincidan con la estética.
- ❌ Bordes mayores a 2.5 px.
- ❌ Border-radius mayores a 8 px.
- ❌ Texto en sentencias largas dentro de la UI; preferir frases cortas tipo HUD.
- ❌ Modal dialogs bloqueantes; preferir drawer/inline.

---

## 13. Referencia visual

El archivo `Giselo Wireframes.html` en este proyecto muestra los 5 breakpoints lado a lado. Es la **fuente de verdad visual** para la dirección. Cualquier desviación debe ser justificada y validada.
