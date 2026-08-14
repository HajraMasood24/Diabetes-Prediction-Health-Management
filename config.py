import os
from dotenv import load_dotenv

load_dotenv()

def _require(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


# Flask
SECRET_KEY = _require("SECRET_KEY")

# Google Gemini (AI dietary advice)
GEMINI_API_KEY = _require("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-flash-lite")

# Email (Gmail SMTP)
EMAIL_SENDER = _require("EMAIL_SENDER")
EMAIL_PASSWORD = _require("EMAIL_PASSWORD")
EMAIL_DISPLAY_NAME = os.environ.get("EMAIL_DISPLAY_NAME", "Diabetes Prediction Co")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))

# Database / model files
DATABASE_PATH = os.environ.get("DATABASE_PATH", "diabetes.db")
MODEL_PATH_PRIMARY = os.environ.get("MODEL_PATH_PRIMARY", "diabetes_model.keras")
MODEL_PATH_FALLBACK = os.environ.get("MODEL_PATH_FALLBACK", "best_model.keras")
PREPROCESSOR_PATH = os.environ.get("PREPROCESSOR_PATH", "preprocessor.pkl")
DATASET_CSV_PATH = os.environ.get("DATASET_CSV_PATH", "diabetes_prediction_dataset.csv")

# Flask run settings
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
PORT = int(os.environ.get("FLASK_PORT", "5000"))
