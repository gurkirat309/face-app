# app/wellness_engine.py
"""
Wellness Analysis Engine for Digital Burnout & Wellness System

Analyzes sensor data to provide:
- Sleep detection & scoring
- Sedentary behavior tracking
- HRV-based stress assessment
- Comprehensive burnout index

Sensor data schema:
{
    "HR": float,          # Heart rate (bpm)
    "RMSSD": float,       # HRV metric (ms)
    "Lux": float,         # Light level
    "Temp": float,        # Temperature (°C)
    "Motion": str,        # "YES" or "NO"
    "timestamp": str      # Optional timestamp
}
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def _parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse timestamp string to datetime object."""
    try:
        # Try common formats
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        return None
    except Exception:
        return None


def _get_current_time() -> datetime:
    """Get current time for analysis."""
    return datetime.now()


def analyze_sleep(sensor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect sleep periods and calculate sleep score.
    
    Sleep detection criteria:
    - Motion: "NO"
    - Light: Lux < 10 (dark environment)
    - Heart Rate: Lower than average (relaxed state)
    - Time: Nighttime hours (22:00 - 08:00) preferred
    
    Args:
        sensor_data: List of sensor readings
        
    Returns:
        {
            "sleep_start": str,
            "sleep_end": str,
            "total_duration_hours": float,
            "sleep_score": float (0-100),
            "sleep_quality": str ("Good" / "OK" / "Poor"),
            "quality_factors": dict
        }
    """
    if not sensor_data:
        return {
            "error": "No sensor data available",
            "sleep_score": 0,
            "sleep_quality": "Unknown"
        }
    
    # Normalize field names
    normalized_data = []
    for record in sensor_data:
        normalized = {
            "hr": float(record.get("HR", record.get("heartRate", 0))),
            "rmssd": float(record.get("RMSSD", record.get("rmssd", 0))),
            "lux": float(record.get("Lux", record.get("lux", 0))),
            "temp": float(record.get("Temp", record.get("temperature", 0))),
            "motion": str(record.get("Motion", record.get("motion", "NO"))).upper(),
            "timestamp": record.get("timestamp", "")
        }
        normalized_data.append(normalized)
    
    # Calculate average HR for baseline
    avg_hr = sum(d["hr"] for d in normalized_data if d["hr"] > 0) / max(1, sum(1 for d in normalized_data if d["hr"] > 0))
    
    # Detect sleep periods (consecutive readings meeting sleep criteria)
    sleep_periods = []
    current_sleep_start = None
    current_sleep_records = []
    
    for i, record in enumerate(normalized_data):
        is_sleeping = (
            record["motion"] == "NO" and
            record["lux"] < 10 and
            (record["hr"] < avg_hr * 0.85 or record["hr"] == 0)  # Relaxed HR or no reading
        )
        
        if is_sleeping:
            if current_sleep_start is None:
                current_sleep_start = i
            current_sleep_records.append(record)
        else:
            # End of sleep period
            if current_sleep_start is not None and len(current_sleep_records) >= 3:
                sleep_periods.append({
                    "start_idx": current_sleep_start,
                    "end_idx": i - 1,
                    "records": current_sleep_records
                })
            current_sleep_start = None
            current_sleep_records = []
    
    # Handle ongoing sleep period
    if current_sleep_start is not None and len(current_sleep_records) >= 3:
        sleep_periods.append({
            "start_idx": current_sleep_start,
            "end_idx": len(normalized_data) - 1,
            "records": current_sleep_records
        })
    
    if not sleep_periods:
        return {
            "sleep_detected": False,
            "sleep_start": None,
            "sleep_end": None,
            "total_duration_hours": 0,
            "sleep_score": 30,
            "sleep_quality": "Poor",
            "quality_factors": {
                "reason": "No sleep period detected in sensor data"
            }
        }
    
    # Use the longest sleep period
    longest_period = max(sleep_periods, key=lambda p: len(p["records"]))
    sleep_duration_hours = len(longest_period["records"]) / 60.0  # Assuming 1 reading per minute
    
    # Calculate sleep score (0-100)
    score = 50.0  # Base score
    quality_factors = {}
    
    # Duration scoring (optimal: 7-9 hours)
    if 7 <= sleep_duration_hours <= 9:
        duration_score = 100
    elif 6 <= sleep_duration_hours < 7 or 9 < sleep_duration_hours <= 10:
        duration_score = 80
    elif sleep_duration_hours < 6:
        duration_score = max(20, 60 - (6 - sleep_duration_hours) * 15)
    else:
        duration_score = max(20, 80 - (sleep_duration_hours - 9) * 10)
    
    quality_factors["duration_score"] = round(duration_score, 1)
    
    # Consistency scoring (low motion throughout)
    motion_consistency = sum(1 for r in longest_period["records"] if r["motion"] == "NO") / len(longest_period["records"])
    consistency_score = motion_consistency * 100
    quality_factors["consistency_score"] = round(consistency_score, 1)
    
    # Environment scoring (darkness)
    avg_lux = sum(r["lux"] for r in longest_period["records"]) / len(longest_period["records"])
    if avg_lux < 5:
        env_score = 100
    elif avg_lux < 20:
        env_score = 70
    else:
        env_score = max(30, 70 - (avg_lux - 20) * 2)
    quality_factors["environment_score"] = round(env_score, 1)
    
    # HRV scoring (higher RMSSD = better recovery)
    avg_rmssd = sum(r["rmssd"] for r in longest_period["records"] if r["rmssd"] > 0) / max(1, sum(1 for r in longest_period["records"] if r["rmssd"] > 0))
    if avg_rmssd > 40:
        hrv_score = 100
    elif avg_rmssd > 20:
        hrv_score = 70 + (avg_rmssd - 20) * 1.5
    else:
        hrv_score = max(30, avg_rmssd * 2)
    quality_factors["hrv_recovery_score"] = round(hrv_score, 1)
    
    # Weighted final score
    final_score = (
        duration_score * 0.35 +
        consistency_score * 0.25 +
        env_score * 0.20 +
        hrv_score * 0.20
    )
    
    # Determine quality label
    if final_score >= 75:
        quality = "Good"
    elif final_score >= 50:
        quality = "OK"
    else:
        quality = "Poor"
    
    # Get timestamps if available
    sleep_start_ts = longest_period["records"][0].get("timestamp", "Unknown")
    sleep_end_ts = longest_period["records"][-1].get("timestamp", "Unknown")
    
    return {
        "sleep_detected": True,
        "sleep_start": sleep_start_ts,
        "sleep_end": sleep_end_ts,
        "total_duration_hours": round(sleep_duration_hours, 2),
        "sleep_score": round(final_score, 1),
        "sleep_quality": quality,
        "quality_factors": quality_factors,
        "current_time": _get_current_time().strftime("%Y-%m-%d %H:%M:%S")
    }


def detect_sedentary(sensor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect sedentary behavior (prolonged sitting) during waking hours.
    
    Ignores sleep periods and tracks continuous inactivity.
    
    Args:
        sensor_data: List of sensor readings
        
    Returns:
        {
            "sedentary_duration_minutes": float,
            "sedentary_status": str ("active" / "sedentary" / "sleeping"),
            "longest_sedentary_period_minutes": float,
            "sedentary_periods": list
        }
    """
    if not sensor_data:
        return {
            "error": "No sensor data available",
            "sedentary_status": "unknown"
        }
    
    # Normalize data
    normalized_data = []
    for record in sensor_data:
        normalized = {
            "hr": float(record.get("HR", record.get("heartRate", 0))),
            "lux": float(record.get("Lux", record.get("lux", 0))),
            "motion": str(record.get("Motion", record.get("motion", "NO"))).upper(),
            "timestamp": record.get("timestamp", "")
        }
        normalized_data.append(normalized)
    
    # First, identify sleep periods (to exclude them)
    avg_hr = sum(d["hr"] for d in normalized_data if d["hr"] > 0) / max(1, sum(1 for d in normalized_data if d["hr"] > 0))
    
    sleep_indices = set()
    for i, record in enumerate(normalized_data):
        is_sleeping = (
            record["motion"] == "NO" and
            record["lux"] < 10 and
            (record["hr"] < avg_hr * 0.85 or record["hr"] == 0)
        )
        if is_sleeping:
            sleep_indices.add(i)
    
    # Detect sedentary periods (awake but no motion)
    sedentary_periods = []
    current_sedentary_start = None
    current_sedentary_count = 0
    
    for i, record in enumerate(normalized_data):
        if i in sleep_indices:
            # Skip sleep periods
            if current_sedentary_start is not None and current_sedentary_count >= 5:
                sedentary_periods.append({
                    "start_idx": current_sedentary_start,
                    "end_idx": i - 1,
                    "duration_minutes": current_sedentary_count
                })
            current_sedentary_start = None
            current_sedentary_count = 0
            continue
        
        # Awake and sedentary: no motion but adequate light
        is_sedentary = (record["motion"] == "NO" and record["lux"] >= 10)
        
        if is_sedentary:
            if current_sedentary_start is None:
                current_sedentary_start = i
            current_sedentary_count += 1
        else:
            # Active period
            if current_sedentary_start is not None and current_sedentary_count >= 5:
                sedentary_periods.append({
                    "start_idx": current_sedentary_start,
                    "end_idx": i - 1,
                    "duration_minutes": current_sedentary_count
                })
            current_sedentary_start = None
            current_sedentary_count = 0
    
    # Handle ongoing sedentary period
    if current_sedentary_start is not None and current_sedentary_count >= 5:
        sedentary_periods.append({
            "start_idx": current_sedentary_start,
            "end_idx": len(normalized_data) - 1,
            "duration_minutes": current_sedentary_count
        })
    
    total_sedentary_minutes = sum(p["duration_minutes"] for p in sedentary_periods)
    longest_period = max((p["duration_minutes"] for p in sedentary_periods), default=0)
    
    # Determine current status
    if normalized_data:
        last_record = normalized_data[-1]
        last_idx = len(normalized_data) - 1
        
        if last_idx in sleep_indices:
            status = "sleeping"
        elif last_record["motion"] == "YES":
            status = "active"
        else:
            status = "sedentary"
    else:
        status = "unknown"
    
    return {
        "sedentary_duration_minutes": round(total_sedentary_minutes, 1),
        "sedentary_status": status,
        "longest_sedentary_period_minutes": round(longest_period, 1),
        "sedentary_periods_count": len(sedentary_periods),
        "recommendation": "Take a 5-minute break every hour" if total_sedentary_minutes > 60 else "Good activity level",
        "current_time": _get_current_time().strftime("%Y-%m-%d %H:%M:%S")
    }


def score_hrv(sensor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze Heart Rate Variability (HRV) for stress assessment.
    
    Higher RMSSD indicates better recovery and lower stress.
    
    Args:
        sensor_data: List of sensor readings
        
    Returns:
        {
            "hrv_score": float (0-100),
            "stress_level": str ("low" / "medium" / "high"),
            "avg_heart_rate": float,
            "avg_rmssd": float,
            "recommendations": list
        }
    """
    if not sensor_data:
        return {
            "error": "No sensor data available",
            "stress_level": "unknown"
        }
    
    # Normalize data
    hr_values = []
    rmssd_values = []
    
    for record in sensor_data:
        hr = float(record.get("HR", record.get("heartRate", 0)))
        rmssd = float(record.get("RMSSD", record.get("rmssd", 0)))
        
        if hr > 0:
            hr_values.append(hr)
        if rmssd > 0:
            rmssd_values.append(rmssd)
    
    if not hr_values:
        return {
            "error": "No valid heart rate data",
            "stress_level": "unknown"
        }
    
    avg_hr = sum(hr_values) / len(hr_values)
    avg_rmssd = sum(rmssd_values) / len(rmssd_values) if rmssd_values else 0
    
    # HRV Score calculation
    # RMSSD ranges: <20 = poor, 20-40 = moderate, 40-60 = good, >60 = excellent
    if avg_rmssd >= 60:
        hrv_score = 95
        stress_level = "low"
    elif avg_rmssd >= 40:
        hrv_score = 70 + (avg_rmssd - 40) * 1.25
        stress_level = "low"
    elif avg_rmssd >= 20:
        hrv_score = 40 + (avg_rmssd - 20) * 1.5
        stress_level = "medium"
    elif avg_rmssd > 0:
        hrv_score = 20 + avg_rmssd
        stress_level = "high"
    else:
        # Fallback to HR-based estimation
        if avg_hr < 70:
            hrv_score = 70
            stress_level = "low"
        elif avg_hr < 85:
            hrv_score = 50
            stress_level = "medium"
        else:
            hrv_score = 30
            stress_level = "high"
    
    # Heart rate variability (calculate standard deviation)
    if len(hr_values) > 1:
        hr_variance = sum((x - avg_hr) ** 2 for x in hr_values) / len(hr_values)
        hr_std = hr_variance ** 0.5
        
        # Higher variability in HR can indicate stress
        if hr_std > 15:
            stress_level = "high" if stress_level != "low" else "medium"
            hrv_score = max(20, hrv_score - 15)
    
    # Recommendations based on stress level
    recommendations = []
    if stress_level == "high":
        recommendations = [
            "Practice deep breathing exercises (4-7-8 technique)",
            "Take regular breaks throughout the day",
            "Consider meditation or mindfulness practice",
            "Ensure adequate sleep (7-9 hours)"
        ]
    elif stress_level == "medium":
        recommendations = [
            "Maintain regular physical activity",
            "Practice stress management techniques",
            "Monitor your sleep quality"
        ]
    else:
        recommendations = [
            "Keep up your healthy habits",
            "Continue regular exercise routine",
            "Maintain good sleep hygiene"
        ]
    
    return {
        "hrv_score": round(hrv_score, 1),
        "stress_level": stress_level,
        "avg_heart_rate": round(avg_hr, 1),
        "avg_rmssd": round(avg_rmssd, 1) if avg_rmssd > 0 else None,
        "heart_rate_variability_std": round(hr_std, 1) if len(hr_values) > 1 else 0,
        "recommendations": recommendations,
        "current_time": _get_current_time().strftime("%Y-%m-%d %H:%M:%S")
    }


def compute_burnout(sensor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute comprehensive burnout index.
    
    Combines:
    - Sleep quality (30%)
    - Sedentary time (25%)
    - Stress/HRV (30%)
    - Environment (15%)
    
    Args:
        sensor_data: List of sensor readings
        
    Returns:
        {
            "burnout_score": float (0-100, higher = more burnout),
            "burnout_level": str ("low" / "medium" / "high"),
            "contributing_factors": dict,
            "recommendations": list
        }
    """
    if not sensor_data:
        return {
            "error": "No sensor data available",
            "burnout_level": "unknown"
        }
    
    # Get component analyses
    sleep_analysis = analyze_sleep(sensor_data)
    sedentary_analysis = detect_sedentary(sensor_data)
    hrv_analysis = score_hrv(sensor_data)
    
    # Calculate component scores (convert to burnout scale where higher = worse)
    
    # Sleep component (30%): invert sleep score
    sleep_score = sleep_analysis.get("sleep_score", 50)
    sleep_burnout = 100 - sleep_score
    
    # Sedentary component (25%): more sedentary = higher burnout
    sedentary_minutes = sedentary_analysis.get("sedentary_duration_minutes", 0)
    if sedentary_minutes > 480:  # >8 hours
        sedentary_burnout = 90
    elif sedentary_minutes > 360:  # >6 hours
        sedentary_burnout = 70
    elif sedentary_minutes > 240:  # >4 hours
        sedentary_burnout = 50
    elif sedentary_minutes > 120:  # >2 hours
        sedentary_burnout = 30
    else:
        sedentary_burnout = 10
    
    # Stress component (30%): invert HRV score
    hrv_score = hrv_analysis.get("hrv_score", 50)
    stress_burnout = 100 - hrv_score
    
    # Environment component (15%): based on temp and light
    normalized_data = []
    for record in sensor_data:
        normalized_data.append({
            "lux": float(record.get("Lux", record.get("lux", 0))),
            "temp": float(record.get("Temp", record.get("temperature", 0)))
        })
    
    avg_lux = sum(d["lux"] for d in normalized_data) / len(normalized_data)
    avg_temp = sum(d["temp"] for d in normalized_data) / len(normalized_data)
    
    # Light scoring (prefer 200-500 lux for work)
    if 200 <= avg_lux <= 500:
        light_burnout = 10
    elif 100 <= avg_lux < 200 or 500 < avg_lux <= 1000:
        light_burnout = 40
    else:
        light_burnout = 70
    
    # Temperature scoring (prefer 20-24°C)
    if 20 <= avg_temp <= 24:
        temp_burnout = 10
    elif 18 <= avg_temp < 20 or 24 < avg_temp <= 26:
        temp_burnout = 40
    else:
        temp_burnout = 70
    
    env_burnout = (light_burnout + temp_burnout) / 2
    
    # Weighted burnout score
    burnout_score = (
        sleep_burnout * 0.30 +
        sedentary_burnout * 0.25 +
        stress_burnout * 0.30 +
        env_burnout * 0.15
    )
    
    # Determine burnout level
    if burnout_score >= 70:
        burnout_level = "high"
    elif burnout_score >= 40:
        burnout_level = "medium"
    else:
        burnout_level = "low"
    
    # Contributing factors breakdown
    contributing_factors = {
        "sleep_impact": round(sleep_burnout, 1),
        "sedentary_impact": round(sedentary_burnout, 1),
        "stress_impact": round(stress_burnout, 1),
        "environment_impact": round(env_burnout, 1),
        "sleep_quality": sleep_analysis.get("sleep_quality", "Unknown"),
        "sedentary_hours": round(sedentary_minutes / 60, 1),
        "stress_level": hrv_analysis.get("stress_level", "Unknown")
    }
    
    # Personalized recommendations
    recommendations = []
    
    if sleep_burnout > 50:
        recommendations.append("Prioritize sleep: aim for 7-9 hours of quality sleep")
    
    if sedentary_burnout > 50:
        recommendations.append("Reduce sedentary time: take breaks every 30-60 minutes")
    
    if stress_burnout > 50:
        recommendations.extend([
            "Practice stress management: meditation, deep breathing",
            "Consider professional support if stress persists"
        ])
    
    if env_burnout > 50:
        recommendations.append("Optimize your environment: adjust lighting and temperature")
    
    if burnout_level == "low":
        recommendations.append("Great job! Maintain your healthy habits")
    
    return {
        "burnout_score": round(burnout_score, 1),
        "burnout_level": burnout_level,
        "contributing_factors": contributing_factors,
        "recommendations": recommendations,
        "component_analyses": {
            "sleep": sleep_analysis,
            "sedentary": sedentary_analysis,
            "stress_hrv": hrv_analysis
        },
        "current_time": _get_current_time().strftime("%Y-%m-%d %H:%M:%S")
    }
