"""Giselo Web Server — FastAPI + WebSocket."""
import asyncio
import json
import logging
import pathlib
import sys
import threading

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import os

from crowia.config import load as load_config
from crowia.transcriber import Transcriber
from crowia.assistant import Assistant
from crowia.history import ConversationHistory
from crowia.server.audio import webm_to_wav, tts_to_wav_bytes

log = logging.getLogger("giselo.server")

WEB_DIR = pathlib.Path(__file__).parent / "web"

cfg = load_config(os.environ.get("CROWIA_CONFIG"))
transcriber = Transcriber(cfg)
assistant = Assistant(cfg)
history = ConversationHistory(
    path=pathlib.Path(cfg["history"]["path"]),
    max_turns=cfg["history"]["max_turns"],
)

app = FastAPI(title="Giselo Web")
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/manifest.json")
async def manifest():
    return FileResponse(WEB_DIR / "manifest.json")


@app.get("/sw.js")
async def sw():
    return FileResponse(WEB_DIR / "sw.js", media_type="application/javascript")


@app.get("/api/history")
async def get_history():
    return JSONResponse({"messages": history.get_messages()})


@app.delete("/api/history")
async def clear_history():
    history.clear()
    return JSONResponse({"ok": True})


@app.get("/api/status")
async def status():
    return JSONResponse({
        "backend": assistant.current_backend_name,
        "model": cfg["claude"].get("model", ""),
        "tts": cfg["output"].get("tts_enabled", False),
    })


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    loop = asyncio.get_event_loop()
    tts_cmd = cfg["output"].get("tts_command", [])
    tts_enabled = cfg["output"].get("tts_enabled", False)

    async def send(obj: dict):
        try:
            await ws.send_json(obj)
        except Exception:
            pass

    async def send_bytes(data: bytes):
        try:
            await ws.send_bytes(data)
        except Exception:
            pass

    async def run_pipeline(text: str):
        await send({"type": "status", "message": f"Preguntando a {assistant.current_backend_name}…"})

        partial_buf = []

        def on_chunk(chunk: str):
            partial_buf.append(chunk)
            asyncio.run_coroutine_threadsafe(
                send({"type": "chunk", "content": chunk}),
                loop,
            )

        try:
            response = await loop.run_in_executor(
                None,
                lambda: assistant.ask(
                    text=text,
                    history=history.get_messages(),
                    on_chunk=on_chunk,
                ),
            )
        except Exception as e:
            await send({"type": "error", "message": str(e)})
            return

        history.add("user", text)
        history.add("assistant", response)
        await send({"type": "done", "content": response})

        if tts_enabled and tts_cmd:
            log.info("TTS: generating audio (%d chars)…", len(response))
            await send({"type": "audio_start"})
            try:
                wav = await loop.run_in_executor(
                    None,
                    lambda: tts_to_wav_bytes(response, tts_cmd),
                )
                log.info("TTS: sending %d bytes", len(wav))
                await send_bytes(wav)
                log.info("TTS: sent OK")
            except Exception as e:
                log.warning("TTS failed: %s", e, exc_info=True)
            await send({"type": "audio_end"})
        else:
            log.info("TTS skipped: enabled=%s cmd=%s", tts_enabled, bool(tts_cmd))

    try:
        audio_chunks: list[bytes] = []
        collecting_audio = False

        while True:
            msg = await ws.receive()

            if "bytes" in msg and msg["bytes"]:
                audio_chunks.append(msg["bytes"])
                continue

            if "text" not in msg or not msg["text"]:
                continue

            data = json.loads(msg["text"])
            mtype = data.get("type")

            if mtype == "text":
                await run_pipeline(data["content"].strip())

            elif mtype == "voice_start":
                audio_chunks = []
                collecting_audio = True
                await send({"type": "status", "message": "Grabando…"})

            elif mtype == "voice_end":
                collecting_audio = False
                if not audio_chunks:
                    await send({"type": "error", "message": "No se recibió audio."})
                    continue

                await send({"type": "status", "message": "Transcribiendo…"})
                raw = b"".join(audio_chunks)
                audio_chunks = []

                try:
                    wav_path = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: webm_to_wav(raw)
                    )
                    text = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: transcriber.transcribe(wav_path)
                    )
                    wav_path.unlink(missing_ok=True)
                except Exception as e:
                    await send({"type": "error", "message": f"Transcripción falló: {e}"})
                    continue

                if not text:
                    await send({"type": "error", "message": "No se escuchó nada."})
                    continue

                await send({"type": "transcript", "content": text})
                await run_pipeline(text)

            elif mtype == "clear_history":
                history.clear()
                await send({"type": "status", "message": "Historial borrado."})

            elif mtype == "switch_backend":
                msg_out = assistant.switch_backend(data.get("backend", ""))
                await send({"type": "status", "message": msg_out})
                await send({"type": "backend", "name": assistant.current_backend_name})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error("WS error: %s", e)
