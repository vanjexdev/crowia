import logging
import subprocess

log = logging.getLogger(__name__)


def control_volume(action) -> str:
    try:
        if action == "up":
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"], check=True)
            return "Volumen subido."
        elif action == "down":
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"], check=True)
            return "Volumen bajado."
        elif action == "mute":
            subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"], check=True)
            return "Audio silenciado/activado."
        elif isinstance(action, int):
            subprocess.run(
                ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{action}%"], check=True
            )
            return f"Volumen al {action}%."
    except FileNotFoundError:
        log.error("pactl not found")
        return "Error: pactl no encontrado."
    except subprocess.CalledProcessError as e:
        log.error("Volume control failed: %s", e)
        return f"Error controlando volumen: {e}"
    return "Acción de volumen desconocida."
