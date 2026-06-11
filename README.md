# 🎭 Swasthaya: Multimodal Wellness & Digital Burnout Platform

**Swasthaya** is an integrated wellness and digital burnout diagnostic platform that combines **IoT hardware telemetry**, **Deep Learning computer vision**, and **Multimodal Audio/Natural Language Processing (NLP)**. By correlating physiological data, environmental comfort, facial expressions, and vocal characteristics, Swasthaya provides a holistic view of user stress, sleep quality, sedentary behavior, and overall burnout levels.

---

## 🏗️ System Architecture & Data Flow

The platform is designed around a decoupled, service-oriented architecture linking local IoT sensors and real-time audio/video processing loops:

```mermaid
graph TD
    A[HTML5/JS Dashboard] -->|Base64 MJPEG Video (5Hz)| B[FastAPI Backend - WebSockets]
    A -->|PCM WAV Audio Buffer| B
    C[IoT Sensor Hub - ESP32/ESP8266] -->|HTTP POST JSON| D[Flask Telemetry Server - Port 5000]
    D -->|Append Data| E[sensor_data.json]
    
    subgraph Computer Vision Pipeline
        B -->|Frame Stream| F[OpenCV Haar Cascade]
        F -->|Face ROI Crop| G[TensorFlow/Keras CNN]
        G -->|Face Emotion Labels| B
    end
    
    subgraph Audio & NLP Pipeline
        B -->|Audio Buffer| H[Whisper ASR - Text Transcription]
        B -->|Audio Buffer| I[Whisper-v3 Speech Emotion Classifier]
        H -->|Speech Text| J[DistilRoBERTa NLP Sentiment Analyzer]
        I -->|Acoustic Features| K[Stress Scoring Logic]
        J -->|Semantic Context| K
        K -->|Vocal/Stress Analytics| B
    end
    
    subgraph Diagnostics Engine
        E -->|Raw Sensor Readings| L[Wellness Analysis Engine]
        L -->|Sleep Analytics| M[Sleep Score 0-100]
        L -->|Sedentary Tracking| N[Inactivity Warnings]
        L -->|Stress & HRV Analysis| O[Stress Levels]
        L -->|Burnout Assessment| P[Digital Burnout Index]
    end

    L -.->|Exposes REST API| B
    B -->|Unified Analytics JSON| A
```

---

## 🌟 Key Features

### 1. Real-time Computer Vision
* **Facial Emotion Recognition (FER):** Captures video frames from the user's camera, isolates faces using OpenCV Haar Cascades, and applies a custom-trained **Keras Convolutional Neural Network (CNN)**.
* **Emotion Categories:** Detects 7 distinct states: `angry`, `disgust`, `fear`, `happy`, `neutral`, `sad`, and `surprise`.

### 2. Multimodal Speech & NLP Pipeline
* **Vocal Emotion Analytics:** Processes user voice recordings with `firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3` to categorize vocal acoustics.
* **Whisper ASR:** Transcribes audio to English text using `openai/whisper-small`.
* **Semantic Sentiment Analysis:** Classifies transcribed text using the `j-hartmann/emotion-english-distilroberta-base` NLP model.
* **Voice Stress Level:** Dynamically maps vocal markers to generate a computed stress percentage indicator.

### 3. IoT Hardware Ingestion
* **Real-time Telemetry Ingest:** Flask server maps and logs Incoming sensor metrics: **Heart Rate (HR)**, **HRV (RMSSD)**, **environmental temperature**, **light levels (Lux)**, and **Motion**.
* **Hardware-Software Loop:** Detects environmental anomalies (e.g. workspace too bright or temperature uncomfortable) and correlates them with body biometrics.

### 4. Advanced Wellness Diagnostics Engine
* **Intelligent Sleep Analysis:** Calculates sleep patterns by confirming conditions: ambient light levels `< 10 lux`, no movement (`Motion = 0`), and heart rate drop > 15% below baseline. Computes a score based on duration, motion consistency, and RMSSD recovery.
* **Waking Activity Tracker:** Identifies prolonged periods of waking physical inactivity to issue alerts to prompt stretching/walking breaks.
* **Comprehensive Burnout Index:** Evaluates workspace comfort (temp/light) and physiological stress to score overall burnout levels (Low, Medium, High).

---

## 📂 Project Directory Structure

```text
├── app/
│   ├── __init__.py
│   ├── infer.py             # Custom CNN inference pipeline for face emotion
│   ├── main.py              # FastAPI ASGI main app (WebSocket + REST endpoints)
│   ├── sensors.py           # Ingestion, normalization, and live sensor utilities
│   ├── voice_infer.py       # Hugging Face pipeline for Speech ASR, Audio, & Text emotion
│   └── wellness_engine.py   # Diagnostic algorithms (Sleep, Sedentary, Stress, Burnout)
├── static/
│   └── index.html           # High-fidelity dashboard (MediaDevices API, Chart.js, CSS UI)
├── demo_sleep_data.json     # 24-hour pre-recorded sensor logs for simulated runs
├── demo_sleep_detection.py  # Interactive sleep cycle simulation CLI
├── emotiondectector.json    # Trained Keras CNN architecture metadata
├── emotiondetector.h5       # Trained CNN model weights
├── getData.py               # Flask REST server (Port 5000) for IoT hardware posts
├── req.txt                  # Python application requirements
├── sensor_data.json         # Runtime sensor database
├── test_wellness.py         # Unit testing command-line engine for diagnostics
└── trainmodel.ipynb         # Jupyter Notebook detailing CNN training on FER2013
```

---

## 🛠️ Installation & Setup

### Prerequisites
* Python 3.10 or higher
* Recommended: Virtual environment manager (`venv` / `conda`)
* Webcam and microphone permissions enabled on the host system

### Step 1: Clone & Setup Environment
1. Open a terminal in the project directory:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r req.txt
   ```

### Step 2: Launch Flask Telemetry Ingest (Port 5000)
Run this server to receive posts from ESP32/ESP8266 hardware devices:
```bash
python getData.py
```
* **Endpoint:** `POST http://localhost:5000/data`
* **Sample Payload:**
  ```json
  {"HR": 72, "RMSSD": 35.5, "Lux": 350.0, "Temp": 22.5, "Motion": "NO"}
  ```

### Step 3: Launch FastAPI Application (Port 8000)
Run this server to host the main dashboard and run real-time inference:
```bash
uvicorn app.main:app --reload
```
Once started, access the dashboard in your web browser:
🔗 **[http://localhost:8000](http://localhost:8000)**

---

## 🧪 Testing & Simulations

Since testing biometric-triggered features like sleep detection or stress analysis live can be challenging, the repository provides built-in testing scripts:

### 1. Simulated Sleep Cycles
Run the interactive CLI utility to simulate a full evening-to-morning sensor dataset and see how the wellness engine detects transitions:
```bash
python demo_sleep_detection.py
```

### 2. Engine Verification
Run this script to verify calculations for Sleep Scores, Sedentary Trackers, HRV/Stress Levels, and Burnout Factors on existing dataset files:
```bash
python test_wellness.py
```

### 3. Demo API Endpoint
Visit **[http://localhost:8000/wellness/demo](http://localhost:8000/wellness/demo)** to see the FastAPI backend mock response evaluating a simulated 24-hour wellness data cycle.

---

## 🧠 Model Training Details

The facial expression recognition classifier is detailed in **[trainmodel.ipynb](file:///c:/Face/trainmodel.ipynb)**.

* **Dataset:** Facial Expression Recognition 2013 (FER2013).
* **Architecture:** 4 Convolutional blocks featuring standard kernel size `(3,3)`, ReLU activations, spatial sub-sampling via `MaxPooling2D`, and aggressive dropout rates (`0.4`) to prevent overfitting.
* **Optimization:** Compiled using the `Adam` optimizer and `categorical_crossentropy` loss.
* **Output:** Saved as `emotiondectector.json` (structure) and `emotiondetector.h5` (trained weights) for backend deployment.

---

## 📡 API Reference

### FastAPI Routes (`app/main.py`)
* `GET /` - Renders the dashboard user interface.
* `GET /sensors` - Returns current normalized readings.
* `GET /wellness` - Evaluates momentary environmental/physiological scores.
* `GET /wellness/sleep` - Analyzes historical sleep logs and computes sleep grades.
* `GET /wellness/sedentary` - Evaluates daytime activity states and thresholds.
* `GET /wellness/stress` - Reviews HRV logs to calculate baseline stress levels.
* `GET /wellness/burnout` - Aggregates sleep, sedentary, and environmental comfort data into a comprehensive Burnout index.
* `GET /wellness/complete` - Returns a combined payload of all wellness analyses.
* `GET /wellness/demo` - Simulated cycle run for visual representations.
* `WebSocket /ws` - Synchronous endpoint managing binary Base64 camera and WAV audio streams.
