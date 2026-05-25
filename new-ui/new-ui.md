# Prompt corto · para pegar al agente implementador

> Versión condensada del brief completo. Para detalle, consultar `DESIGN_BRIEF.md` y `Giselo Wireframes.html` en el mismo proyecto.

---

Eres un agente que va a reimplementar la UI de **Giselo** (asistente de voz cyberpunk) en **PyQt6**. Tu objetivo es reemplazar la UI actual (asistente + launcher en ventanas separadas) por **una sola ventana cockpit unificada, responsive y oscura**.

## Stack
- Python 3.11+
- PyQt6 + PyQt6-multimedia (cámara/audio)
- Estructura modular bajo `giselo/` (window, widgets/, panels/, services/, assets/)

## Visual

- Estética: **cyberpunk oscuro minimalista** (referencia: HUD de nave / Iron Man). NO gradientes saturados, NO emojis decorativos, NO iconografía genérica de Material.
- Fondo `#0a1020`, texto `#cfd6e6`, mute `#5d6b85`.
- Acentos neón (uso quirúrgico, con glow vía `QGraphicsDropShadowEffect`):
  - `lime #88c93a` (memoria, OK, acento default)
  - `cyan #3a9ee0` (voz, agente)
  - `yellow #e8c33a` (warning)
  - `orange #e07a3a` (usuario, alarma suave)
  - `red #cc4040` (error)
- Bordes 1.5 px solid o dashed, radios 4–6 px (nunca > 8).
- Scan lines tenues sobre el fondo + glow radial detrás de Giselo.
- Fuentes: `Geist Sans` (UI), `JetBrains Mono` (datos/atajos).

## Layout

Ventana = `QMainWindow` con **breakpoints responsive** por `resizeEvent`:

| Ancho | Modo | Visible |
|---|---|---|
| ≤ 620 | MIN | Title bar + 1 tab + Giselo + rings + input + status bar |
| 621–920 | COMPACT | + 2 rails laterales (44 px) + chat preview |
| > 920 | MEDIUM/LARGE | + drawer lateral expandible (1 a la vez, 260–280 px) |

Mínimo 500×600. Toggle fullscreen con `Ctrl+F`.

**Anatomía vertical** (top → bottom):
1. Title bar 30 px (traffic lights + "GISELO" + ⌘F)
2. Tab dock (instancias: Opencode/Claude/Codex/+)
3. Centro: Giselo + voice rings (5 anillos SVG/QPainter) + status pill + spectrum
4. Chat preview (2 cards, solo ≥ COMPACT)
5. Input bar (placeholder + botones cam/voz/adjuntar/enviar)
6. Status bar 22 px (online · instancia · mem · cam · voz · versión)

**Rails laterales:**
- Izquierdo: `◆ Memoria · ⊟ Historial · ◑ Sistema · ⊞ Cola · ◔ Notif · ⚙`
- Derecho: `◉ Voz · ◐ Cámara · ⊡ Expandir · ✎ Editor`
- Click en icono → abre/cierra drawer correspondiente (animado, 220 ms OutCubic).

## Giselo (mascota)

5 assets PNG ya existen en `assets/`:
- `idle` → `giselo-normal.png` (respiración sutil 1.0↔1.03)
- `thinking` → `giselo-thinking.png` (rings con dash girando)
- `speaking` → `giselo-open.png` (rings + spectrum reaccionan al audio)
- `success` → `giselo-like.png` (flash lime 1.5 s)
- `error` / `off` → `giselo-closet.png`

Transición entre estados: **crossfade 250 ms** (dos `QLabel` apilados con `QPropertyAnimation` sobre opacity).

Tamaño dentro del ring: `ringSize * 0.62`. Ring size: `min(centerW*0.78, H*0.55, 460)`.

## Voz

- `QMediaCaptureSession` + `QAudioBufferInput`.
- Calcular RMS por frame → animar spectrum (24–28 barras).
- Wake word "hey giselo" → STT → texto en input → enviar a instancia activa.
- Status pill arriba del ring: `● ESCUCHANDO · LVL XX%` / `● PROCESANDO`.

## Cámara

- `QMediaCaptureSession` + `QCamera` + `QVideoWidget`.
- **PIP flotante** sobre las ondas, 220×135 (170×110 en MIN), borde `1.5px solid lime`, glow lime.
- Badge `● LIVE` (top-left) y resolución (`cam-0 720p · 30fps`, bottom-right).
- Botón `×` (top-right) para cerrar.
- Toggle con `Ctrl+Shift+C` o botón `◐ cam` del rail derecho.
- Indicador `● cam` en status bar siempre visible cuando está activa.

## Instancias

3 instancias preconfiguradas: **Opencode**, **Claude**, **Codex**. Dock superior tipo pestañas con:
- Dot de color (lime/cyan/orange) + nombre + shortcut (`⌃⇧1`, `⌃\``, `⌃⇧⌥1`).
- Activa: fondo `--panel`, dot con glow, border-bottom fusionado con el contenido.
- Botón `+ instancia` al final.
- Conmutación NO recarga ventana — solo cambia el contexto del input/chat.

## Atajos (todos globales con `Qt.ApplicationShortcut`)

```
Ctrl+F              fullscreen ↔ windowed
Ctrl+Enter          enviar
Ctrl+L              toggle voz
Ctrl+Shift+C        toggle cámara
Ctrl+K              command palette
Ctrl+/              comandos slash
Ctrl+1/2/3          saltar a instancia
Ctrl+Shift+1..5     toggle drawer (memoria/historial/sistema/cola/notif)
Esc                 cerrar drawer activo
```

## Reglas estrictas

- ❌ NUNCA ventanas hijas separadas para módulos.
- ❌ NUNCA gradientes saturados o pasteles.
- ❌ NUNCA emojis decorativos en la UI.
- ❌ NUNCA modal dialogs bloqueantes (preferir drawer/inline).
- ❌ NUNCA bordes > 2.5 px ni radios > 8 px.
- ✅ Todo dentro de la ventana cockpit.
- ✅ Indicadores de privacidad visibles cuando cámara/voz activos.
- ✅ Layout debe colapsar limpiamente al mínimo de 500 px.

## Entregables

1. `giselo/` con estructura modular como en `DESIGN_BRIEF.md §10`.
2. `main.py` ejecutable: `python -m giselo`.
3. Tema oscuro por defecto, acento `lime`.
4. Los 5 estados de Giselo conmutan vía API: `window.set_giselo_state('thinking')`.
5. README breve con cómo correr + dependencias.

## Referencia visual

El archivo `Giselo Wireframes.html` en el proyecto muestra los **5 breakpoints lado a lado** (MIN, MIN+cam, COMPACT, MEDIUM+drawer, FULLSCREEN). Es la fuente de verdad — si tu implementación se desvía, justifícalo.
