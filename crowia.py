#!/usr/bin/env python3
import argparse
import asyncio
import datetime
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
from crowia.memory import MemoryManager
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

    cfg = load_config(args.config)
    log = logging.getLogger("crowia")

    if args.backend:
        cfg["backend"] = args.backend
    if args.hotkey:
        cfg["hotkey"]["keys"] = [k.strip() for k in args.hotkey.split(",")]

    # Qt must be initialized before anything else that touches the display
    overlay = None
    qt_app = None
    ui_queue = None
    if not args.no_ui:
        try:
            import queue
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QTimer
            from crowia.ui import CrowiaOverlay
            qt_app = QApplication(sys.argv)
            overlay = CrowiaOverlay(cfg=cfg)
            overlay.show()
            ui_queue = queue.Queue()
            # Process UI queue every 50ms
            def process_ui_queue():
                try:
                    while True:
                        fn, args, kwargs = ui_queue.get_nowait()
                        fn(*args, **kwargs)
                except queue.Empty:
                    pass
            timer = QTimer()
            timer.timeout.connect(process_ui_queue)
            timer.start(50)
        except Exception as e:
            logging.getLogger("crowia").warning("UI unavailable: %s", e)
            overlay = None
            ui_queue = None

    recorder = Recorder(cfg)
    transcriber = Transcriber(cfg)
    assistant = Assistant(cfg)
    memory = MemoryManager()
    assistant.set_memory_context(memory.build_memory_prompt())

    def _save_memory():
        msgs = history.get_messages()
        if msgs:
            try:
                memory.save_session(msgs, lambda p: assistant.ask(text=p))
            except Exception as e:
                log.warning("Memory save on exit failed: %s", e)

    def on_cancel():
        log.info("Cancel requested")
        assistant.cancel()
        if overlay:
            overlay.notify("idle")

    output = OutputHandler(cfg)

    if overlay:
        overlay._on_cancel = on_cancel
        overlay.set_backend(assistant.current_backend_name)
        overlay.tts_toggled.connect(output.set_tts)
        overlay.skip_tts.connect(output.stop_tts)
        output.set_tts(overlay._tts_enabled)  # sync prefs → output on startup

    history_cfg = cfg.get("history", {})
    history = ConversationHistory(
        path=pathlib.Path(history_cfg.get("path", "/tmp/crowia/history.json")),
        max_turns=history_cfg.get("max_turns", 10),
    )

    pipeline_lock = threading.Lock()
    safety_timer: threading.Timer | None = None

    def ui(state: str):
        if overlay:
            if ui_queue:
                ui_queue.put((overlay.notify, (state,), {}))
            else:
                overlay.notify(state)

    def thread_safe_show_status(msg: str):
        if ui_queue:
            ui_queue.put((output.show_status, (msg,), {}))
        else:
            output.show_status(msg)

    def _handle_intents(intents, text: str) -> bool:
        """Handle quick intents. Returns True if handled (skip LLM)."""
        if intents.switch_backend:
            msg = assistant.switch_backend(intents.switch_backend)
            if overlay:
                overlay.set_backend(assistant.current_backend_name)
            output.show("Giselo", msg)
            ui("done")
            return True
        if intents.tts_mute:
            output.set_tts(False)
            if overlay:
                overlay.set_tts_state(False)
            output.show("Giselo", "Audio desactivado.")
            ui("done")
            return True
        if intents.tts_unmute:
            output.set_tts(True)
            if overlay:
                overlay.set_tts_state(True)
            output.show("Giselo", "Audio activado.")
            ui("done")
            return True
        if intents.skill_disable:
            output.show("Giselo", assistant.disable_skill(intents.skill_disable))
            ui("done")
            return True
        if intents.skill_enable:
            output.show("Giselo", assistant.enable_skill(intents.skill_enable))
            ui("done")
            return True
        if intents.skill_list:
            output.show("Giselo", assistant.list_skills())
            ui("done")
            return True
        if intents.clear_history:
            history.clear()
            output.show("Crowia", "Historial borrado.")
            ui("done")
            return True
        if intents.media is not None:
            output.show("Media", system_control.control_media(intents.media))
            ui("done")
            return True
        if intents.volume is not None and not intents.screenshot and not intents.files:
            output.show("Sistema", system_control.control_volume(intents.volume))
            ui("done")
            return True
        return False

    def _run_text_pipeline(text: str, extra_files: list[pathlib.Path] | None = None):
        """Shared pipeline for voice transcription and typed text input."""
        ui("processing")
        log.info("Text pipeline: %s", text)
        intents = intent.detect(text)

        if _handle_intents(intents, text):
            return

        screenshot_path = None
        if intents.screenshot:
            output.show_status("Capturando pantalla…")
            screenshot_path = screen.take_screenshot()

        file_paths = list(intents.files or [])
        if extra_files:
            file_paths.extend(extra_files)

        output.show_status(f"Preguntando a {assistant.current_backend_name}: {text[:50]}…")

        def _on_chunk(partial: str):
            if overlay:
                overlay.set_response(partial)

        try:
            response = assistant.ask(
                text=text,
                history=history.get_messages(),
                image_path=screenshot_path,
                file_paths=file_paths or None,
                on_chunk=_on_chunk if overlay else None,
            )
        except Exception as e:
            log.error("Assistant error: %s", e)
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

    def _on_text_submitted(text: str, file_strs: list):
        files = [pathlib.Path(p) for p in file_strs]
        def _wrapper():
            with pipeline_lock:
                _run_text_pipeline(text, files)
        threading.Thread(target=_wrapper, daemon=True).start()

    def _handle_save_memory():
        msgs = history.get_messages()
        if not msgs:
            output.show("Crowia", "No hay historial que recordar.")
            return
        mem_dir = pathlib.Path.home() / ".config/crowia/memories"
        mem_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        mem_file = mem_dir / f"memory_{ts}.txt"
        lines = [f"[{m.get('role','?')}]\n{m.get('content','')}\n" for m in msgs]
        mem_file.write_text("\n".join(lines), encoding="utf-8")
        output.show("Crowia", f"Memoria guardada: {mem_file.name}")

    def _handle_export_summary():
        msgs = history.get_messages()
        if not msgs:
            output.show("Crowia", "No hay historial que exportar.")
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = pathlib.Path.home() / "Documents" / "crowia_exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_file = export_dir / f"chat_{ts}.txt"
        lines = [f"--- {m.get('role','?').upper()} ---\n{m.get('content','')}\n" for m in msgs]
        export_file.write_text("\n".join(lines), encoding="utf-8")
        output.show("Crowia", f"Exportado: {export_file}")

    if overlay:
        overlay.text_submitted.connect(_on_text_submitted)
        overlay.save_memory.connect(_handle_save_memory)
        overlay.export_summary.connect(_handle_export_summary)

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
            ui("idle")
            return
        finally:
            recorder.cleanup(wav)

        if not text:
            output.show_status("No se escuchó nada.")
            ui("idle")
            return

        _run_text_pipeline(text)

    def on_start():
        nonlocal safety_timer
        if not pipeline_lock.acquire(blocking=False):
            log.warning("Pipeline already running, ignoring start")
            return
        pipeline_lock.release()  # Just checking availability

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
            _run_text_pipeline(text)

        listener = AlwaysOnListener(
            cfg=cfg,
            on_speech_ready=on_speech_ready,
            transcriber=transcriber,
            on_wake=lambda: (ui("recording"), thread_safe_show_status("Escuchando…")),
            on_idle=lambda: (ui("idle"), thread_safe_show_status(f"Di '{wake_phrases[0]}' para activar")),
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
        def _run_hotkey_listener():
            asyncio.run(listener.run())
        t = threading.Thread(target=_run_hotkey_listener, daemon=True)
        t.start()

        def _on_hotkey_changed(new_keys: list):
            nonlocal listener, t
            log.info("Hotkey changed to: %s", new_keys)
            listener.stop()
            # Save to config.local.yaml
            import yaml
            local_path = PROJECT_ROOT / "config.local.yaml"
            local_raw = {}
            if local_path.exists():
                with open(local_path, encoding="utf-8") as f:
                    local_raw = yaml.safe_load(f) or {}
            local_raw.setdefault("hotkey", {})["keys"] = new_keys
            with open(local_path, "w", encoding="utf-8") as f:
                yaml.dump(local_raw, f, allow_unicode=True)
            cfg["hotkey"]["keys"] = new_keys
            # Start new listener
            new_listener = HotkeyListener(
                key_names=new_keys,
                mode=cfg["hotkey"]["mode"],
                on_start=on_start,
                on_stop=on_stop,
            )
            listener = new_listener
            nt = threading.Thread(target=lambda: asyncio.run(new_listener.run()), daemon=True)
            nt.start()
            log.info("Hotkey listener restarted with: %s", new_keys)

        if overlay:
            overlay.hotkey_changed.connect(_on_hotkey_changed)

    if qt_app:
        import signal
        signal.signal(signal.SIGINT, lambda *_: qt_app.quit())
        qt_app.aboutToQuit.connect(_save_memory)
        # Timer trick: let Python check signals every 500ms (Qt blocks signal delivery)
        from PyQt6.QtCore import QTimer
        sig_timer = QTimer()
        sig_timer.start(500)
        sig_timer.timeout.connect(lambda: None)
        sys.exit(qt_app.exec())
    else:
        # No UI — block main thread
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            _save_memory()


if __name__ == "__main__":
    main()
