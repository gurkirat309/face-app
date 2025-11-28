# app/sensors.py
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Path to the JSON file (adjust if your file is elsewhere)
SENSOR_JSON_PATH = os.path.join(os.getcwd(), "sensor_data.json")

def load_all_sensor_data() -> list:
    """
    Load all sensor records from sensor_data.json.
    Returns list of all sensor readings for historical analysis.
    """
    try:
        if not os.path.exists(SENSOR_JSON_PATH):
            return []

        with open(SENSOR_JSON_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []

        # Try parse as JSON array
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                # single object, wrap in list
                return [parsed]
            else:
                return []
        except Exception:
            # Fallback to JSON-lines
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            return [json.loads(line) for line in lines]

    except Exception as e:
        logger.exception("load_all_sensor_data error: %s", e)
        return []

def load_live_sensors() -> Dict[str, Any]:
    """
    Read the last sensor record from sensor_data.json.
    Supports:
      - JSON array: [ {...}, {...}, ... ] -> returns last element
      - JSON-lines (one JSON per line) -> returns last non-empty line
    Returns dict with keys: heart_rate, temperature, lux
    """
    try:
        if not os.path.exists(SENSOR_JSON_PATH):
            return {}

        with open(SENSOR_JSON_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}

        # Try parse as JSON array
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list) and len(parsed) > 0:
                last = parsed[-1]
            elif isinstance(parsed, dict):
                # single object
                last = parsed
            else:
                last = None
        except Exception:
            # Fallback to JSON-lines: pick last non-empty line
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            if not lines:
                return {}
            last = json.loads(lines[-1])

        if not last:
            return {}

        # Map/normalize keys (handle different naming)
        heart_rate = float(last.get("HR", last.get("heartRate", last.get("heart_rate", 0))))
        temperature = float(last.get("Temp", last.get("temperature", last.get("temp", last.get("tempC", 0)))))
        lux = float(last.get("Lux", last.get("lux", last.get("light", 0))))

        return {
            "heart_rate": heart_rate,
            "temperature": temperature,
            "lux": lux,
            "raw": last
        }

    except Exception as e:
        logger.exception("load_live_sensors error: %s", e)
        return {}

def compute_wellness_from_sensors(heart_rate: float, temperature: float, lux: float) -> Dict[str, Any]:
    """
    Compute a wellness score (0-100) based on heart rate, temperature (C), and lux.
    soundDB has been removed from wellness calculations.
    Returns: {score:float, status:str, breakdown: {...}}
    Tunable logic:
      - heart_rate: ideal 60-100 bpm -> full points; below/above penalized
      - temperature (C): ideal 20-26C for environment
      - lux: low light (<50) slightly penalized, good indoor 100-500, too bright >1000 penalized
    """
    score = 100.0
    breakdown = {}

    # HEART RATE (weight 40%)
    hr_score = 50.0  # base out of 100 for HR subscore then weighted
    if heart_rate <= 0:
        hr_score = 20.0
    else:
        # ideal range 60-100
        if 60 <= heart_rate <= 100:
            hr_score = 100.0
        else:
            # penalize proportionally the further from range
            if heart_rate < 60:
                diff = 60 - heart_rate
            else:
                diff = heart_rate - 100
            # simple decay: larger diff -> lower score
            hr_score = max(0.0, 100.0 - diff * 2.0)  # 2 points per bpm outside
    breakdown["heart_rate_subscore"] = round(hr_score, 2)

    # TEMPERATURE (weight 40%) - environmental temperature
    temp_score = 50.0
    # ideal roughly 20 - 26 C for environment
    if 20 <= temperature <= 26:
        temp_score = 100.0
    else:
        # penalize: temperature outside comfort range
        if temperature < 20:
            diff = 20 - temperature
        else:
            diff = temperature - 26
        temp_score = max(0.0, 100.0 - diff * 10.0)
    breakdown["temperature_subscore"] = round(temp_score, 2)

    # LUX (weight 20%)
    # prefer moderate indoor light: 100 - 1000 lux
    if lux <= 0:
        lux_score = 40.0
    elif 100 <= lux <= 1000:
        lux_score = 100.0
    else:
        # outside preferred range penalize
        if lux < 100:
            # too dark
            lux_score = max(0.0, 100.0 - (100 - lux) * 0.2)  # small penalty per lux below 100
        else:
            # too bright
            lux_score = max(0.0, 100.0 - (lux - 1000) * 0.02)  # mild penalty
    breakdown["lux_subscore"] = round(lux_score, 2)

    # combine with weights
    # weights: HR 40%, Temp 40%, Lux 20% (sum 100)
    total = (breakdown["heart_rate_subscore"] * 0.40 +
             breakdown["temperature_subscore"] * 0.40 +
             breakdown["lux_subscore"] * 0.20)

    total = max(0.0, min(100.0, total))
    if total >= 80:
        status = "excellent"
    elif total >= 60:
        status = "good"
    elif total >= 40:
        status = "moderate"
    else:
        status = "poor"

    return {
        "score": round(total, 2),
        "status": status,
        "breakdown": breakdown
    }
