import logging
import pathlib
import re
import subprocess

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


class OutputHandler:
    def __init__(self, cfg: dict):
        out = cfg["output"]
        self.max_chars = out["notify_max_chars"]
        self.timeout_ms = out["notify_timeout_ms"]
        self.response_file = pathlib.Path(out["response_file"])
        self.tts_enabled = out["tts_enabled"]
        self.tts_command = out["tts_command"]
        self._last_notif_id: str | None = None
        self._tts_lock = __import__("threading").Lock()
        self._piper_proc: subprocess.Popen | None = None
        self._aplay_proc: subprocess.Popen | None = None

    def stop_tts(self):
        with self._tts_lock:
            if self._aplay_proc and self._aplay_proc.poll() is None:
                self._aplay_proc.kill()
            if self._piper_proc and self._piper_proc.poll() is None:
                self._piper_proc.kill()

    def show_status(self, message: str):
        args = [
            "notify-send",
            "--app-name", "crowia",
            "--icon", "audio-input-microphone",
            "--expire-time", "5000",
            "--urgency", "low",
            "--print-id",
        ]
        if self._last_notif_id:
            args += ["--replace-id", self._last_notif_id]
        args += ["crowia", message]

        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            self._last_notif_id = result.stdout.strip()

    def set_tts(self, enabled: bool):
        self.tts_enabled = enabled

    def show(self, query: str, response: str):
        # Write full response to file
        self.response_file.parent.mkdir(parents=True, exist_ok=True)
        self.response_file.write_text(
            f"Q: {query}\n\nA: {response}\n", encoding="utf-8"
        )

        # Build notification body (truncated)
        body = response
        if len(body) > self.max_chars:
            body = body[: self.max_chars - 3] + "…"
            body += f"\n[Full: {self.response_file}]"

        summary = f"Q: {query[:60]}" if len(query) <= 60 else f"Q: {query[:57]}…"

        args = [
            "notify-send",
            "--app-name", "crowia",
            "--icon", "audio-input-microphone",
            "--expire-time", str(self.timeout_ms),
            "--print-id",
        ]
        if self._last_notif_id:
            args += ["--replace-id", self._last_notif_id]
        args += [summary, body]

        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            self._last_notif_id = result.stdout.strip()
        elif result.returncode != 0:
            log.warning("notify-send failed (rc=%d): %s", result.returncode, result.stderr)

        if self.tts_enabled:
            self._speak(response)

    def _speak(self, text: str):
        text = _strip_markdown(text)
        if not text.strip():
            return

        cmd = [str(pathlib.Path(c).expanduser()) if c.startswith("~") else c
               for c in self.tts_command]
        is_piper = cmd and "piper-tts" in cmd[0]

        if is_piper:
            try:
                piper_proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                aplay_proc = subprocess.Popen(
                    ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
                    stdin=piper_proc.stdout,
                    stderr=subprocess.DEVNULL,
                )
                with self._tts_lock:
                    self._piper_proc = piper_proc
                    self._aplay_proc = aplay_proc
                piper_proc.stdin.write(text.encode())
                piper_proc.stdin.close()
                piper_proc.stdout.close()
                aplay_proc.wait(timeout=120)
                piper_proc.wait(timeout=5)
            except Exception as e:
                log.warning("piper TTS failed: %s", e)
            finally:
                with self._tts_lock:
                    self._piper_proc = None
                    self._aplay_proc = None
        else:
            try:
                subprocess.run(
                    cmd,
                    input=text,
                    text=True,
                    timeout=120,
                    check=False,
                )
            except Exception as e:
                log.warning("TTS failed: %s", e)
