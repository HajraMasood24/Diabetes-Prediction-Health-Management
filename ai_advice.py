"""
AI-generated dietary/lifestyle advice via Google Gemini.
"""
import google.generativeai as genai

import config

genai.configure(api_key=config.GEMINI_API_KEY)

_FALLBACK_ADVICE = (
    "Maintain a balanced diet with fruits, vegetables, whole grains, and "
    "regular exercise. Stay hydrated and get adequate sleep."
)


def get_ai_advice(prediction, probability, user_data):
    """Return short AI-generated dietary/lifestyle advice based on risk level."""
    if prediction == "Diabetic":
        prompt = f"""
        User is DIABETIC with {probability:.1%} risk.
        Age: {user_data['age']}, BMI: {user_data['bmi']}, Glucose: {user_data['blood_glucose_level']}

        Provide:
        1. 3 specific foods to avoid
        2. 3 specific foods to eat
        3. 2 lifestyle changes
        Keep response short and practical (max 150 words).
        """
    elif probability > 0.3:
        prompt = f"""
        User is PREDIABETIC with {probability:.1%} risk.
        Age: {user_data['age']}, BMI: {user_data['bmi']}

        Provide:
        1. 3 dietary changes to prevent diabetes
        2. 2 lifestyle modifications
        Keep response short (max 120 words).
        """
    else:
        prompt = """
        User is HEALTHY with low diabetes risk.

        Provide:
        3 tips to maintain healthy lifestyle and prevent diabetes.
        Keep response short (max 100 words).
        """

    try:
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini error: {e}")
        return _FALLBACK_ADVICE


def get_custom_advice(user_query):
    """Answer a free-form diabetes-related question from the user."""
    prompt = (
        f"User asks: {user_query}\n\n"
        "Provide helpful diabetes-related dietary and lifestyle advice. "
        "Keep response concise and practical."
    )
    model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
    response = model.generate_content(prompt)
    return response.text
