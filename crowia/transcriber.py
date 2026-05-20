import logging
import pathlib

from faster_whisper import WhisperModel
from . import i18n as _i18n

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

        lang = _i18n.t("whisper_lang") or self.language
        prompt = _i18n.t("whisper_initial_prompt") or self.initial_prompt or None
        log.debug("Transcribing %s (lang=%s)", wav_path, lang)
        segs, _ = self._model.transcribe(
            str(wav_path),
            language=lang or None,
            beam_size=3,
            temperature=0,
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
            vad_filter=False,
            initial_prompt=prompt,
        )

        text = " ".join(s.text for s in segs).strip()
        log.info("Transcribed: %r", text)
        return text
