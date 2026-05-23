import logging
import pathlib
import re
import subprocess
import sys
import threading

log = logging.getLogger(__name__)

_say_voice_cache: dict[str, str | None] = {}

_SENT_END = re.compile(r'(?<=[.!?…])\s')


def _split_sentences(buf: str) -> tuple[list[str], str]:
    """Split buf into (complete_sentences, remainder). Boundary = .!?… followed by whitespace."""
    parts = _SENT_END.split(buf)
    if len(parts) == 1:
        return [], buf
    complete = [p.strip() for p in parts[:-1] if p.strip()]
    return complete, parts[-1]


class StreamingTTSPlayer:
    """Keeps piper + aplay alive across multiple sentences (Linux only)."""

    def __init__(self, tts_cmd: list[str]):
        cmd = [str(pathlib.Path(c).expanduser()) if c.startswith("~") else c
               for c in tts_cmd]
        self._piper = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._aplay = subprocess.Popen(
            ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
            stdin=self._piper.stdout,
            stderr=subprocess.DEVNULL,
        )
        self._piper.stdout.close()

    def write(self, sentence: str) -> None:
        text = _strip_markdown(sentence).strip()
        if not text:
            return
        try:
            self._piper.stdin.write((text + "\n").encode())
            self._piper.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def finish(self) -> None:
        try:
            self._piper.stdin.close()
        except OSError:
            pass
        try:
            self._aplay.wait(timeout=120)
        except subprocess.TimeoutExpired:
            self._aplay.kill()
        try:
            self._piper.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._piper.kill()

    def stop(self) -> None:
        for proc in (self._piper, self._aplay):
            try:
                proc.kill()
            except Exception:
                pass


def _best_say_voice(lang: str) -> str | None:
    """Return best `say -v` voice for lang (ISO 639-1). Cached after first call."""
    key = lang[:2].lower()
    if key in _say_voice_cache:
        return _say_voice_cache[key]
    voice = None
    try:
        result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    locale = parts[1] if len(parts) >= 2 else ""
                    if locale.lower().startswith(key + "_"):
                        voice = parts[0]
                        break
    except Exception:
        pass
    _say_voice_cache[key] = voice
    if voice:
        log.info("say voice selected for '%s': %s", key, voice)
    else:
        log.warning(
            "No Spanish say voice found. Options:\n"
            "  1. macOS: System Settings → Accessibility → Spoken Content → Manage Voices → Español\n"
            "  2. pip install piper-tts + download model (better quality)"
        )
    return voice


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
        self._lang = "es"
        self._last_notif_id: str | None = None
        self._tts_lock = threading.Lock()
        self._piper_proc: subprocess.Popen | None = None
        self._aplay_proc: subprocess.Popen | None = None
        self._mpv_proc: subprocess.Popen | None = None
        el = cfg.get("elevenlabs", {})
        self.el_enabled  = el.get("enabled", False)
        self.el_api_key  = el.get("api_key", "")
        self.el_voice_id = el.get("voice_id", "")
        self.el_model_id = el.get("model_id", "eleven_multilingual_v2")

    def set_language(self, lang: str):
        self._lang = lang[:2].lower()

    def stop_tts(self):
        with self._tts_lock:
            if self._aplay_proc and self._aplay_proc.poll() is None:
                self._aplay_proc.kill()
            if self._piper_proc and self._piper_proc.poll() is None:
                self._piper_proc.kill()
            if self._mpv_proc and self._mpv_proc.poll() is None:
                self._mpv_proc.kill()
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

    def _speak_elevenlabs(self, text: str) -> None:
        try:
            from elevenlabs import ElevenLabs
            client = ElevenLabs(api_key=self.el_api_key)
            audio_iter = client.text_to_speech.stream(
                text=text,
                voice_id=self.el_voice_id,
                model_id=self.el_model_id,
            )
            proc = subprocess.Popen(
                ["mpv", "--no-terminal", "--demuxer=lavf", "-"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            with self._tts_lock:
                self._mpv_proc = proc
            try:
                for chunk in audio_iter:
                    if chunk:
                        proc.stdin.write(chunk)
                proc.stdin.close()
                proc.wait(timeout=120)
            except (BrokenPipeError, OSError):
                pass
            finally:
                with self._tts_lock:
                    self._mpv_proc = None
        except Exception as e:
            log.warning("ElevenLabs TTS failed: %s — falling back to system TTS", e)
            self._speak_system(text)

    def _speak(self, text: str):
        text = _strip_markdown(text)
        if not text.strip():
            return

        if self.el_enabled and self.el_api_key and self.el_voice_id:
            self._speak_elevenlabs(text)
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
                cmd = ["say"]
                voice = _best_say_voice(self._lang)
                if voice:
                    cmd += ["-v", voice]
                cmd.append(text)
                subprocess.run(cmd, timeout=60, check=False)
            else:
                subprocess.run(["espeak", text], timeout=60, check=False,
                               capture_output=True)
        except Exception as e:
            log.debug("System TTS fallback failed: %s", e)
