"""
Demo script to test wellness engine functionality
"""
import json
from app.wellness_engine import analyze_sleep, detect_sedentary, score_hrv, compute_burnout

# Load sensor data
with open("sensor_data.json", "r") as f:
    sensor_data = json.load(f)

print("=" * 60)
print("WELLNESS ENGINE DEMONSTRATION")
print("=" * 60)
print(f"\nLoaded {len(sensor_data)} sensor record(s)\n")

# Test 1: Sleep Analysis
print("\n" + "=" * 60)
print("1. SLEEP ANALYSIS")
print("=" * 60)
sleep_result = analyze_sleep(sensor_data)
print(json.dumps(sleep_result, indent=2))

# Test 2: Sedentary Detection
print("\n" + "=" * 60)
print("2. SEDENTARY BEHAVIOR DETECTION")
print("=" * 60)
sedentary_result = detect_sedentary(sensor_data)
print(json.dumps(sedentary_result, indent=2))

# Test 3: HRV/Stress Scoring
print("\n" + "=" * 60)
print("3. HRV & STRESS ANALYSIS")
print("=" * 60)
hrv_result = score_hrv(sensor_data)
print(json.dumps(hrv_result, indent=2))

# Test 4: Burnout Index
print("\n" + "=" * 60)
print("4. COMPREHENSIVE BURNOUT INDEX")
print("=" * 60)
burnout_result = compute_burnout(sensor_data)
# Print without component_analyses for brevity
burnout_summary = {k: v for k, v in burnout_result.items() if k != "component_analyses"}
print(json.dumps(burnout_summary, indent=2))

print("\n" + "=" * 60)
print("DEMONSTRATION COMPLETE")
print("=" * 60)
