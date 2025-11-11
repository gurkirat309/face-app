import base64, io
import numpy as np
from PIL import Image
import cv2
from tensorflow.keras.models import model_from_json

# --- Load your model exactly like your script ---
with open("emotiondectector.json", "r") as f:   # keep your original filename
    _model = model_from_json(f.read())
_model.load_weights("emotiondetector.h5")

# Haar cascade (OpenCV built-in path)
_haar = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Your label mapping/order
LABELS = {0:'angry',1:'disgust',2:'fear',3:'happy',4:'neutral',5:'sad',6:'surprise'}

def _extract_features(gray_roi: np.ndarray) -> np.ndarray:
    # gray_roi is already grayscale 48x48
    feature = np.array(gray_roi, dtype=np.float32).reshape(1, 48, 48, 1) / 255.0
    return feature

def _b64_to_bgr(data_url: str) -> np.ndarray:
    # data_url: 'data:image/jpeg;base64,...'
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    img_bytes = base64.b64decode(b64)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    arr = np.array(img)[:, :, ::-1]  # RGB -> BGR for OpenCV
    return arr

def predict_frame(data_url: str):
    """Return detections = [{box:[x,y,w,h], label, probs:[..]}]"""
    frame = _b64_to_bgr(data_url)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = _haar.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
    detections = []
    for (x, y, w, h) in faces:
        roi = gray[y:y+h, x:x+w]
        roi = cv2.resize(roi, (48, 48))
        x_in = _extract_features(roi)
        pred = _model.predict(x_in, verbose=0)[0]
        idx = int(np.argmax(pred))
        detections.append({
            "box": [int(x), int(y), int(w), int(h)],
            "label": LABELS.get(idx, str(idx)),
            "probs": [float(p) for p in pred],
            "classes": [LABELS[i] for i in range(len(LABELS))]
        })

    # For convenience, also return top_label (first face) or "no_face"
    top_label = detections[0]["label"] if detections else "no_face"
    return {"top_label": top_label, "detections": detections}
