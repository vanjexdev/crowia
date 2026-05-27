import collections
import logging
import pathlib
import queue
import tempfile
import threading
import wave
from difflib import SequenceMatcher

import numpy as np
import sounddevice as sd
import webrtcvad

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)  # 480


class AlwaysOnListener:
    """
    Wake word + VAD listener.
    Single processor thread eliminates race conditions.
    Flow: IDLE → (wake word) → ACTIVE → (utterance) → IDLE
    """

    def __init__(self, cfg: dict, on_speech_ready, transcriber, on_wake=None, on_idle=None, on_text_ready=None):
        ao = cfg.get("always_on", {})
        self.wake_phrases: list[str] = [
            p.lower() for p in ao.get("wake_phrases", ["oye crowia", "hey crowia", "crowia"])
        ]
        self._vad_level: int = ao.get("vad_aggressiveness", 2)
        self._silence_ms: int = ao.get("silence_duration_ms", 800)
        self._min_speech_ms: int = ao.get("min_speech_ms", 400)
        self._max_record_sec: int = ao.get("max_record_seconds", 30)
        self._transcriber = transcriber
        self.on_speech_ready = on_speech_ready
        self.on_wake = on_wake or (lambda: None)
        self.on_idle = on_idle or (lambda: None)
        self.on_text_ready = on_text_ready or (lambda txt: None)

        self._vad = webrtcvad.Vad(self._vad_level)
        self._silence_frames = int(self._silence_ms / FRAME_MS)
        self._min_frames = int(self._min_speech_ms / FRAME_MS)
        self._max_frames = int(self._max_record_sec * 1000 / FRAME_MS)
        self._stop_event = threading.Event()
        self._utterance_queue: queue.Queue = queue.Queue()
        self._active = False  # only touched by processor thread

    def stop(self):
        self._stop_event.set()

    def run(self):
        log.info("AlwaysOn: wake phrases: %s", self.wake_phrases)

        # Processor thread handles state sequentially — no race conditions
        proc = threading.Thread(target=self._processor, daemon=True)
        proc.start()

        ring = collections.deque(maxlen=int(500 / FRAME_MS))  # 500ms pre-roll
        speech_buf: list[bytes] = []
        silence_count = 0
        in_speech = False

        def audio_callback(indata, _frames, _time, _status):
            nonlocal speech_buf, silence_count, in_speech

            if self._stop_event.is_set():
                raise sd.CallbackStop()

            pcm = (indata[:, 0] * 32767).astype(np.int16)
            raw = pcm.tobytes()

            try:
                is_speech = self._vad.is_speech(raw, SAMPLE_RATE)
            except Exception:
                is_speech = False

            ring.append(raw)

            if is_speech:
                if not in_speech:
                    in_speech = True
                    speech_buf = list(ring)  # include pre-roll
                else:
                    speech_buf.append(raw)
                silence_count = 0
            elif in_speech:
                speech_buf.append(raw)
                silence_count += 1

                if silence_count >= self._silence_frames or len(speech_buf) >= self._max_frames:
                    captured = list(speech_buf)
                    speech_buf = []
                    silence_count = 0
                    in_speech = False

                    if len(captured) >= self._min_frames:
                        self._utterance_queue.put(captured)

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=FRAME_SAMPLES,
            callback=audio_callback,
        ):
            log.info("AlwaysOn: mic open. Di '%s' para activar.", self.wake_phrases[0])
            self._stop_event.wait()

        proc.join(timeout=5)

    def _processor(self):
        """Single thread: reads utterances, dispatches wake-word transcription async."""
        import concurrent.futures
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="ww-transcribe")
        # pending: future_id → (future, wav_path)
        pending: dict[int, tuple[concurrent.futures.Future, pathlib.Path]] = {}

        try:
            while not self._stop_event.is_set():
                # Drain completed transcriptions first
                for fid in list(pending):
                    fut, wav = pending[fid]
                    if not fut.done():
                        continue
                    del pending[fid]
                    wav.unlink(missing_ok=True)
                    try:
                        text = fut.result()
                    except Exception as e:
                        log.warning("Wake word transcription error: %s", e)
                        text = ""
                    if text and self._has_wake_word(text):
                        log.info("Wake word detected: '%s'", text)
                        self._active = True
                        self.on_wake()
                        trailing = self._extract_trailing(text)
                        if trailing:
                            log.info("Inline command detected: '%s'", trailing)
                            self.on_text_ready(trailing)
                    else:
                        log.debug("No wake word in: '%s'", text)

                try:
                    frames = self._utterance_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                wav = self._save_wav(frames)
                if wav is None:
                    continue

                if self._active:
                    self._active = False
                    self.on_idle()
                    log.info("Active utterance → pipeline")
                    self.on_speech_ready(wav)
                else:
                    log.debug("Checking for wake word (async)…")
                    fut = pool.submit(self._transcriber.transcribe, wav)
                    pending[id(fut)] = (fut, wav)
        finally:
            pool.shutdown(wait=False)

    def _has_wake_word(self, text: str) -> bool:
        low = text.lower().strip()
        # Exact substring match
        if any(phrase in low for phrase in self.wake_phrases):
            return True
        # Fuzzy word-level match — catches Whisper misrecognitions
        # e.g. "pepito" → "pito" (ratio 0.8)
        text_words = low.split()
        for phrase in self.wake_phrases:
            for pw in phrase.split():
                for tw in text_words:
                    ratio = SequenceMatcher(None, pw, tw).ratio()
                    if ratio >= 0.75 and len(pw) >= 4:
                        log.debug("Fuzzy match: '%s' ~ '%s' (%.2f)", pw, tw, ratio)
                        return True
        return False

    def _extract_trailing(self, text: str) -> str | None:
        """Extract text after wake phrase. E.g. 'oye giselo dame la hora' → 'dame la hora'."""
        low = text.lower().strip()
        for phrase in self.wake_phrases:
            idx = low.find(phrase)
            if idx >= 0:
                # Extract after wake phrase + strip
                trailing = text[idx + len(phrase):].strip()
                return trailing if trailing else None
        return None

    def _save_wav(self, frames: list[bytes]) -> pathlib.Path | None:
        try:
            tmp = pathlib.Path(
                tempfile.mktemp(suffix=".wav", prefix="crowia_ao_", dir="/tmp/crowia")
            )
            tmp.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(tmp), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(b"".join(frames))
            return tmp
        except Exception as e:
            log.error("Failed to save WAV: %s", e)
            return None
