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
    parser.add_argument("--no-ui", action="store_true", help="Disable graphical overlay")
    parser.add_argument("--list-devices", action="store_true",
                        help="List keyboard input devices and exit")
    parser.add_argument("--always-on", action="store_true",
                        help="Always-on mode: wake word + VAD (no hotkey needed)")
    parser.add_argument("--backend", choices=["claude", "opencode", "codex"],
                        help="Override backend from config (claude|opencode|codex)")
    parser.add_argument("--hotkey",
                        help="Override hotkey combo, comma-separated evdev names "
                             "(e.g. KEY_LEFTCTRL,KEY_LEFTSHIFT,KEY_LEFTALT,KEY_1)")
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

    # Qt must be initialized before anything else that touches the display
    overlay = None
    qt_app = None
    if not args.no_ui:
        try:
            from PyQt6.QtWidgets import QApplication
            from crowia.ui import CrowiaOverlay
            qt_app = QApplication(sys.argv)
            overlay = CrowiaOverlay()
            overlay.show()
        except Exception as e:
            logging.getLogger("crowia").warning("UI unavailable: %s", e)
            overlay = None

    cfg = load_config(args.config)
    log = logging.getLogger("crowia")

    if args.backend:
        cfg["backend"] = args.backend
    if args.hotkey:
        cfg["hotkey"]["keys"] = [k.strip() for k in args.hotkey.split(",")]

    recorder = Recorder(cfg)
    transcriber = Transcriber(cfg)
    assistant = Assistant(cfg)

    def on_cancel():
        log.info("Cancel requested")
        assistant.cancel()
        if overlay:
            overlay.notify("idle")

    if overlay:
        overlay._on_cancel = on_cancel
        overlay.set_backend(assistant.current_backend_name)
    output = OutputHandler(cfg)

    history_cfg = cfg.get("history", {})
    history = ConversationHistory(
        path=pathlib.Path(history_cfg.get("path", "/tmp/crowia/history.json")),
        max_turns=history_cfg.get("max_turns", 10),
    )

    pipeline_lock = threading.Lock()
    safety_timer: threading.Timer | None = None

    def ui(state: str):
        if overlay:
            overlay.notify(state)

    def run_pipeline():
        wav = recorder.wav_path
        if wav is None or not wav.exists():
            log.warning("No WAV file after recording")
            return

        ui("processing")
        output.show_status("Transcribiendo…")
        try:
            text = transcriber.transcribe(wav)
        except Exception as e:
            log.error("Transcription error: %s", e)
            output.show_status(f"Error de transcripción: {e}")
            ui("idle")
            return
        finally:
            recorder.cleanup(wav)

        if not text:
            output.show_status("No se escuchó nada.")
            ui("idle")
            return

        log.info("Transcribed: %s", text)
        log.debug("Detecting intents...")
        intents = intent.detect(text)
        log.debug("Intents: screenshot=%s volume=%s files=%s backend=%s",
                  intents.screenshot, intents.volume, intents.files, intents.switch_backend)

        if intents.switch_backend:
            msg = assistant.switch_backend(intents.switch_backend)
            if overlay:
                overlay.set_backend(assistant.current_backend_name)
            output.show("Giselo", msg)
            ui("done")
            return

        if intents.clear_history:
            history.clear()
            output.show("Crowia", "Historial borrado.")
            ui("done")
            return

        if intents.volume is not None and not intents.screenshot and not intents.files:
            result = system_control.control_volume(intents.volume)
            output.show("Control de sistema", result)
            ui("done")
            return

        screenshot_path: pathlib.Path | None = None
        if intents.screenshot:
            output.show_status("Capturando pantalla…")
            screenshot_path = screen.take_screenshot()

        log.debug("Calling assistant.ask (backend=%s)...", assistant.current_backend_name)
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
            ui("idle")
            return
        finally:
            if screenshot_path and screenshot_path.exists():
                screenshot_path.unlink(missing_ok=True)

        if intents.volume is not None:
            system_control.control_volume(intents.volume)

        history.add("user", text)
        history.add("assistant", response)
        output.show(text, response)
        if overlay:
            overlay.set_response(response)
        ui("done")

    def on_start():
        nonlocal safety_timer
        if pipeline_lock.locked():
            log.warning("Pipeline already running, ignoring start")
            return
        log.info("Recording started")
        ui("recording")
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
        ui("processing")
        output.show_status("Procesando…")
        recorder.stop()
        t = threading.Thread(target=_pipeline_wrapper, daemon=True)
        t.start()

    def _pipeline_wrapper():
        with pipeline_lock:
            run_pipeline()

    if args.always_on:
        ao_cfg = cfg.get("always_on", {})
        wake_phrases = ao_cfg.get("wake_phrases", ["oye giselo", "hey giselo"])

        def on_speech_ready(wav_path):
            ui("processing")
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
                output.show_status(f"Error: {e}")
                ui("idle")
                return
            finally:
                wav_path.unlink(missing_ok=True)

            if not text:
                output.show_status("No se escuchó nada.")
                ui("idle")
                return

            log.info("Transcribed: %s", text)
            intents = intent.detect(text)

            if intents.switch_backend:
                msg = assistant.switch_backend(intents.switch_backend)
                if overlay:
                    overlay.set_backend(assistant.current_backend_name)
                output.show("Giselo", msg)
                ui("done")
                return

            if intents.clear_history:
                history.clear()
                output.show("Crowia", "Historial borrado.")
                ui("done")
                return

            if intents.volume is not None and not intents.screenshot and not intents.files:
                result = system_control.control_volume(intents.volume)
                output.show("Sistema", result)
                ui("done")
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
                ui("idle")
                return
            finally:
                if screenshot_path and screenshot_path.exists():
                    screenshot_path.unlink(missing_ok=True)

            if intents.volume is not None:
                system_control.control_volume(intents.volume)

            history.add("user", text)
            history.add("assistant", response)
            output.show(text, response)
            if overlay:
                overlay.set_response(response)
            ui("done")

        listener = AlwaysOnListener(
            cfg=cfg,
            on_speech_ready=on_speech_ready,
            transcriber=transcriber,
            on_wake=lambda: (ui("recording"), output.show_status("Escuchando…")),
            on_idle=lambda: (ui("idle"), output.show_status(f"Di '{wake_phrases[0]}' para activar")),
        )
        log.info("crowia listo. Modo: always-on | Wake: %s | Whisper: %s",
                 wake_phrases, cfg["whisper"]["model"])
        t = threading.Thread(target=listener.run, daemon=True)
        t.start()

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
        t = threading.Thread(target=lambda: asyncio.run(listener.run()), daemon=True)
        t.start()

    if qt_app:
        import signal
        signal.signal(signal.SIGINT, lambda *_: qt_app.quit())
        # Timer trick: let Python check signals every 500ms (Qt blocks signal delivery)
        from PyQt6.QtCore import QTimer
        sig_timer = QTimer()
        sig_timer.start(500)
        sig_timer.timeout.connect(lambda: None)
        sys.exit(qt_app.exec())
    else:
        # No UI — block main thread
        threading.Event().wait()


if __name__ == "__main__":
    main()
