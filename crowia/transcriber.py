import logging
import pathlib

from faster_whisper import WhisperModel

log = logging.getLogger(__name__)


class Transcriber:
    def __init__(self, cfg: dict):
        w = cfg["whisper"]
        self.model_size = w["model"]
        self.language = w["language"] or None
        self.device = w["device"]
        self.compute_type = w["compute_type"]
        self.initial_prompt = w.get("initial_prompt", "")
        log.info("Loading Whisper '%s' (%s/%s)…", self.model_size, self.device, self.compute_type)
        self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        log.info("Whisper ready.")

    def transcribe(self, wav_path: pathlib.Path) -> str:
        if not wav_path.exists():
            raise FileNotFoundError(f"WAV not found: {wav_path}")
        if wav_path.stat().st_size < 1024:
            log.warning("WAV very small (%d bytes)", wav_path.stat().st_size)
            return ""

        log.debug("Transcribing %s", wav_path)
        segs, _ = self._model.transcribe(
            str(wav_path),
            language=self.language,
            beam_size=3,
            temperature=0,
            condition_on_previous_text=False,   # evita alucinaciones/repeticiones
            no_speech_threshold=0.6,            # descarta clips sin voz
            compression_ratio_threshold=2.4,    # descarta output sin sentido
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
            initial_prompt=self.initial_prompt or None,
        )

        text = " ".join(s.text for s in segs).strip()
        log.info("Transcribed: %r", text)
        return text
