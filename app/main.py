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

from app.sensors import load_live_sensors, compute_wellness_from_sensors, load_all_sensor_data
from app.wellness_engine import analyze_sleep, detect_sedentary, score_hrv, compute_burnout


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
    """
    Return latest raw sensor values (heart_rate, temperature, lux, buzzer)
    """
    data = load_live_sensors()
    if not data:
        return {"error": "no sensor data"}
    # return only the requested keys (do not expose raw payload unless needed)
    return {
        "heart_rate": data.get("heart_rate"),
        "temperature": data.get("temperature"),
        "lux": data.get("lux"),
        "buzzer": data.get("buzzer"),
        "timestamp": data.get("raw", {}).get("timestamp")
    }

@app.get("/wellness")
def wellness_index():
    """
    Compute wellness index using only heart_rate, temperature, lux (no soundDB).
    """
    data = load_live_sensors()
    if not data:
        return {"error": "no sensor data"}

    hr = data.get("heart_rate", 0)
    temp = data.get("temperature", 0)
    lux = data.get("lux", 0)
    buzzer = data.get("buzzer", 0)

    result = compute_wellness_from_sensors(hr, temp, lux)
    return {
        "sensors": {
            "heart_rate": hr,
            "temperature": temp,
            "lux": lux,
            "buzzer": buzzer,
            "timestamp": data.get("raw", {}).get("timestamp")
        },
        "wellness": result
    }

@app.get("/wellness/sleep")
def wellness_sleep():
    """
    Analyze sleep patterns and calculate sleep score.
    """
    sensor_data = load_all_sensor_data()
    if not sensor_data:
        return {"error": "no sensor data available"}
    
    result = analyze_sleep(sensor_data)
    return result

@app.get("/wellness/sedentary")
def wellness_sedentary():
    """
    Detect sedentary behavior during waking hours.
    """
    sensor_data = load_all_sensor_data()
    if not sensor_data:
        return {"error": "no sensor data available"}
    
    result = detect_sedentary(sensor_data)
    return result

@app.get("/wellness/stress")
def wellness_stress():
    """
    Analyze HRV and heart rate for stress assessment.
    """
    sensor_data = load_all_sensor_data()
    if not sensor_data:
        return {"error": "no sensor data available"}
    
    result = score_hrv(sensor_data)
    return result

@app.get("/wellness/burnout")
def wellness_burnout():
    """
    Comprehensive burnout index calculation.
    """
    sensor_data = load_all_sensor_data()
    if not sensor_data:
        return {"error": "no sensor data available"}
    
    result = compute_burnout(sensor_data)
    return result

@app.get("/wellness/complete")
def wellness_complete():
    """
    Get all wellness analyses in one response.
    """
    sensor_data = load_all_sensor_data()
    if not sensor_data:
        return {"error": "no sensor data available"}
    
    # Get latest sensor reading for buzzer status
    latest_sensor = load_live_sensors()
    buzzer_status = latest_sensor.get("buzzer", 0) if latest_sensor else 0
    
    return {
        "sleep": analyze_sleep(sensor_data),
        "sedentary": detect_sedentary(sensor_data),
        "stress": score_hrv(sensor_data),
        "burnout": compute_burnout(sensor_data),
        "buzzer": buzzer_status
    }

@app.get("/wellness/demo")
def wellness_demo():
    """
    Demo endpoint using pre-recorded sleep data for presentations.
    Perfect for demonstrating sleep detection without actually sleeping!
    """
    import json
    import os
    
    demo_file = "demo_sleep_data.json"
    if not os.path.exists(demo_file):
        return {
            "error": "Demo data file not found",
            "message": "Please ensure demo_sleep_data.json exists in the project root"
        }
    
    with open(demo_file, 'r') as f:
        demo_data = json.load(f)
    
    return {
        "message": "Demo data - simulated 24-hour sleep cycle",
        "data_points": len(demo_data),
        "sleep": analyze_sleep(demo_data),
        "sedentary": detect_sedentary(demo_data),
        "stress": score_hrv(demo_data),
        "burnout": compute_burnout(demo_data),
        "sample_readings": demo_data[:3] + demo_data[-3:]  # First 3 and last 3 readings
    }
