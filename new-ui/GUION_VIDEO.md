# Guion — Video Giselo
**Canal:** Vanjex
**Tono:** técnico pero accesible, sin relleno, directo al grano
**Duración estimada:** 6–9 minutos

---

## 🎬 INTRO (0:00 – 0:30)

> **[Pantalla: Giselo corriendo, logo o UI visible]**

"Qué tal, soy Vanjex.
Hoy les traigo algo en lo que he estado trabajando: **Giselo**,
un asistente de IA personal que corre localmente en tu máquina Linux,
responde por voz, controla el navegador, abre apps, busca en internet
y básicamente actúa como si tuvieras un Claude con acceso a tu sistema.

Sin APIs de terceros para la voz. Sin ventanas emergentes. Sin fricción.
Solo hablas — y él responde."

---

## 🧠 PARTE 1 — QUÉ ES (0:30 – 1:30)

> **[Mostrar la UI: ventana Giselo, pill de estado, botones]**

"Giselo es un asistente de voz construido sobre **Claude de Anthropic**,
pero corriendo desde tu escritorio. Tiene interfaz gráfica propia —
la ven acá — con un núcleo central que cambia de estado: grabando,
procesando, respondiendo.

Tres cosas que lo diferencian de un chatbot normal:

Primero — **acceso real al sistema**. No simula hacer cosas. Las hace.
Abre aplicaciones, navega en tu navegador con tu sesión activa,
ejecuta comandos bash, lee y escribe archivos.

Segundo — **voz bidireccional**. Hablas, él escucha. Responde en voz
usando síntesis TTS con Piper — offline, sin latencia de red.

Tercero — **streaming de audio**. No espera a que Claude termine de
escribir la respuesta completa para empezar a hablar. En cuanto termina
la primera frase, ya está sonando."

---

## 🎤 PARTE 2 — DEMO VOZ BÁSICA (1:30 – 2:30)

> **[DEMO EN VIVO: hablar con Giselo]**
> Pregunta sugerida: *"Giselo, ¿cuánto vale Tesla en bolsa ahora mismo?"*

"Miren cómo funciona. Presiono **Ctrl+L** para activar el micrófono —
ven el indicador de nivel de audio — hago una pregunta..."

> **[mostrar respuesta en pantalla + audio saliendo]**

"No abrió el navegador. Usó WebSearch directamente, me trajo el dato,
y empezó a responder en voz antes de que terminara de escribir.
Eso es el streaming TTS en acción."

---

## 🔁 PARTE 3 — MODO SIEMPRE ACTIVO (2:30 – 3:30)

> **[DEMO: activar botón "◉ siempre" en la UI]**

"Pero presionar Ctrl+L cada vez es fricción. Tengo un modo **siempre
activo** — este botón de acá.

Cuando lo activo, Giselo empieza a escuchar constantemente.
Detecta cuándo empiezo a hablar, espera que me calle — usando VAD,
detección de actividad de voz — y automáticamente procesa lo que dije.

El truco: mientras Giselo está hablando, el micrófono está silenciado.
Así evitamos que su propia voz se capture como input y cree un bucle infinito.
Y mientras habla, el volumen de otras apps — Spotify, YouTube, lo que sea —
baja automáticamente. Cuando termina, vuelve al nivel original."

---

## 🌐 PARTE 4 — CONTROL DEL NAVEGADOR (3:30 – 4:45)

> **[DEMO: pedir abrir YouTube Music o navegar a algún sitio]**

"Ahora lo interesante: el navegador.

Giselo tiene acceso a **tu navegador real** — con tu sesión, tus cookies,
tus cuentas. No abre un perfil limpio de Playwright. Se conecta a
Chromium/Brave que ya tenés corriendo via CDP, o lanza Firefox
con tu perfil.

Entonces puedo decirle: *'Giselo, pon música de los 90 en YouTube Music'* —"

> **[mostrar cómo abre nueva pestaña y navega]**

"...y lo hace. Abre **nueva pestaña** para no interrumpir lo que
ya está corriendo, navega, busca, hace clic.

Importante: si le hago una pregunta informativa, no toca el navegador.
Usa WebSearch. El navegador solo se abre cuando yo pido explícitamente
'abre', 'navega', o 'muéstrame en el navegador'."

---

## 💻 PARTE 5 — CONTROL DEL SISTEMA (4:45 – 5:45)

> **[DEMO: "abre el editor", "abre la terminal"]**

"También controla el sistema operativo. Si digo *'abre Zed'* —"

> **[mostrar giselo-launch-app en acción]**

"Antes de lanzarlo, verifica si ya está corriendo via `pgrep`.
Si ya está abierto, enfoca la ventana. Si no, lo lanza.
Sin duplicados, sin preguntas."

> **[DEMO: @ en el input para adjuntar archivo o carpeta]**

"En el input de texto, el símbolo **@** abre un selector.
Puedo adjuntar archivos, carpetas o capturas de pantalla directamente
en el mensaje. Útil cuando quiero que analice algo específico de mi sistema."

---

## 🗂️ PARTE 6 — PERFILES DE TRABAJO (5:45 – 6:30)

> **[mostrar config.yaml o simplemente describir]**

"Tengo perfiles de trabajo configurados. Si le digo
*'vamos a trabajar para PDM'*, activa ese perfil:
lanza **Floorp** — que es el navegador asignado a ese proyecto —
e inyecta contexto en la conversación para que sepa en qué modo está.

Cada perfil puede tener su propio navegador y su propio contexto de trabajo.
Útil cuando trabajo en varios proyectos con diferentes stacks o clientes."

---

## 🔧 PARTE 7 — STACK TÉCNICO (6:30 – 7:30)

> **[Mostrar código o estructura de carpetas brevemente]**

"Para los curiosos del stack:

- **Frontend:** PyQt6 — UI nativa, sin Electron, sin browser embebido
- **LLM:** Claude Haiku via API de Anthropic — rápido y barato
- **Transcripción:** Whisper `small` corriendo en CPU
- **TTS:** Piper con modelo español — offline, ~1s latencia
- **Browser:** Playwright + CDP para conectar a navegador real
- **VAD:** webrtcvad para detección de silencio
- **Todo en Python**, corriendo en CachyOS + KDE Plasma 6 Wayland

El código está en GitHub si quieren verlo, hacer fork o contribuir."

---

## 🚀 OUTRO (7:30 – 8:00)

"Esto es Giselo. Todavía en desarrollo activo — hay cosas por pulir,
features por agregar. Pero ya lo uso día a día para trabajar.

Si les interesa ver cómo construí algo específico — el streaming TTS,
la integración con el navegador, el modo siempre activo con VAD — díganme
en los comentarios y lo explico en detalle en otro video.

Soy Vanjex. Nos vemos."

---

## 📋 CHECKLIST PRE-GRABACIÓN

- [ ] Giselo corriendo y respondiendo correctamente
- [ ] Piper TTS funcionando (probar antes)
- [ ] Brave con `--remote-debugging-port=9222` abierto
- [ ] Spotify o YouTube Music corriendo (para demo de duck de audio)
- [ ] Perfil PDM configurado en config.yaml
- [ ] Silencio en el ambiente (VAD es sensible)
- [ ] OBS o grabador configurado con audio del sistema
- [ ] `◎ siempre` desactivado al inicio (mostrar activación en cámara)

---

## 🎯 ORDEN DE IMPACTO (si hay que recortar)

1. Demo voz básica con respuesta + TTS streaming → **imprescindible**
2. Modo siempre activo + duck de audio → **muy visual**
3. Browser con YouTube Music → **wow factor**
4. Control del sistema (launch-app) → **útil demostrar**
5. Stack técnico → **para la audiencia dev**
6. Perfiles de trabajo → **opcional, si hay tiempo**
