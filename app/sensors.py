# app/sensors.py  (recommended)
import os, json, logging

logger = logging.getLogger(__name__)

SENSOR_JSON_PATH = "sensor_data.json"   # adjust if needed

def load_live_sensors():
    """
    Reads the latest sensor data from sensor_data.json.
    Supports:
      - Single JSON: {"heartRate":90, "tempF":82,...}
      - JSON-lines:   each line JSON → reads the last line
    """
    try:
        if not os.path.exists(SENSOR_JSON_PATH):
            return {}

        with open(SENSOR_JSON_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}

            lines = [l.strip() for l in content.splitlines() if l.strip()]
            last = lines[-1]

            data = json.loads(last)

        return {
            "heart_rate": float(data.get("heartRate", data.get("heart_rate", 0))),
            "temperature": float(data.get("tempF", data.get("temperature", 0))),
            "light": int(data.get("light", 0)),
            "sound_db": float(data.get("sound", data.get("sound_db", 0)))
        }

    except Exception as e:
        logger.warning(f"load_live_sensors error: {e}")
        return {}
# app/sensors.py (continue)

def compute_wellness(heart_rate, temperature, light, sound_db):
    """
    Returns a wellness_score between 0–100 and classification label.
    Modify weights freely.
    """

    score = 100

    # Heart rate
    if heart_rate <= 0:
        score -= 30
    elif heart_rate < 50 or heart_rate > 110:
        score -= 20

    # Temperature (F)
    if temperature < 96 or temperature > 100:
        score -= 20

    # Light
    if light < 1:      # dark
        score -= 10
    elif light > 800:  # too bright
        score -= 10

    # Sound (dB)
    if sound_db > 80:
        score -= 20
    elif sound_db > 60:
        score -= 10

    # clamp
    score = max(0, min(100, score))

    if score >= 80:
        status = "excellent"
    elif score >= 60:
        status = "good"
    elif score >= 40:
        status = "moderate"
    else:
        status = "poor"

    return score, status
