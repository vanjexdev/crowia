import logging
import pathlib
import wave

import numpy as np
from faster_whisper import WhisperModel
from . import i18n as _i18n

log = logging.getLogger(__name__)

_SILENCE_RMS_THRESHOLD = 0.002  # int16 normalized; below this = no voice captured


def _audio_rms(wav_path: pathlib.Path) -> float:
    try:
        with wave.open(str(wav_path), "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        if len(audio) == 0:
            return 0.0
        return float(np.sqrt(np.mean(audio ** 2)) / 32768.0)
    except Exception:
        return 1.0  # can't check — proceed


class Transcriber:
    def __init__(self, cfg: dict):
        w = cfg["whisper"]
        self.model_size = w["model"]
        self.language = w["language"] or None
        self.device = w["device"]
        self.compute_type = w["compute_type"]
        log.info("Loading Whisper '%s' (%s/%s)…", self.model_size, self.device, self.compute_type)
        self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        log.info("Whisper ready.")

    def transcribe(self, wav_path: pathlib.Path) -> str:
        if not wav_path.exists():
            raise FileNotFoundError(f"WAV not found: {wav_path}")
        if wav_path.stat().st_size < 1024:
            log.warning("WAV very small (%d bytes)", wav_path.stat().st_size)
            return ""

        rms = _audio_rms(wav_path)
        log.info("Audio RMS: %.5f (threshold=%.3f)", rms, _SILENCE_RMS_THRESHOLD)
        if rms < _SILENCE_RMS_THRESHOLD:
            log.warning(
                "Audio is silent (RMS=%.5f). "
                "Check macOS: System Settings → Sound → Input → raise Input Volume.",
                rms,
            )
            return ""

        lang = _i18n.t("whisper_lang") or self.language
        log.debug("Transcribing %s (lang=%s, rms=%.4f)", wav_path, lang, rms)
        segs, _ = self._model.transcribe(
            str(wav_path),
            language=lang or None,
            beam_size=3,
            temperature=0,
            condition_on_previous_text=False,
            no_speech_threshold=0.5,
            compression_ratio_threshold=1.8,   # reject hallucination loops
            vad_filter=True,
            vad_parameters={
                "threshold": 0.3,
                "min_speech_duration_ms": 100,
                "min_silence_duration_ms": 300,
            },
            # no initial_prompt — causes catastrophic hallucinations on silence
        )

        text = " ".join(s.text for s in segs).strip()
        log.info("Transcribed: %r", text)
        return text
