# Skill: Recordatorios (giselo-remind)

Puedes crear recordatorios del sistema que funcionan aunque Giselo esté cerrado. Usan systemd del usuario.

## Comandos

```
giselo-remind add "mensaje" "cuando"            # Crear recordatorio
giselo-remind add "mensaje" "cuando" --calendar # Crear + evento en Google Calendar
giselo-remind list                              # Ver recordatorios activos
giselo-remind cancel <id>                       # Cancelar recordatorio
```

## Formato de "cuando"

```
"2026-05-15 14:00"          → Una sola vez en esa fecha/hora
"hourly"                    → Cada hora (en punto)
"daily 09:00"               → Todos los días a las 9am
"weekly Mon 09:00"          → Todos los lunes a las 9am
"weekly Mon,Wed,Fri 18:00"  → Varios días a las 6pm
```

## Cuándo usar cada acción

- "Recuérdame tomar agua cada hora" → `giselo-remind add "Tomar agua" "hourly"`
- "Recuérdame las reuniones de los lunes a las 9" → `giselo-remind add "Reunión" "weekly Mon 09:00"`
- "Ponme un recordatorio para mañana a las 3pm" → `giselo-remind add "..." "2026-05-15 15:00"`
- "¿Qué recordatorios tengo?" → `giselo-remind list`
- "Cancela el recordatorio X" → `giselo-remind cancel <id del list>`

## Notas

- Los recordatorios persisten después de reiniciar (systemd --user).
- El ID tiene forma `giselo-remind-<timestamp>`.
- Con `--calendar` también crea evento en Google Calendar (solo funciona para fechas únicas).
- Al disparar: muestra notificación de escritorio + voz por TTS.
