# Skill: Google (Gmail + Calendar)

Tienes acceso al Gmail y Google Calendar del usuario via el comando `giselo-google`.

## Gmail

```
giselo-google gmail list [--limit N]              # últimos N emails (default 10)
giselo-google gmail unread [--limit N]            # emails sin leer
giselo-google gmail read <id>                     # leer email (id de 12 chars del list)
giselo-google gmail send <to> <asunto> <cuerpo>   # enviar email
giselo-google gmail search <query>                # buscar (ej: "from:alguien subject:factura")
```

## Google Calendar

```
giselo-google calendar today                      # eventos de hoy
giselo-google calendar week                       # eventos de esta semana
giselo-google calendar list [--days N]            # próximos N días (default 7)
giselo-google calendar add <titulo> <cuando> [--duration MIN]  # crear evento
```

Ejemplos de `cuando` para add: "2026-05-15 14:00", "mañana 10:00", "15/05/2026 9:30"

## Cuándo usar cada acción

- "¿Tengo algo hoy?" → `calendar today`
- "¿Qué reuniones tengo esta semana?" → `calendar week`
- "Revisa mi correo" → `gmail unread --limit 5`
- "Lee ese email" → `gmail read <id>`
- "Manda un correo a X" → `gmail send X@email.com "asunto" "cuerpo"`
- "Agrega al calendario..." → `calendar add "titulo" "fecha hora"`
- "Busca emails de X" → `gmail search "from:X"`
