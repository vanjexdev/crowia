import logging
import pathlib
import signal
import subprocess
import time

log = logging.getLogger(__name__)


class Recorder:
    def __init__(self, cfg: dict):
        self.cfg = cfg["audio"]
        self._proc: subprocess.Popen | None = None
        self._wav_path: pathlib.Path | None = None

    def start(self) -> pathlib.Path:
        tmp_dir = pathlib.Path(self.cfg["tmp_dir"])
        tmp_dir.mkdir(parents=True, exist_ok=True)
        self._wav_path = tmp_dir / f"rec_{int(time.time())}.wav"

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
        log.info("Recording to %s", self._wav_path)
        return self._wav_path

    def stop(self) -> pathlib.Path | None:
        if not self._proc:
            return None
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
        log.info("Recording stopped: %s", self._wav_path)
        return self._wav_path

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
