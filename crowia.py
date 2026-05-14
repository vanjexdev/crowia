#!/usr/bin/env python3
import argparse
import asyncio
import logging
import pathlib
import sys
import threading

PROJECT_ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from crowia.config import load as load_config
from crowia.hotkey import HotkeyListener
from crowia.recorder import Recorder
from crowia.transcriber import Transcriber
from crowia.assistant import Assistant
from crowia.output import OutputHandler
from crowia.history import ConversationHistory
from crowia.always_on import AlwaysOnListener
from crowia import intent, screen, system_control


def setup_logging(debug: bool = False):
    level = logging.DEBUG if debug else logging.INFO
    log_dir = pathlib.Path("/tmp/crowia")
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "crowia.log"),
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="crowia — voice assistant")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config.yaml"))
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--list-devices", action="store_true",
                        help="List keyboard input devices and exit")
    parser.add_argument("--always-on", action="store_true",
                        help="Always-on mode: wake word + VAD (no hotkey needed)")
    args = parser.parse_args()

    setup_logging(args.debug)

    if args.list_devices:
        import evdev
        from evdev import ecodes
        for path in evdev.list_devices():
            try:
                d = evdev.InputDevice(path)
                has_keys = ecodes.EV_KEY in d.capabilities()
                print(f"{'[KB]' if has_keys else '    '} {path}  {d.name}")
            except PermissionError:
                print(f"[!!] {path}  [PERMISSION DENIED]")
        return

    cfg = load_config(args.config)
    log = logging.getLogger("crowia")

    recorder = Recorder(cfg)
    transcriber = Transcriber(cfg)
    assistant = Assistant(cfg)
    output = OutputHandler(cfg)

    history_cfg = cfg.get("history", {})
    history = ConversationHistory(
        path=pathlib.Path(history_cfg.get("path", "/tmp/crowia/history.json")),
        max_turns=history_cfg.get("max_turns", 10),
    )

    pipeline_lock = threading.Lock()
    safety_timer: threading.Timer | None = None

    def run_pipeline():
        wav = recorder.wav_path
        if wav is None or not wav.exists():
            log.warning("No WAV file after recording")
            return

        output.show_status("Transcribiendo…")
        try:
            text = transcriber.transcribe(wav)
        except Exception as e:
            log.error("Transcription error: %s", e)
            output.show_status(f"Error de transcripción: {e}")
            return
        finally:
            recorder.cleanup(wav)

        if not text:
            output.show_status("No se escuchó nada.")
            return

        log.info("Transcribed: %s", text)

        intents = intent.detect(text)

        # Clear history
        if intents.clear_history:
            history.clear()
            output.show("Crowia", "Historial borrado.")
            return

        # Volume control — handled immediately, no Claude needed
        if intents.volume is not None and not intents.screenshot and not intents.files:
            result = system_control.control_volume(intents.volume)
            output.show("Control de sistema", result)
            return

        # Screenshot
        screenshot_path: pathlib.Path | None = None
        if intents.screenshot:
            output.show_status("Capturando pantalla…")
            screenshot_path = screen.take_screenshot()
            if not screenshot_path:
                output.show_status("Error: grim no disponible.")

        output.show_status(f"Preguntando a Claude: {text[:50]}…")

        try:
            response = assistant.ask(
                text=text,
                history=history.get_messages(),
                image_path=screenshot_path,
                file_paths=intents.files if intents.files else None,
            )
        except Exception as e:
            log.error("Claude error: %s", e)
            output.show_status(f"Error de Claude: {e}")
            return
        finally:
            if screenshot_path and screenshot_path.exists():
                screenshot_path.unlink(missing_ok=True)

        # Also apply volume if mixed intent (e.g. "sube el volumen y dime X")
        if intents.volume is not None and (intents.screenshot or intents.files or True):
            system_control.control_volume(intents.volume)

        history.add("user", text)
        history.add("assistant", response)

        output.show(text, response)

    def on_start():
        nonlocal safety_timer
        if pipeline_lock.locked():
            log.warning("Pipeline already running, ignoring start")
            return
        log.info("Recording started")
        output.show_status("Grabando…")
        recorder.start()

        max_secs = cfg["hotkey"]["max_record_seconds"]
        if cfg["hotkey"]["mode"] == "toggle":
            safety_timer = threading.Timer(max_secs, on_stop)
            safety_timer.daemon = True
            safety_timer.start()

    def on_stop():
        nonlocal safety_timer
        if safety_timer:
            safety_timer.cancel()
            safety_timer = None
        log.info("Recording stopped")
        output.show_status("Procesando…")
        recorder.stop()
        t = threading.Thread(target=_pipeline_wrapper, daemon=True)
        t.start()

    def _pipeline_wrapper():
        with pipeline_lock:
            run_pipeline()

    if args.always_on:
        ao_cfg = cfg.get("always_on", {})
        wake_phrases = ao_cfg.get("wake_phrases", ["oye crowia", "hey crowia"])

        def on_speech_ready(wav_path):
            output.show_status("Procesando…")
            t = threading.Thread(target=_pipeline_from_wav, args=(wav_path,), daemon=True)
            t.start()

        def _pipeline_from_wav(wav_path):
            with pipeline_lock:
                _run_pipeline_wav(wav_path)

        def _run_pipeline_wav(wav_path):
            output.show_status("Transcribiendo…")
            try:
                text = transcriber.transcribe(wav_path)
            except Exception as e:
                log.error("Transcription error: %s", e)
                output.show_status(f"Error de transcripción: {e}")
                return
            finally:
                wav_path.unlink(missing_ok=True)

            if not text:
                output.show_status("No se escuchó nada.")
                return

            log.info("Transcribed: %s", text)
            intents = intent.detect(text)

            if intents.clear_history:
                history.clear()
                output.show("Crowia", "Historial borrado.")
                return

            if intents.volume is not None and not intents.screenshot and not intents.files:
                result = system_control.control_volume(intents.volume)
                output.show("Sistema", result)
                return

            screenshot_path = None
            if intents.screenshot:
                output.show_status("Capturando pantalla…")
                screenshot_path = screen.take_screenshot()

            output.show_status(f"Preguntando a Claude: {text[:50]}…")
            try:
                response = assistant.ask(
                    text=text,
                    history=history.get_messages(),
                    image_path=screenshot_path,
                    file_paths=intents.files or None,
                )
            except Exception as e:
                log.error("Claude error: %s", e)
                output.show_status(f"Error: {e}")
                return
            finally:
                if screenshot_path and screenshot_path.exists():
                    screenshot_path.unlink(missing_ok=True)

            if intents.volume is not None:
                system_control.control_volume(intents.volume)

            history.add("user", text)
            history.add("assistant", response)
            output.show(text, response)

        listener = AlwaysOnListener(
            cfg=cfg,
            on_speech_ready=on_speech_ready,
            transcriber=transcriber,
            on_wake=lambda: output.show_status("Escuchando…"),
            on_idle=lambda: output.show_status(f"Di '{wake_phrases[0]}' para activar"),
        )
        log.info("crowia listo. Modo: always-on | Wake: %s | Whisper: %s",
                 wake_phrases, cfg["whisper"]["model"])
        listener.run()
    else:
        listener = HotkeyListener(
            key_names=cfg["hotkey"]["keys"],
            mode=cfg["hotkey"]["mode"],
            on_start=on_start,
            on_stop=on_stop,
        )
        log.info(
            "crowia listo. Hotkey: %s | Modo: %s | Whisper: %s | Claude: %s",
            cfg["hotkey"]["keys"],
            cfg["hotkey"]["mode"],
            cfg["whisper"]["model"],
            cfg["claude"].get("model", "claude-sonnet-4-6"),
        )
        asyncio.run(listener.run())


if __name__ == "__main__":
    main()
