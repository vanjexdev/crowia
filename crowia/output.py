import logging
import pathlib
import re
import subprocess
import sys
import threading

log = logging.getLogger(__name__)


def _strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'`{1,3}[^`]*`{1,3}', '', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _notify(title: str, body: str, timeout_ms: int = 5000,
            urgency: str = "low", replace_id: str | None = None) -> str | None:
    """Send desktop notification. Returns notification ID (Linux only)."""
    if sys.platform == "linux":
        args = [
            "notify-send", "--app-name", "crowia",
            "--icon", "audio-input-microphone",
            "--expire-time", str(timeout_ms),
            "--urgency", urgency,
            "--print-id",
        ]
        if replace_id:
            args += ["--replace-id", replace_id]
        args += [title, body]
        try:
            result = subprocess.run(args, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip() or None
            log.warning("notify-send failed (rc=%d): %s", result.returncode, result.stderr)
        except FileNotFoundError:
            log.debug("notify-send not found — install libnotify")
    else:
        # macOS / other: osascript
        safe_body = body.replace("\\", "\\\\").replace('"', '\\"')
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        script = f'display notification "{safe_body}" with title "{safe_title}"'
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
        except Exception as e:
            log.debug("osascript notification failed: %s", e)
    return None


class OutputHandler:
    def __init__(self, cfg: dict):
        out = cfg["output"]
        self.max_chars = out["notify_max_chars"]
        self.timeout_ms = out["notify_timeout_ms"]
        self.response_file = pathlib.Path(out["response_file"])
        self.tts_enabled = out["tts_enabled"]
        self.tts_command = out["tts_command"]
        self._last_notif_id: str | None = None
        self._tts_lock = threading.Lock()
        self._piper_proc: subprocess.Popen | None = None
        self._aplay_proc: subprocess.Popen | None = None

    def stop_tts(self):
        with self._tts_lock:
            if self._aplay_proc and self._aplay_proc.poll() is None:
                self._aplay_proc.kill()
            if self._piper_proc and self._piper_proc.poll() is None:
                self._piper_proc.kill()
        if sys.platform != "linux":
            try:
                import sounddevice as sd
                sd.stop()
            except Exception:
                pass

    def show_status(self, message: str):
        nid = _notify("crowia", message, timeout_ms=5000, urgency="low",
                      replace_id=self._last_notif_id)
        if nid:
            self._last_notif_id = nid

    def set_tts(self, enabled: bool):
        self.tts_enabled = enabled

    def show(self, query: str, response: str):
        self.response_file.parent.mkdir(parents=True, exist_ok=True)
        self.response_file.write_text(
            f"Q: {query}\n\nA: {response}\n", encoding="utf-8"
        )

        body = response
        if len(body) > self.max_chars:
            body = body[: self.max_chars - 3] + "…"
            body += f"\n[Full: {self.response_file}]"

        summary = f"Q: {query[:60]}" if len(query) <= 60 else f"Q: {query[:57]}…"
        nid = _notify(summary, body, timeout_ms=self.timeout_ms,
                      replace_id=self._last_notif_id)
        if nid:
            self._last_notif_id = nid

        if self.tts_enabled:
            self._speak(response)

    def _speak(self, text: str):
        text = _strip_markdown(text)
        if not text.strip():
            return

        cmd = [str(pathlib.Path(c).expanduser()) if c.startswith("~") else c
               for c in self.tts_command]
        is_piper = bool(cmd) and "piper" in pathlib.Path(cmd[0]).name

        if is_piper:
            try:
                piper_proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                with self._tts_lock:
                    self._piper_proc = piper_proc

                piper_proc.stdin.write(text.encode())
                piper_proc.stdin.close()

                if sys.platform == "linux":
                    aplay_proc = subprocess.Popen(
                        ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
                        stdin=piper_proc.stdout,
                        stderr=subprocess.DEVNULL,
                    )
                    with self._tts_lock:
                        self._aplay_proc = aplay_proc
                    piper_proc.stdout.close()
                    aplay_proc.wait(timeout=120)
                    piper_proc.wait(timeout=5)
                else:
                    raw = piper_proc.stdout.read()
                    piper_proc.wait(timeout=30)
                    self._play_raw_sounddevice(raw)
            except Exception as e:
                log.warning("piper TTS failed: %s — falling back to system TTS", e)
                self._speak_system(text)
            finally:
                with self._tts_lock:
                    self._piper_proc = None
                    self._aplay_proc = None
        else:
            try:
                subprocess.run(cmd, input=text, text=True, timeout=120, check=False)
            except Exception as e:
                log.warning("TTS failed: %s", e)

    def _play_raw_sounddevice(self, raw: bytes, sample_rate: int = 22050):
        try:
            import numpy as np
            import sounddevice as sd
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            sd.play(audio, samplerate=sample_rate)
            sd.wait()
        except Exception as e:
            log.warning("sounddevice playback failed: %s", e)

    def _speak_system(self, text: str):
        """Fallback: say (macOS) or espeak (Linux)."""
        try:
            if sys.platform == "darwin":
                subprocess.run(["say", text], timeout=60, check=False)
            else:
                subprocess.run(["espeak", text], timeout=60, check=False,
                               capture_output=True)
        except Exception as e:
            log.debug("System TTS fallback failed: %s", e)
