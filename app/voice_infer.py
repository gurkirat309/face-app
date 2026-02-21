# app/voice_infer.py

import os
import random
import logging
import numpy as np
import torch
import librosa
from transformers import (
    AutoModelForAudioClassification,
    AutoFeatureExtractor,
    pipeline,
    WhisperProcessor,
    WhisperForConditionalGeneration
)

logger = logging.getLogger(__name__)

device = torch.device("cpu")

# -------------------------------
# 1️⃣ AUDIO EMOTION MODEL
# -------------------------------

AUDIO_MODEL_ID = "firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3"

model = AutoModelForAudioClassification.from_pretrained(AUDIO_MODEL_ID)
feature_extractor = AutoFeatureExtractor.from_pretrained(AUDIO_MODEL_ID)
model.to(device)
model.eval()

id2label = model.config.id2label

# -------------------------------
# 2️⃣ WHISPER ASR MODEL
# -------------------------------

ASR_MODEL_ID = "openai/whisper-small"

whisper_processor = WhisperProcessor.from_pretrained(ASR_MODEL_ID)
whisper_model = WhisperForConditionalGeneration.from_pretrained(ASR_MODEL_ID)
whisper_model.to(device)
whisper_model.eval()

# -------------------------------
# 3️⃣ TEXT EMOTION NLP MODEL
# -------------------------------

text_emotion_pipeline = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    return_all_scores=True,
    framework="pt",   # FORCE PyTorch
    device=-1
)


# -------------------------------
# HELPERS
# -------------------------------

def load_audio(path, sr=16000):
    y, sr = librosa.load(path, sr=sr)
    y = librosa.util.normalize(y)
    return y


def transcribe_audio(audio_array):
    inputs = whisper_processor(
        audio_array,
        sampling_rate=16000,
        return_tensors="pt"
    )
    input_features = inputs.input_features.to(device)

    # Force English transcription
    forced_decoder_ids = whisper_processor.get_decoder_prompt_ids(language="english", task="transcribe")

    with torch.no_grad():
        predicted_ids = whisper_model.generate(
            input_features,
            forced_decoder_ids=forced_decoder_ids
        )

    transcription = whisper_processor.batch_decode(
        predicted_ids,
        skip_special_tokens=True
    )[0]

    return transcription


def predict_audio_emotion(audio_array):
    inputs = feature_extractor(
        audio_array,
        sampling_rate=16000,
        return_tensors="pt"
    )

    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]

    probs = probs.cpu().numpy()
    pred_id = int(np.argmax(probs))
    label = id2label[pred_id]
    confidence = float(probs[pred_id]) * 100

    all_probs = {
        id2label[i]: round(float(probs[i]) * 100, 2)
        for i in range(len(probs))
    }

    return label, confidence, all_probs


def analyze_text_emotion(text):
    results = text_emotion_pipeline(text)[0]

    probs = {r["label"]: round(r["score"] * 100, 2) for r in results}
    top = max(probs, key=probs.get)

    return top, probs


# -------------------------------
# MAIN FUNCTION
# -------------------------------

def predict_emotion_from_wav_file(wav_path):


    audio_array = load_audio(wav_path)

    # 1️⃣ Transcription
    transcript = transcribe_audio(audio_array)

    # 2️⃣ Audio-based Emotion
    audio_emotion, audio_conf, audio_probs = predict_audio_emotion(audio_array)

    # 3️⃣ Text-based Emotion
    text_emotion, text_probs = analyze_text_emotion(transcript)

    # 4️⃣ Stress score logic
    stress_mapping = {
        "angry": 0.9,
        "disgust": 0.85,
        "fearful": 0.95,
        "sad": 0.88,
        "surprise": 0.6,
        "neutral": 0.5,
        "happy": 0.2
    }

    stress_score = stress_mapping.get(audio_emotion.lower())

    return {
        "transcript": transcript,
        "audio_emotion": audio_emotion,
        "audio_confidence": round(audio_conf, 2),
        "audio_probabilities": audio_probs,
        "text_emotion": text_emotion,
        "text_probabilities": text_probs,
        "stress_score": stress_score,
        "duration_seconds": round(len(audio_array) / 16000, 2)
    }
