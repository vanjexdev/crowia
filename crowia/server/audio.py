"""Audio conversion helpers for the web server."""
import io
import pathlib
import struct
import subprocess
import tempfile
import wave


def webm_to_wav(audio_bytes: bytes) -> pathlib.Path:
    """Convert browser audio (WebM/Opus) to 16kHz mono WAV for Whisper."""
    tmp_in = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
    tmp_in.write(audio_bytes)
    tmp_in.close()

    out_path = pathlib.Path(tmp_in.name).with_suffix(".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", tmp_in.name,
         "-ar", "16000", "-ac", "1", "-f", "wav", str(out_path)],
        check=True,
        capture_output=True,
    )
    pathlib.Path(tmp_in.name).unlink(missing_ok=True)
    return out_path


def pcm_to_wav_bytes(pcm: bytes, sample_rate: int = 22050, channels: int = 1) -> bytes:
    """Wrap raw S16_LE PCM in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


def tts_to_wav_bytes(text: str, tts_cmd: list[str]) -> bytes:
    """Run piper-tts and return WAV bytes. tts_cmd must include --output_raw."""
    cmd = [str(pathlib.Path(c).expanduser()) if c.startswith("~") else c for c in tts_cmd]
    proc = subprocess.run(
        cmd,
        input=text.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return pcm_to_wav_bytes(proc.stdout)
