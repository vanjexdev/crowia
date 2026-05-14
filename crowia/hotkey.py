import asyncio
import logging
import threading
from typing import Callable

import evdev
from evdev import ecodes

log = logging.getLogger(__name__)


class HotkeyListener:
    def __init__(
        self,
        key_names: list[str],
        mode: str,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
    ):
        self.target_keys = {getattr(ecodes, k) for k in key_names}
        self.mode = mode
        self.on_start = on_start
        self.on_stop = on_stop
        self.pressed: set[int] = set()
        self.recording = False
        self._lock = threading.Lock()

    def _find_keyboard_devices(self) -> list[evdev.InputDevice]:
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

    async def _monitor_device(self, device: evdev.InputDevice):
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
                        self._check_trigger()
                elif key_event.keystate == key_event.key_up:
                    with self._lock:
                        self.pressed.discard(code)
                        if self.mode == "push_to_talk" and self.recording:
                            self.recording = False
                            self._fire(self.on_stop)
        except OSError as e:
            log.warning("Device %s disconnected: %s", device.path, e)

    def _check_trigger(self):
        if not self.target_keys.issubset(self.pressed):
            return
        if self.mode == "toggle":
            if not self.recording:
                self.recording = True
                self._fire(self.on_start)
            else:
                self.recording = False
                self._fire(self.on_stop)
        elif self.mode == "push_to_talk":
            if not self.recording:
                self.recording = True
                self._fire(self.on_start)

    def _fire(self, callback: Callable[[], None]):
        threading.Thread(target=callback, daemon=True).start()

    async def run(self):
        devices = self._find_keyboard_devices()
        if not devices:
            raise RuntimeError(
                "No readable keyboard devices found.\n"
                "Fix: sudo usermod -aG input $USER  then log out and back in.\n"
                "Temp workaround: run with sudo."
            )
        log.info("Listening on %d keyboard device(s). Hotkey: %s (%s mode)",
                 len(devices), list(self.target_keys), self.mode)
        tasks = [asyncio.create_task(self._monitor_device(d)) for d in devices]
        await asyncio.gather(*tasks)
