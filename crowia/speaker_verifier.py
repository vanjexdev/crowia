import logging
import pathlib
import numpy as np

log = logging.getLogger(__name__)

_PROFILE_PATH = pathlib.Path("~/.config/crowia/speaker.npy").expanduser()


class SpeakerVerifier:
    """
    Resemblyzer-based speaker verification gate.
    Lazy-loads GE2E model on first use (~50MB, downloaded once to ~/.cache).
    """

    def __init__(self, profile_path: pathlib.Path = _PROFILE_PATH, threshold: float = 0.75):
        self._profile_path = profile_path
        self._threshold = threshold
        self._encoder = None
        self._embedding: np.ndarray | None = None
        self._load_profile()

    def _get_encoder(self):
        if self._encoder is None:
            from resemblyzer import VoiceEncoder
            log.info("SpeakerVerifier: loading GE2E model…")
            self._encoder = VoiceEncoder()
            log.info("SpeakerVerifier: model ready")
        return self._encoder

    def _load_profile(self) -> None:
        if self._profile_path.exists():
            try:
                self._embedding = np.load(self._profile_path)
                log.info("SpeakerVerifier: loaded profile from %s", self._profile_path)
            except Exception as e:
                log.warning("SpeakerVerifier: failed to load profile: %s", e)
                self._embedding = None

    @property
    def has_profile(self) -> bool:
        return self._embedding is not None

    def enroll(self, wav_paths: list[pathlib.Path]) -> None:
        """Compute mean embedding from WAV files and save profile."""
        from resemblyzer import preprocess_wav
        enc = self._get_encoder()
        embeddings = []
        for p in wav_paths:
            try:
                wav = preprocess_wav(p)
                emb = enc.embed_utterance(wav)
                embeddings.append(emb)
                log.info("SpeakerVerifier: enrolled %s", p.name)
            except Exception as e:
                log.warning("SpeakerVerifier: skipping %s — %s", p, e)
        if not embeddings:
            raise ValueError("No valid audio files for enrollment")
        self._embedding = np.mean(embeddings, axis=0)
        self._profile_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(self._profile_path, self._embedding)
        log.info("SpeakerVerifier: profile saved to %s", self._profile_path)

    def verify(self, wav_path: pathlib.Path) -> tuple[bool, float]:
        """Return (is_user, similarity). similarity ∈ [−1, 1]."""
        if self._embedding is None:
            return True, 1.0  # no profile → pass everything
        try:
            from resemblyzer import preprocess_wav
            enc = self._get_encoder()
            wav = preprocess_wav(wav_path)
            emb = enc.embed_utterance(wav)
            sim = float(np.dot(self._embedding, emb))
            is_user = sim >= self._threshold
            log.info("SpeakerVerifier: sim=%.3f threshold=%.2f → %s",
                     sim, self._threshold, "PASS" if is_user else "REJECT")
            return is_user, sim
        except Exception as e:
            log.warning("SpeakerVerifier: verify failed (%s) — passing through", e)
            return True, 0.0
