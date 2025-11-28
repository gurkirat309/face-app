"""
Sleep Detection Demo Script
============================

This script demonstrates the sleep detection feature using pre-recorded data.
Perfect for presentations and demos where the person can't actually sleep!

Usage:
    python demo_sleep_detection.py
"""

import json
import time
from app.wellness_engine import analyze_sleep

def load_demo_data():
    """Load the demo sleep data."""
    with open('demo_sleep_data.json', 'r') as f:
        return json.load(f)

def display_sensor_reading(reading, index, total):
    """Display a single sensor reading in a nice format."""
    print(f"\n{'='*60}")
    print(f"Reading {index + 1}/{total} - {reading.get('timestamp', 'N/A')}")
    print(f"{'='*60}")
    print(f"💓 Heart Rate: {reading['heartRate']} bpm")
    print(f"📊 HRV (RMSSD): {reading['rmssd']} ms")
    print(f"💡 Light Level: {reading['lux']} lux")
    print(f"🌡️  Temperature: {reading['tempC']}°C")
    print(f"🏃 Motion: {'YES' if reading['motion'] == 1 else 'NO'}")
    
    # Determine current state
    if reading['motion'] == 0 and reading['lux'] < 10 and reading['heartRate'] < 65:
        state = "😴 SLEEPING"
        color = "\033[94m"  # Blue
    elif reading['motion'] == 0 and reading['lux'] < 100:
        state = "😌 RELAXING"
        color = "\033[93m"  # Yellow
    else:
        state = "👁️  AWAKE"
        color = "\033[92m"  # Green
    
    print(f"\n{color}Current State: {state}\033[0m")
    print(f"{'='*60}")

def run_live_demo():
    """Run a live demonstration showing sensor readings over time."""
    print("\n" + "="*60)
    print("🛌 SLEEP DETECTION DEMO - Live Simulation")
    print("="*60)
    print("\nThis demo simulates a full sleep cycle from evening to morning.")
    print("Watch how the sensor values change and sleep is detected!\n")
    
    input("Press ENTER to start the demo...")
    
    demo_data = load_demo_data()
    
    # Show each reading with a delay
    for i, reading in enumerate(demo_data):
        display_sensor_reading(reading, i, len(demo_data))
        
        if i < len(demo_data) - 1:
            print("\n⏳ Next reading in 2 seconds...")
            time.sleep(2)
    
    # Now analyze the complete sleep data
    print("\n\n" + "="*60)
    print("📊 COMPLETE SLEEP ANALYSIS")
    print("="*60)
    
    analysis = analyze_sleep(demo_data)
    
    print(f"\n✅ Sleep Detected: {analysis.get('sleep_detected', False)}")
    print(f"🛌 Sleep Start: {analysis.get('sleep_start', 'N/A')}")
    print(f"⏰ Sleep End: {analysis.get('sleep_end', 'N/A')}")
    print(f"⏱️  Total Duration: {analysis.get('total_duration_hours', 0)} hours")
    print(f"📈 Sleep Score: {analysis.get('sleep_score', 0)}/100")
    print(f"⭐ Sleep Quality: {analysis.get('sleep_quality', 'Unknown')}")
    
    if 'quality_factors' in analysis:
        print(f"\n📊 Quality Breakdown:")
        factors = analysis['quality_factors']
        print(f"  - Duration Score: {factors.get('duration_score', 0)}/100")
        print(f"  - Consistency Score: {factors.get('consistency_score', 0)}/100")
        print(f"  - Environment Score: {factors.get('environment_score', 0)}/100")
        print(f"  - HRV Recovery Score: {factors.get('hrv_recovery_score', 0)}/100")
    
    print("\n" + "="*60)
    print("✨ Demo Complete!")
    print("="*60 + "\n")

def run_quick_demo():
    """Quick demo showing just the analysis results."""
    print("\n" + "="*60)
    print("🛌 SLEEP DETECTION DEMO - Quick Analysis")
    print("="*60)
    
    demo_data = load_demo_data()
    analysis = analyze_sleep(demo_data)
    
    print(json.dumps(analysis, indent=2))
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    import sys
    
    print("\n🎭 Sleep Detection Demo Options:")
    print("1. Live simulation (shows each reading)")
    print("2. Quick analysis (shows final results only)")
    
    choice = input("\nSelect option (1 or 2): ").strip()
    
    if choice == "1":
        run_live_demo()
    elif choice == "2":
        run_quick_demo()
    else:
        print("Invalid choice. Running live demo by default...")
        run_live_demo()
