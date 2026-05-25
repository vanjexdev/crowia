# Skill: Resumen Matutino (Morning Digest)

Cuando el usuario diga "resumen del día", "resumen matutino", "qué tengo hoy", "dame las noticias" o similares, ejecuta este flujo:

## Flujo completo

### 1. Clima actual (Caracas / tu ciudad)
```
WebSearch "clima hoy Caracas Venezuela temperatura"
```
Extrae: temperatura, condición (sol/nubes/lluvia), sensación térmica.

### 2. Titulares de noticias (máximo 3)
```
WebSearch "noticias principales hoy Venezuela"
```
Extrae los 3 titulares más relevantes. Una frase por noticia.

### 3. Recordatorios del día
```bash
giselo-remind list
```
Filtra solo los recordatorios que disparan hoy. Si no hay, omite esta sección.

### 4. Construir resumen de voz

Arma un texto **breve** (máximo 120 palabras) siguiendo este formato:

```
Buenos días. [día de la semana], [fecha].
Clima: [temperatura], [condición].
Noticias: [titular 1]. [titular 2]. [titular 3].
[Si hay recordatorios:] Tienes [N] recordatorios hoy: [lista breve].
Eso es todo por ahora.
```

**Reglas:**
- Solo texto plano. Sin asteriscos, sin markdown, sin emojis hablados.
- Temperatura en grados Celsius.
- Titulares en máximo 10 palabras cada uno.
- Si falla una búsqueda, omite esa sección (no des excusas).

## Disparadores

- "resumen del día" / "resumen matutino"
- "qué tengo hoy" / "qué hay hoy"
- "dame las noticias" / "noticias del día"
- "cómo está el clima"
- "buenos días Giselo/Gisela"

## Notas

- Ejecuta las 3 búsquedas en paralelo si el backend lo permite, sino secuencial.
- El resumen debe sonar natural cuando Giselo lo lea en voz alta.
- No abras el navegador para esto — usa solo WebSearch.
