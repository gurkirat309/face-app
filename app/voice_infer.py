# app/voice_infer.py
import os
import tempfile
import base64
import traceback
import logging
import random

import torch
import numpy as np
from transformers import AutoModelForAudioClassification, AutoFeatureExtractor
import librosa
  # needs ffmpeg on system

logger = logging.getLogger(__name__)

MODEL_ID = "firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3"

# ---- load model + extractor (similar to your flask file) ----
try:
    logger.info(f"Loading audio model {MODEL_ID} ...")
    model = AutoModelForAudioClassification.from_pretrained(MODEL_ID)
    feature_extractor = AutoFeatureExtractor.from_pretrained(MODEL_ID, do_normalize=True)
    id2label = model.config.id2label
    logger.info("Audio model loaded")
except Exception as e:
    logger.exception("Failed loading audio model; entering fallback mode")
    model = None
    feature_extractor = None
    id2label = {
        0: "angry",
        1: "disgust",
        2: "fearful",
        3: "happy",
        4: "neutral",
        5: "sad",
        6: "surprised"
    }

EMOTION_RECOMMENDATIONS = {
    'angry': ["Take deep breaths and count to 10", "Go for a short walk to cool down"],
    'disgust': ["Focus on positive aspects", "Practice mindfulness"],
    'fearful': ["Grounding techniques", "Deep breathing"],
    'happy': ["Savor this positive emotion", "Share your happiness"],
    'neutral': ["Reflect on goals", "Practice gratitude"],
    'sad': ["Allow feelings", "Connect with someone"],
    'surprised': ["Process the event", "Focus on breathing"]
}
EMOTION_TO_STRESS = {
    'angry': 'high', 'disgust': 'high', 'fearful': 'high', 'sad': 'high',
    'surprised': 'medium', 'neutral': 'medium', 'happy': 'low'
}

# audio loading / preprocessing helpers (taken & simplified from your Flask code)
def _to_wav_bytes_from_webm_or_ogg(raw_bytes: bytes, input_format: str = "webm") -> bytes:
    # uses pydub (ffmpeg) to convert webm/ogg -> wav bytes
    audio = AudioSegment.from_file(io.BytesIO(raw_bytes), format=input_format)
    buf = io.BytesIO()
    audio.export(buf, format="wav")
    return buf.getvalue()

def load_audio_with_librosa(path, sr=16000):
    y, s = librosa.load(path, sr=sr)
    return y, s

def preprocess_for_model(audio_path, max_duration=30.0):
    # loads audio using librosa/fallback like your flask code and returns `inputs` for HF extractor
    try:
        y, sr = load_audio_with_librosa(audio_path, sr=16000)
    except Exception as e:
        # fallback more thorough loaders could be placed here -- for brevity, re-raise
        logger.exception("librosa failed to load; re-raising")
        raise

    # truncate/pad
    max_len = int(16000 * max_duration)
    if len(y) > max_len:
        y = y[:max_len]
    if len(y) < 8000:
        y = np.pad(y, (0, 8000 - len(y)), 'constant')

    # normalize
    y = librosa.util.normalize(y)

    if feature_extractor:
        inputs = feature_extractor(y, sampling_rate=16000, return_tensors="pt")
        return inputs, y
    else:
        return None, y

def predict_emotion_from_wav_file(wav_path, max_duration=30.0):
    """Main entry: given path to WAV file, returns same JSON as your Flask predict_emotion"""
    try:
        if model is None:
            # fallback randomized output
            emotions = list(id2label.values())
            emotion = random.choice(emotions)
            confidence = random.uniform(0.6, 0.95)
            result = {
                'emotion': emotion,
                'confidence': confidence,
                'confidence_str': f"{confidence:.2%}",
                'stress_level': EMOTION_TO_STRESS.get(emotion, 'medium'),
                'recommendation': random.choice(EMOTION_RECOMMENDATIONS.get(emotion, [])),
                'all_probabilities': {e: random.uniform(0.01, 0.2) for e in emotions},
                'audio_duration': 5.0,
                'note': 'fallback mode (model not loaded)'
            }
            return result

        inputs, audio_array = preprocess_for_model(wav_path, max_duration=max_duration)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=-1)[0].cpu().numpy()
            pred_id = int(np.argmax(probs))
            label = id2label[pred_id]
            confidence = float(probs[pred_id])
            all_probs = {id2label[i]: float(probs[i]) for i in range(len(probs))}

        result = {
            'emotion': label,
            'confidence': confidence,
            'confidence_str': f"{confidence:.2%}",
            'stress_level': EMOTION_TO_STRESS.get(label, 'medium'),
            'recommendation': random.choice(EMOTION_RECOMMENDATIONS.get(label, [])),
            'all_probabilities': all_probs,
            'audio_duration': len(audio_array) / 16000.0
        }
        return result
    except Exception as e:
        logger.exception("Error during audio prediction")
        # fallback emergency behavior like in your Flask app
        emotions = list(id2label.values())
        emotion = random.choice(emotions)
        confidence = random.uniform(0.7, 0.9)
        all_probs = {e: random.uniform(0.01, 0.2) for e in emotions}
        all_probs[emotion] = confidence
        return {
            'emotion': emotion,
            'confidence': confidence,
            'confidence_str': f"{confidence:.2%}",
            'stress_level': EMOTION_TO_STRESS.get(emotion, 'medium'),
            'recommendation': random.choice(EMOTION_RECOMMENDATIONS.get(emotion, [])),
            'all_probabilities': all_probs,
            'audio_duration': 5.0,
            'note': 'emergency fallback due to error'
        }
