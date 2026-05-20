import asyncio
import logging
import sys
import threading
from typing import Callable

log = logging.getLogger(__name__)


def _macos_has_accessibility() -> bool:
    """Check if process has macOS Accessibility permission (required by pynput)."""
    try:
        import ctypes
        lib = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
        )
        return bool(lib.AXIsProcessTrusted())
    except Exception:
        return True  # can't check — assume OK


# evdev key name → canonical string for pynput comparison
_EVDEV_TO_CANON = {
    "KEY_RIGHTCTRL": "ctrl", "KEY_LEFTCTRL": "ctrl",
    "KEY_LEFTSHIFT": "shift", "KEY_RIGHTSHIFT": "shift",
    "KEY_LEFTALT": "alt", "KEY_RIGHTALT": "alt",
    "KEY_LEFTMETA": "cmd", "KEY_RIGHTMETA": "cmd",
    "KEY_GRAVE": "`",
    "KEY_SPACE": "space", "KEY_ENTER": "enter",
    "KEY_TAB": "tab", "KEY_ESC": "esc", "KEY_BACKSPACE": "backspace",
    **{f"KEY_F{i}": f"f{i}" for i in range(1, 13)},
    **{f"KEY_{i}": str(i) for i in range(10)},
}


def _pynput_canonical(key) -> str:
    try:
        from pynput.keyboard import Key
        if isinstance(key, Key):
            name = key.name  # e.g. "ctrl_r", "shift_l"
            for base in ("ctrl", "shift", "alt", "cmd"):
                if name.startswith(base):
                    return base
            return name
    except Exception:
        pass
    c = getattr(key, "char", None)
    if c:
        return c
    return f"vk:{getattr(key, 'vk', '?')}"


class HotkeyListener:
    def __init__(
        self,
        key_names: list[str],
        mode: str,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
    ):
        self.mode = mode
        self.on_start = on_start
        self.on_stop = on_stop
        self.recording = False
        self._lock = threading.Lock()

        if sys.platform == "linux":
            import evdev
            from evdev import ecodes
            self._evdev = evdev
            self._ecodes = ecodes
            self.target_keys: set = {getattr(ecodes, k) for k in key_names}
            self.pressed: set = set()
        else:
            self.target_keys_str: set[str] = {
                _EVDEV_TO_CANON.get(k, k.lower().replace("key_", ""))
                for k in key_names
            }
            self.pressed_str: set[str] = set()

    # ── Linux / evdev ──────────────────────────────────────────────────────────

    def _find_keyboard_devices(self):
        evdev, ecodes = self._evdev, self._ecodes
        devices = []
        for path in evdev.list_devices():
            try:
                d = evdev.InputDevice(path)
                if ecodes.EV_KEY in d.capabilities():
                    devices.append(d)
                    log.debug("Monitoring device: %s (%s)", path, d.name)
            except PermissionError:
                log.warning("Permission denied: %s — add user to 'input' group", path)
            except Exception as e:
                log.debug("Skipping device %s: %s", path, e)
        return devices

    async def _monitor_device(self, device):
        evdev, ecodes = self._evdev, self._ecodes
        try:
            async for event in device.async_read_loop():
                if event.type != ecodes.EV_KEY:
                    continue
                key_event = evdev.categorize(event)
                code = key_event.scancode
                if code not in self.target_keys:
                    continue
                if key_event.keystate == key_event.key_down:
                    with self._lock:
                        self.pressed.add(code)
                        if self.target_keys.issubset(self.pressed):
                            self._trigger()
                elif key_event.keystate == key_event.key_up:
                    with self._lock:
                        self.pressed.discard(code)
                        if self.mode == "push_to_talk" and self.recording:
                            self.recording = False
                            self._fire(self.on_stop)
        except OSError as e:
            log.warning("Device %s disconnected: %s", device.path, e)

    # ── macOS / Windows / pynput ───────────────────────────────────────────────

    def _on_press(self, key):
        canon = _pynput_canonical(key)
        with self._lock:
            self.pressed_str.add(canon)
            if self.target_keys_str.issubset(self.pressed_str):
                self._trigger()

    def _on_release(self, key):
        canon = _pynput_canonical(key)
        with self._lock:
            self.pressed_str.discard(canon)
            if self.mode == "push_to_talk" and self.recording and canon in self.target_keys_str:
                self.recording = False
                self._fire(self.on_stop)

    # ── shared ─────────────────────────────────────────────────────────────────

    def _trigger(self):
        if self.mode == "toggle":
            if not self.recording:
                self.recording = True
                self._fire(self.on_start)
            else:
                self.recording = False
                self._fire(self.on_stop)
        elif self.mode == "push_to_talk" and not self.recording:
            self.recording = True
            self._fire(self.on_start)

    def _fire(self, callback: Callable[[], None]):
        threading.Thread(target=callback, daemon=True).start()

    def stop(self):
        if sys.platform == "linux":
            loop = getattr(self, "_loop", None)
            tasks = getattr(self, "_tasks", [])
            if loop and tasks:
                for t in tasks:
                    loop.call_soon_threadsafe(t.cancel)
        else:
            listener = getattr(self, "_pynput_listener", None)
            if listener:
                listener.stop()

    async def run(self):
        if sys.platform == "linux":
            await self._run_evdev()
        else:
            await self._run_pynput()

    async def _run_evdev(self):
        devices = self._find_keyboard_devices()
        if not devices:
            raise RuntimeError(
                "No readable keyboard devices found.\n"
                "Fix: sudo usermod -aG input $USER  then log out and back in.\n"
                "Temp workaround: run with sudo."
            )
        log.info("Listening on %d keyboard device(s). Hotkey: %s (%s mode)",
                 len(devices), list(self.target_keys), self.mode)
        self._loop = asyncio.get_running_loop()
        self._tasks = [asyncio.create_task(self._monitor_device(d)) for d in devices]
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            pass

    async def _run_pynput(self):
        try:
            from pynput.keyboard import Listener
        except ImportError:
            raise RuntimeError(
                "pynput not installed. Fix:\n"
                "  ~/.local/share/crowia/.venv/bin/pip install pynput"
            )

        # macOS: pynput sends SIGTRAP (kills process) if Accessibility is not granted.
        # Check before calling Listener.start() so we can fail with a clear message.
        if sys.platform == "darwin" and not _macos_has_accessibility():
            raise RuntimeError(
                "Giselo necesita permiso de Accesibilidad para detectar el hotkey.\n\n"
                "  System Settings → Privacy & Security → Accessibility\n"
                "  → habilitar Terminal (o iTerm2)\n\n"
                "Luego reinicia Giselo. La ventana funciona sin hotkey por ahora."
            )

        log.info("Listening via pynput. Target keys: %s (%s mode)",
                 self.target_keys_str, self.mode)
        self._pynput_listener = Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._pynput_listener.start()
        log.info("pynput listener active")
        try:
            await asyncio.sleep(float("inf"))
        except asyncio.CancelledError:
            pass
        finally:
            self._pynput_listener.stop()
