import asyncio
import logging
import sys
import threading
from typing import Callable

log = logging.getLogger(__name__)


def _macos_has_accessibility() -> bool:
    try:
        import ctypes
        lib = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
        )
        return bool(lib.AXIsProcessTrusted())
    except Exception:
        return True


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


# ── subprocess worker (module-level for multiprocessing spawn pickling) ────────

def _pynput_worker(target_keys_str: set, conn):
    """Run pynput isolated. If SIGTRAP fires here, only this process dies."""
    try:
        from pynput.keyboard import Listener, Key
    except ImportError:
        conn.close()
        return

    pressed: set = set()

    def _canon(key) -> str:
        try:
            if isinstance(key, Key):
                name = key.name
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

    def on_press(key):
        c = _canon(key)
        pressed.add(c)
        if target_keys_str.issubset(pressed):
            try:
                conn.send("trigger")
            except Exception:
                pass

    def on_release(key):
        c = _canon(key)
        pressed.discard(c)
        if c in target_keys_str:
            try:
                conn.send(f"release:{c}")
            except Exception:
                pass

    listener = Listener(on_press=on_press, on_release=on_release)
    try:
        listener.run()
    finally:
        conn.close()


# ── main class ─────────────────────────────────────────────────────────────────

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
            self._hotkey_proc = None

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

    # ── shared trigger ─────────────────────────────────────────────────────────

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
            proc = getattr(self, "_hotkey_proc", None)
            if proc and proc.is_alive():
                proc.kill()

    async def run(self):
        if sys.platform == "linux":
            await self._run_evdev()
        else:
            await self._run_pynput_subprocess()

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

    async def _run_pynput_subprocess(self):
        """Run pynput in a subprocess so SIGTRAP can't kill the main process."""
        try:
            import multiprocessing
        except ImportError:
            raise RuntimeError("multiprocessing not available")

        if sys.platform == "darwin" and not _macos_has_accessibility():
            raise RuntimeError(
                "Giselo necesita permiso de Accesibilidad para el hotkey.\n"
                "System Settings → Privacy & Security → Accessibility → habilitar Terminal\n"
                "Luego reinicia Giselo."
            )

        ctx = multiprocessing.get_context("spawn")
        conn_recv, conn_send = ctx.Pipe(duplex=False)

        self._hotkey_proc = ctx.Process(
            target=_pynput_worker,
            args=(self.target_keys_str, conn_send),
            daemon=True,
        )
        self._hotkey_proc.start()
        conn_send.close()

        log.info("pynput subprocess started (pid=%d). Target keys: %s (%s mode)",
                 self._hotkey_proc.pid, self.target_keys_str, self.mode)

        try:
            while True:
                # Check subprocess health
                if self._hotkey_proc.exitcode is not None:
                    code = self._hotkey_proc.exitcode
                    hint = " (SIGTRAP — pynput/CGEventTap failure)" if code == -5 else ""
                    raise RuntimeError(
                        f"pynput subprocess exited (code={code}){hint}.\n"
                        "Hotkey no disponible. Usa la caja de texto.\n"
                        "Posible causa: Python 3.14 incompatibilidad con pynput en macOS.\n"
                        "Prueba con Python 3.12: brew install python@3.12"
                    )

                # Drain pipe events (non-blocking)
                while conn_recv.poll():
                    try:
                        msg = conn_recv.recv()
                        if msg == "trigger":
                            with self._lock:
                                self._trigger()
                        elif isinstance(msg, str) and msg.startswith("release:"):
                            key = msg[8:]
                            with self._lock:
                                if (self.mode == "push_to_talk"
                                        and self.recording
                                        and key in self.target_keys_str):
                                    self.recording = False
                                    self._fire(self.on_stop)
                    except Exception as e:
                        log.debug("pipe recv error: %s", e)

                await asyncio.sleep(0.05)  # 50ms polling

        except asyncio.CancelledError:
            pass
        finally:
            try:
                conn_recv.close()
            except Exception:
                pass
            proc = self._hotkey_proc
            if proc and proc.is_alive():
                proc.kill()
