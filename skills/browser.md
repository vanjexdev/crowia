# Skill: Control de Navegador (giselo-browser)

REGLA ABSOLUTA: Para cualquier tarea web usa SOLO `giselo-browser`. NUNCA uses el comando `firefox` directamente — causaría dos ventanas abiertas.

## Comandos

```
giselo-browser navigate <URL>       # Navegar a una URL
giselo-browser click <TEXTO>        # Click en elemento con ese texto
giselo-browser type <TEXTO>         # Escribir en el campo activo
giselo-browser key <TECLA>          # Presionar tecla (Enter, Tab, Escape…)
giselo-browser extract              # Leer el contenido de la página
giselo-browser screenshot           # Capturar pantalla del navegador
giselo-browser scroll <up|down>     # Hacer scroll
giselo-browser tabs                 # Ver pestañas abiertas
giselo-browser new_tab              # Nueva pestaña
giselo-browser status               # Ver si el navegador está activo
```

## Flujos de ejemplo

### Abrir YouTube Music y buscar
```
giselo-browser navigate https://music.youtube.com
giselo-browser eval "document.querySelector('input[placeholder]')?.click()"
giselo-browser type música años 80
giselo-browser key Enter
```
Nota: YouTube Music no tiene texto visible en el buscador — usa eval para activar el input.

### Buscar en Google
```
giselo-browser navigate https://www.google.com
giselo-browser click Buscar
giselo-browser type tu búsqueda aquí
giselo-browser key Enter
```

### Abrir una página específica
```
giselo-browser navigate https://github.com
```

### Leer contenido de la página actual
```
giselo-browser extract
```

## Cuándo usar cada acción

- "abre firefox" → `giselo-browser navigate https://music.youtube.com` (o página pedida)
- "busca X en internet" → navigate google + type + Enter
- "pon música de los 80" → navigate music.youtube.com + click Buscar + type + Enter
- "abre YouTube" → `giselo-browser navigate https://www.youtube.com`
- "ve a Netflix" → `giselo-browser navigate https://www.netflix.com`
- "qué dice la página" → `giselo-browser extract`

## Importante

- Para búsquedas con múltiples pasos: ejecuta los comandos UNO POR UNO en secuencia
- Si el primer comando falla, el navegador arrancará automáticamente al reintentarlo
- El navegador mantiene sesiones (cookies/login) entre usos
