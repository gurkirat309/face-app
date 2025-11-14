# app/main.py
import os
import tempfile
import base64
import json
import logging
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.infer import predict_frame    # ensure this file exposes predict_frame
from app.voice_infer import predict_emotion_from_wav_file  # returns same dict shape as before
from app.sensors import load_live_sensors, compute_wellness

logger = logging.getLogger(__name__)

app = FastAPI(title="Face+Voice Emotion Demo (stable)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket connected")
    try:
        while True:
            text = await ws.receive_text()
            # Expect JSON envelope
            try:
                obj = json.loads(text)
            except Exception:
                # if not JSON, ignore
                await ws.send_json({"type":"error", "message":"invalid json"})
                continue

            typ = obj.get("type", "video")
            # --- Video frames (fast) ---
            if typ == "video":
                data = obj.get("data")
                if not data:
                    await ws.send_json({"type":"error", "message":"no frame data"})
                    continue
                # Predict synchronously (should be fast). If heavy, consider using to_thread too.
                try:
                    res = predict_frame(data)
                    res["type"] = "video"
                    await ws.send_json(res)
                except Exception as e:
                    logger.exception("Error during video predict")
                    await ws.send_json({"type":"video", "top_label":"error", "detections":[]})

            # --- Audio analyze (only on user 'Analyze' press) ---
            elif typ == "audio":
                action = obj.get("action", "analyze")
                data = obj.get("data")
                fmt = obj.get("format", "wav")
                if action != "analyze":
                    await ws.send_json({"type":"audio", "message":"unsupported action"})
                    continue
                if not data:
                    await ws.send_json({"type":"audio", "error":"no audio data"})
                    continue

                # We only support wav format (no ffmpeg). If not wav, return helpful error.
                if fmt != "wav":
                    await ws.send_json({"type":"audio", "error": "server expects WAV format. Please record/send WAV."})
                    continue

                # decode and save to temporary file
                try:
                    b64 = data.split(",", 1)[1] if "," in data else data
                    audio_bytes = base64.b64decode(b64)
                except Exception as e:
                    logger.exception("Failed to decode base64 audio")
                    await ws.send_json({"type":"audio", "error":"failed to decode audio base64"})
                    continue

                tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                try:
                    tmp_wav.write(audio_bytes)
                    tmp_wav.flush()
                    tmp_wav.close()
                except Exception:
                    try:
                        tmp_wav.close()
                    except:
                        pass

                # Run the (potentially slow) audio model in a thread to avoid blocking the event loop
                try:
                    predict_res = await asyncio.to_thread(predict_emotion_from_wav_file, tmp_wav.name)
                except Exception:
                    logger.exception("Audio prediction failed")
                    predict_res = {"error": "audio prediction failed"}
                finally:
                    # cleanup temp file
                    try:
                        os.unlink(tmp_wav.name)
                    except Exception:
                        pass

                # send result to client
                if isinstance(predict_res, dict):
                    predict_res["type"] = "audio"
                else:
                    predict_res = {"type":"audio", "error":"invalid model response"}
                await ws.send_json(predict_res)

            else:
                await ws.send_json({"type":"error", "message":"unknown message type"})
    except WebSocketDisconnect:
        logger.info("Websocket disconnected")
    except Exception:
        logger.exception("Unexpected websocket error")
@app.get("/sensors")
def get_sensors():
    """Return latest raw sensor readings."""
    return load_live_sensors()

@app.get("/wellness")
def get_wellness():
    """
    Returns overall wellness score + classification.
    Combines heart rate, temperature, light, sound.
    """
    sensors = load_live_sensors()
    if not sensors:
        return {"error": "No sensor data available"}

    score, status = compute_wellness(
        sensors.get("heart_rate", 0),
        sensors.get("temperature", 0),
        sensors.get("light", 0),
        sensors.get("sound_db", 0),
    )

    return {
        "sensors": sensors,
        "wellness_score": score,
        "wellness_status": status
    }        
