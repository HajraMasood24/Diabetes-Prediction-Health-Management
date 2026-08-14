"""
Loads the trained Keras model + preprocessor, and runs predictions.
Falls back to a simple rule-based mock prediction if either file is missing,
so the API stays usable for demoing the rest of the app.
"""
import os
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')

import joblib
import pandas as pd
import tensorflow as tf

import config

model = None
preprocessor = None


def load_model_and_preprocessor():
    """Load the trained model and preprocessor from disk. Call once at startup."""
    global model, preprocessor

    print("=" * 50)
    print("LOADING DIABETES PREDICTION MODEL")
    print("=" * 50)

    try:
        model = tf.keras.models.load_model(config.MODEL_PATH_PRIMARY)
        print(f"Model loaded: {config.MODEL_PATH_PRIMARY}")
    except Exception as e:
        print(f"Could not load {config.MODEL_PATH_PRIMARY}: {e}")
        print(f"Trying {config.MODEL_PATH_FALLBACK}...")
        try:
            model = tf.keras.models.load_model(config.MODEL_PATH_FALLBACK)
            print(f"Model loaded: {config.MODEL_PATH_FALLBACK}")
        except Exception as e2:
            print(f"No model found: {e2}")
            print("Will use fallback mock predictions until a model is available")
            model = None

    try:
        preprocessor = joblib.load(config.PREPROCESSOR_PATH)
        print(f"Preprocessor loaded: {config.PREPROCESSOR_PATH}")
    except Exception as e:
        print(f"Preprocessor not found: {e}")
        preprocessor = None

    print("=" * 50)


def _fallback_prediction(user_data):
    glucose = user_data.get('blood_glucose_level', 100)
    bmi = user_data.get('bmi', 25)
    if glucose > 180 or bmi > 35:
        return 0.85, "Diabetic"
    elif glucose > 140 or bmi > 30:
        return 0.45, "Non-diabetic"
    return 0.15, "Non-diabetic"


def make_real_prediction(user_data):
    """Run the trained model on user_data and return (probability, label)."""
    if model is None or preprocessor is None:
        print("Model/preprocessor not loaded — using fallback mock prediction")
        return _fallback_prediction(user_data)

    try:
        input_df = pd.DataFrame([{
            'age': user_data['age'],
            'gender': user_data['gender'],
            'bmi': user_data['bmi'],
            'hypertension': user_data['hypertension'],
            'heart_disease': user_data['heart_disease'],
            'smoking_history': user_data['smoking_history'],
            'blood_glucose_level': user_data['blood_glucose_level'],
        }])

        processed = preprocessor.transform(input_df).astype('float32')
        probability = float(model.predict(processed, verbose=0)[0][0])
        prediction = "Diabetic" if probability >= 0.7 else "Non-diabetic"
        return probability, prediction
    except Exception as e:
        print(f"Prediction error: {e}")
        return 0.5, "Non-diabetic"
