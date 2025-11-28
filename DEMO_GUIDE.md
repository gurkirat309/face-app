# 🎭 Sleep Detection Demo Guide

## Problem: How to Demo Sleep Detection Without Actually Sleeping?

You can't sleep during a presentation, but you still need to demonstrate the sleep detection feature. Here are **3 practical solutions**:

---

## ✅ **Option 1: Use the Demo Script** (Recommended)

Run the interactive demo that simulates a complete sleep cycle:

```bash
python demo_sleep_detection.py
```

**What it does:**
- Shows sensor readings changing from awake → sleeping → awake
- Displays real-time status updates
- Provides complete sleep analysis at the end
- Takes about 20 seconds to run

**Demo Flow:**
1. Evening (awake): High heart rate, lights on, movement
2. Getting sleepy: Heart rate drops, lights dim
3. Deep sleep: Very low heart rate, dark, no motion
4. Morning (waking): Heart rate rises, lights on, movement

---

## ✅ **Option 2: Use the Demo API Endpoint**

Start your server and visit the demo endpoint:

```bash
# Start the server
uvicorn app.main:app --reload

# Then visit in browser or curl:
http://localhost:8000/wellness/demo
```

**What you get:**
- Complete sleep analysis using simulated data
- Sedentary behavior analysis
- Stress/HRV assessment
- Burnout index
- Sample sensor readings showing the transition

**Perfect for:** API demonstrations, Postman testing, frontend integration demos

---

## ✅ **Option 3: Simulate Sleep Conditions Live**

Manually create "sleep-like" conditions with your actual hardware:

### Step-by-Step:

1. **Cover the light sensor** (or turn off lights)
   - Target: `lux < 10`
   
2. **Stay completely still** for 30-60 seconds
   - Target: `motion = 0`
   
3. **Relax and breathe slowly**
   - Deep, slow breaths will lower your heart rate
   - Target: `heartRate < average * 0.85`

### Demo Script:
```
"I'll now simulate sleep conditions:
- [Cover light sensor] → Lux drops below 10
- [Sit very still] → Motion sensor shows 0
- [Breathe slowly] → Heart rate decreases

Watch the API detect 'sleeping' status in real-time!"
```

**Check status:**
```bash
curl http://localhost:8000/wellness/sleep
```

---

## 📊 **Sleep Detection Criteria**

The system detects sleep when **ALL** these conditions are met:

| Sensor | Sleep Condition | Typical Value |
|--------|----------------|---------------|
| 💡 Light (lux) | `< 10` | 2-5 lux (very dark) |
| 🏃 Motion | `= 0` | No movement |
| 💓 Heart Rate | `< avg * 0.85` | 55-65 bpm (vs 70-80 awake) |

---

## 🎯 **Quick Demo Checklist**

### Before the Demo:
- [ ] Server is running (`uvicorn app.main:app --reload`)
- [ ] `demo_sleep_data.json` exists in project root
- [ ] Test the demo endpoint: `http://localhost:8000/wellness/demo`

### During the Demo:
- [ ] Show the demo script output OR
- [ ] Show the demo API endpoint OR
- [ ] Simulate sleep conditions live

### What to Highlight:
- [ ] Sleep duration calculation (hours)
- [ ] Sleep score (0-100)
- [ ] Sleep quality (Good/OK/Poor)
- [ ] Quality factors breakdown
- [ ] Real-time detection capability

---

## 🚀 **Sample Demo Narration**

> "Our system uses multiple sensors to detect sleep automatically:
> 
> 1. **Light sensor** detects darkness (< 10 lux)
> 2. **Motion sensor** confirms no movement
> 3. **Heart rate** drops 15% below average
> 
> When all three conditions are met, the system knows you're sleeping.
> 
> Let me show you with our demo data... [run demo]
> 
> As you can see, it detected 7.5 hours of sleep with a score of 85/100 - 'Good' quality!"

---

## 📁 **Demo Files**

- `demo_sleep_data.json` - Pre-recorded sensor data (9 data points covering 24 hours)
- `demo_sleep_detection.py` - Interactive demo script
- `GET /wellness/demo` - API endpoint for demos

---

## 💡 **Pro Tips**

1. **For live demos:** Use Option 3 (simulate conditions) - it's more impressive!
2. **For presentations:** Use Option 1 (demo script) - it's reliable and visual
3. **For API testing:** Use Option 2 (demo endpoint) - it's quick and consistent
4. **For investors/stakeholders:** Combine all three to show versatility!

---

## ❓ **Common Questions**

**Q: How accurate is the sleep detection?**
A: The system uses 3 independent sensors with weighted scoring. Accuracy depends on sensor quality and calibration.

**Q: Can it detect naps?**
A: Yes! Any period meeting the sleep criteria for 3+ consecutive readings is detected.

**Q: What if someone is just sitting in the dark?**
A: The heart rate check prevents false positives - sitting still has higher HR than sleeping.

**Q: How is sleep duration calculated?**
A: By counting consecutive sensor readings that meet sleep criteria, then converting to hours based on sampling rate.

---

Good luck with your demo! 🎉
