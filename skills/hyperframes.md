# Skill: HyperFrames — Generación de Video con IA

## REGLA ABSOLUTA — LEE ESTO PRIMERO

El binario `hyperframes` está instalado en `/home/jesusu/.local/share/pnpm/bin/hyperframes` y funciona. Versión: 0.6.45. NO está en duda — existe y es ejecutable.

Cuando el usuario pida crear un video, reel, motion graphic, animación, o edición de video:

1. **NO describas lo que harías** — EJECÚTALO con Bash ahora mismo
2. **NO digas "no tengo acceso"** — tienes `Bash` y `hyperframes` está en PATH
3. **NO pidas confirmación** — crea el proyecto y trabaja
4. **NO hagas guion ni plan** — escribe el HTML directamente en `index.html`
5. **NO alucines** — si un comando falla, muestra el error real; no inventes output
6. Informa al final la ruta exacta del MP4 generado

Si falta el tema → pregunta UNA sola vez. Luego ejecuta sin más preguntas.

### Verificación rápida (corre si tienes dudas)
```bash
which hyperframes   # → /home/jesusu/.local/share/pnpm/bin/hyperframes
hyperframes --version  # → 0.6.45
```

---

Usa este skill cuando el usuario pida crear videos, motion graphics, reels, edición de video, o animaciones.

## Perfil de contenido del usuario

- **Nicho:** Tecnología y programación
- **Idioma:** Español (puede mezclar términos técnicos en inglés)
- **Plataforma principal:** TikTok (9:16)
- **Duración típica:** 30–60 segundos
- **Contexto del video:** el usuario lo especifica en el prompt cada vez

Si el usuario no especifica tema, preguntar: "¿sobre qué tema es el video?"
Si no especifica estilo, usar **estilo oscuro** por defecto.

---

## Estilos visuales (paleta Giselo)

### Estilo oscuro (default)
```css
--bg:       #0a1020;   /* fondo principal */
--bg2:      #0f1a2e;   /* fondo secundario / cards */
--text:     #cfd6e6;   /* texto principal */
--mute:     #5d6b85;   /* texto secundario */
--accent:   #88c93a;   /* verde lima — highlights, CTA */
--accent2:  #3a9ee0;   /* azul — código, links */
--yellow:   #e8c33a;   /* warnings, énfasis */
--cyan:     #58d8e8;   /* accento frío */
```

### Estilo claro
```css
--bg:       #f0f4ff;
--bg2:      #ffffff;
--text:     #0a1020;
--mute:     #5d6b85;
--accent:   #3a9ee0;
--accent2:  #88c93a;
--yellow:   #e8c33a;
--cyan:     #0d8fa0;
```

### Fuentes
```html
<!-- Geist (principal — títulos, UI) -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;700;900&display=swap" rel="stylesheet">

<!-- Geist Mono (código) -->
<link href="https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400;500;700&display=swap" rel="stylesheet">
```

Aplicar en body: `font-family: 'Geist', system-ui, sans-serif;`
Para código: `font-family: 'Geist Mono', monospace;`

### Snippet de estilo base (oscuro, TikTok)
```html
<style>
  @import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;700;900&family=Geist+Mono:wght@400;700&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    width: 1080px; height: 1920px;
    background: #0a1020;
    color: #cfd6e6;
    font-family: 'Geist', system-ui, sans-serif;
    overflow: hidden;
  }
  .accent  { color: #88c93a; }
  .accent2 { color: #3a9ee0; }
  .code    { font-family: 'Geist Mono', monospace; color: #58d8e8; }
  .mute    { color: #5d6b85; }
</style>
```

---

## Uso de video como asset

Video del usuario en la composición — tres patrones:

### 1. Video de fondo (full screen)
```html
<video id="bg-video"
       class="clip"
       data-start="0"
       data-duration="30"
       data-track-index="1"
       src="assets/video.mp4"
       style="position:absolute; top:0; left:0; width:1080px; height:1920px;
              object-fit:cover; z-index:0"
       muted playsinline>
</video>
```

### 2. Video + overlay de texto encima
```html
<!-- Video fondo -->
<video id="bg" class="clip" data-start="0" data-duration="30" data-track-index="1"
       src="assets/video.mp4"
       style="position:absolute; inset:0; width:100%; height:100%; object-fit:cover;"
       muted playsinline></video>

<!-- Overlay oscuro para legibilidad -->
<div id="overlay" class="clip" data-start="0" data-duration="30" data-track-index="2"
     style="position:absolute; inset:0; background:rgba(10,16,32,0.55);"></div>

<!-- Texto encima -->
<div id="titulo" class="clip" data-start="1" data-duration="5" data-track-index="3"
     style="position:absolute; top:300px; width:1080px; text-align:center;
            font-size:90px; font-weight:900; color:#cfd6e6; padding:0 60px;">
  Tu título aquí
</div>
```

### 3. Video en ventana (no full screen)
```html
<video id="demo" class="clip" data-start="2" data-duration="15" data-track-index="2"
       src="assets/demo.mp4"
       style="position:absolute; top:400px; left:90px; width:900px; height:506px;
              border-radius:16px; object-fit:cover;"
       muted playsinline></video>
```

### Copiar assets del usuario al proyecto
```bash
cp /ruta/del/video.mp4 ~/Workspace/giselo-video/<proyecto>/assets/
```

### Quitar fondo de video (green screen / fondo sólido)
```bash
cd ~/Workspace/giselo-video/<proyecto>
hyperframes remove-background assets/video.mp4
# output: assets/video-nobg.webm (transparente)
```

---

## Workspace

```
~/Workspace/giselo-video/
├── tiktok-template/    # base TikTok 9:16 (1080×1920) — copia para nuevos proyectos
├── base/               # base 16:9 (1920×1080)
└── <proyecto>/         # proyectos generados
```

**Crear nuevo proyecto TikTok:**
```bash
cp -r ~/Workspace/giselo-video/tiktok-template ~/Workspace/giselo-video/<nombre>
cd ~/Workspace/giselo-video/<nombre>
```

## Formatos

| Plataforma | data-width | data-height | Duración |
|-----------|------------|-------------|---------|
| TikTok / Reels / Shorts | 1080 | 1920 | ≤60s |
| YouTube / horizontal | 1920 | 1080 | libre |

## Sintaxis de composición

```html
<div id="root"
     data-composition-id="main"
     data-start="0"
     data-duration="30"
     data-width="1080"
     data-height="1920">

  <div id="titulo"
       class="clip"
       data-start="0"
       data-duration="5"
       data-track-index="1"
       style="position:absolute; top:300px; left:0; width:1080px;
              text-align:center; font-size:90px; font-weight:900; color:#cfd6e6;">
    Texto
  </div>

</div>

<script>
  window.__timelines = window.__timelines || {};
  const tl = gsap.timeline({ paused: true });
  tl.from("#titulo", { opacity: 0, y: -60, duration: 0.8 }, 0);
  window.__timelines["main"] = tl;
</script>
```

**Reglas críticas:**
1. Todo clip con timing → `class="clip"` obligatorio
2. Timeline siempre `{ paused: true }` y registrado en `window.__timelines["<id>"]`
3. Assets → carpeta `assets/` del proyecto, referenciar como `src="assets/archivo"`
4. `data-track-index` empieza en 1, sin repetir en el mismo instante

## Bloques del catálogo más útiles

```bash
# Captions / texto
hyperframes add caption-highlight       # highlight TikTok-style (rojo)
hyperframes add caption-kinetic-slam    # texto kinético full screen
hyperframes add caption-neon-glow       # neon — bueno para tech/gaming
hyperframes add caption-matrix-decode   # scramble Matrix — ideal para código
hyperframes add caption-glitch-rgb      # glitch RGB — estética tech

# Social overlays
hyperframes add tiktok-follow           # follow card TikTok
hyperframes add instagram-follow        # follow card Instagram

# Transiciones
hyperframes add whip-pan
hyperframes add cinematic-zoom
hyperframes add domain-warp-dissolve

# Showcase
hyperframes add logo-outro              # cierre con logo
hyperframes add app-showcase            # showcase app en teléfono
```

## Comandos flujo de trabajo

```bash
hyperframes lint                        # SIEMPRE antes de renderizar
hyperframes inspect                     # revisar layout visual
hyperframes render -o output.mp4        # render final
hyperframes snapshot                    # frames clave como PNG

hyperframes tts --text "texto" -o voz.wav   # TTS local (Kokoro)
hyperframes transcribe assets/audio.mp3     # transcribir → timestamps JSON
hyperframes remove-background assets/v.mp4  # quitar fondo
```

## Flujo completo

```bash
# 1. Copiar template
cp -r ~/Workspace/giselo-video/tiktok-template ~/Workspace/giselo-video/<nombre>
cd ~/Workspace/giselo-video/<nombre>

# 2. Copiar assets del usuario
cp /ruta/video.mp4 assets/

# 3. Agregar bloques
hyperframes add caption-highlight

# 4. Editar index.html

# 5. Validar y renderizar
hyperframes lint && hyperframes render -o output.mp4

# MP4 final: ~/Workspace/giselo-video/<nombre>/output.mp4
```

## Errores comunes

- `clip missing data-track-index` → agregar `data-track-index="N"`
- `timeline not paused` → `gsap.timeline({ paused: true })`
- `timeline not registered` → `window.__timelines["main"] = tl`
- Video no se ve → verificar `muted playsinline` en el tag `<video>`
- Video muy pesado → `hyperframes render --quality medium`
