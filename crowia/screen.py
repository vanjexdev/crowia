import logging
import os
import pathlib
import subprocess
import tempfile

log = logging.getLogger(__name__)


def _env() -> dict:
    env = os.environ.copy()
    uid = os.getuid()
    env.setdefault("WAYLAND_DISPLAY", "wayland-0")
    env.setdefault("DISPLAY", ":0")
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{uid}")
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{uid}/bus")
    env.setdefault("XDG_CURRENT_DESKTOP", "KDE")
    return env


def take_screenshot() -> pathlib.Path | None:
    tmp = pathlib.Path(tempfile.mktemp(suffix=".png", prefix="crowia_screen_", dir="/tmp/crowia"))
    tmp.parent.mkdir(parents=True, exist_ok=True)
    env = _env()

    # KDE Plasma — spectacle
    try:
        result = subprocess.run(
            ["spectacle", "--background", "--nonotify", "--fullscreen", "--output", str(tmp)],
            capture_output=True,
            timeout=15,
            env=env,
        )
        if result.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
            log.info("Screenshot via spectacle: %s", tmp)
            return tmp
        log.warning("spectacle failed (rc=%d): %s", result.returncode, result.stderr.decode())
    except FileNotFoundError:
        log.warning("spectacle not found, trying grim")
    except subprocess.TimeoutExpired:
        log.error("spectacle timed out")
        return None

    # Fallback: wlroots (Hyprland/Sway)
    try:
        result = subprocess.run(
            ["grim", str(tmp)],
            capture_output=True,
            timeout=10,
            env=env,
        )
        if result.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
            log.info("Screenshot via grim: %s", tmp)
            return tmp
        log.error("grim failed (rc=%d): %s", result.returncode, result.stderr.decode())
    except FileNotFoundError:
        log.error("No screenshot tool available.")
    except subprocess.TimeoutExpired:
        log.error("grim timed out")

    return None
