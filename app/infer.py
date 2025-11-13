# app/infer.py
import base64
import io
import numpy as np
from PIL import Image
import cv2
from tensorflow.keras.models import model_from_json
import os

# --- CONFIG: filenames (put these in your project root or adjust paths) ---
MODEL_JSON = "emotiondectector.json"
MODEL_WEIGHTS = "emotiondetector.h5"

# --- Load Keras model (json + weights) ---
_model = None
try:
    if os.path.exists(MODEL_JSON):
        with open(MODEL_JSON, "r", encoding="utf-8") as f:
            _model = model_from_json(f.read())
        if os.path.exists(MODEL_WEIGHTS):
            _model.load_weights(MODEL_WEIGHTS)
        else:
            print(f"[WARN] weights file not found: {MODEL_WEIGHTS}")
    else:
        print(f"[WARN] model json not found: {MODEL_JSON}")
except Exception as e:
    print("Error loading model:", e)
    _model = None

# Haar cascade (OpenCV path)
_haar = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Label mapping (match your realtimedetection.py)
LABELS = {0: 'angry', 1: 'disgust', 2: 'fear', 3: 'happy', 4: 'neutral', 5: 'sad', 6: 'surprise'}

def _b64_to_bgr(data_url: str):
    """Convert dataURL to BGR numpy image (OpenCV format)"""
    if "," in data_url:
        b64 = data_url.split(",", 1)[1]
    else:
        b64 = data_url
    img_bytes = base64.b64decode(b64)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    arr = np.array(img)[:, :, ::-1]  # RGB->BGR
    return arr

def _extract_features(gray_roi: np.ndarray) -> np.ndarray:
    """Resize/reshape/normalize as (1,48,48,1)"""
    arr = np.array(gray_roi, dtype=np.float32).reshape(1, 48, 48, 1) / 255.0
    return arr

def predict_frame(data_url: str):
    """
    Input: dataURL (e.g. 'data:image/jpeg;base64,...') representing a frame.
    Output: dict { top_label: str, detections: [ { box: [x,y,w,h], label: str, probs: [...], classes: [...] } ] }
    """
    try:
        frame = _b64_to_bgr(data_url)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = _haar.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
        detections = []
        for (x, y, w, h) in faces:
            roi = gray[y:y+h, x:x+w]
            roi = cv2.resize(roi, (48, 48))
            x_in = _extract_features(roi)
            if _model is not None:
                pred = _model.predict(x_in, verbose=0)[0]
                idx = int(np.argmax(pred))
                label = LABELS.get(idx, str(idx))
                probs = [float(p) for p in pred]
                classes = [LABELS[i] for i in range(len(LABELS))]
            else:
                # fallback: return neutral
                label = "neutral"
                probs = [0.0] * len(LABELS)
                probs[list(LABELS.keys())[4]] = 1.0
                classes = [LABELS[i] for i in range(len(LABELS))]
            detections.append({
                "box": [int(x), int(y), int(w), int(h)],
                "label": label,
                "probs": probs,
                "classes": classes
            })
        top_label = detections[0]["label"] if detections else "no_face"
        return {"top_label": top_label, "detections": detections}
    except Exception as e:
        # On error return empty result (don't crash the websocket loop)
        print("infer.predict_frame error:", e)
        import traceback
        traceback.print_exc()
        return {"top_label": "error", "detections": []}
