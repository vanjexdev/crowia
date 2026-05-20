import logging
import pathlib
import signal
import subprocess
import sys
import time
import wave

log = logging.getLogger(__name__)


class Recorder:
    def __init__(self, cfg: dict):
        self.cfg = cfg["audio"]
        self._proc: subprocess.Popen | None = None
        self._wav_path: pathlib.Path | None = None
        # macOS / non-Linux: sounddevice-based recording
        self._sd_stream = None
        self._sd_frames: list = []
        self._sd_recording = False

    def _tmp_path(self) -> pathlib.Path:
        tmp_dir = pathlib.Path(self.cfg["tmp_dir"])
        tmp_dir.mkdir(parents=True, exist_ok=True)
        return tmp_dir / f"rec_{int(time.time())}.wav"

    def start(self) -> pathlib.Path:
        self._wav_path = self._tmp_path()
        if sys.platform == "linux":
            self._start_arecord()
        else:
            self._start_sounddevice()
        log.info("Recording to %s", self._wav_path)
        return self._wav_path

    def stop(self) -> pathlib.Path | None:
        if sys.platform == "linux":
            self._stop_arecord()
        else:
            self._stop_sounddevice()
        log.info("Recording stopped: %s", self._wav_path)
        return self._wav_path

    # ── Linux / arecord ────────────────────────────────────────────────────────

    def _start_arecord(self):
        cmd = [
            "arecord",
            "-D", self.cfg["device"],
            "-c", str(self.cfg["channels"]),
            "-r", str(self.cfg["rate"]),
            "-f", self.cfg["format"],
            "-t", "wav",
            str(self._wav_path),
        ]
        log.debug("arecord cmd: %s", " ".join(cmd))
        self._proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def _stop_arecord(self):
        if not self._proc:
            return
        if self._proc.poll() is None:
            # SIGINT required — arecord only writes WAV header on graceful shutdown
            self._proc.send_signal(signal.SIGINT)
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                log.warning("arecord did not stop gracefully, killing")
                self._proc.kill()
                self._proc.wait()
        stderr = self._proc.stderr.read().decode(errors="replace") if self._proc.stderr else ""
        if stderr:
            log.debug("arecord stderr: %s", stderr.strip())
        self._proc = None

    # ── macOS / sounddevice ────────────────────────────────────────────────────

    def _start_sounddevice(self):
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            raise RuntimeError(
                "sounddevice not installed. Fix:\n"
                "  pip install sounddevice numpy"
            )

        self._sd_frames = []
        self._sd_recording = True
        rate = self.cfg["rate"]
        channels = self.cfg["channels"]

        def _callback(indata, frames, time_info, status):
            if status:
                log.debug("sounddevice status: %s", status)
            if self._sd_recording:
                self._sd_frames.append(indata.copy())

        self._sd_stream = sd.InputStream(
            samplerate=rate,
            channels=channels,
            dtype="int16",
            callback=_callback,
        )
        self._sd_stream.start()

    def _stop_sounddevice(self):
        self._sd_recording = False
        if self._sd_stream:
            self._sd_stream.stop()
            self._sd_stream.close()
            self._sd_stream = None

        if not self._sd_frames or not self._wav_path:
            return

        try:
            import numpy as np
            audio = np.concatenate(self._sd_frames, axis=0)
            with wave.open(str(self._wav_path), "wb") as wf:
                wf.setnchannels(self.cfg["channels"])
                wf.setsampwidth(2)  # int16
                wf.setframerate(self.cfg["rate"])
                wf.writeframes(audio.tobytes())
        except Exception as e:
            log.error("Failed to write WAV: %s", e)

    # ── shared ─────────────────────────────────────────────────────────────────

    def cleanup(self, path: pathlib.Path | None):
        if path and path.exists():
            try:
                path.unlink()
                log.debug("Deleted %s", path)
            except OSError as e:
                log.warning("Could not delete %s: %s", path, e)

    @property
    def wav_path(self) -> pathlib.Path | None:
        return self._wav_path
