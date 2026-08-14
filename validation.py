"""
Validates raw prediction-request input before it reaches the model.
"""
import pandas as pd

REQUIRED_FIELDS = [
    'age', 'gender', 'bmi', 'hypertension',
    'heart_disease', 'smoking_history', 'blood_glucose_level',
]

VALID_GENDERS = ['Female', 'Male', 'Other']
VALID_SMOKING_HISTORY = ['never', 'former', 'current', 'not current', 'ever']

AGE_RANGE = (0, 120)
BMI_RANGE = (10, 50)
GLUCOSE_RANGE = (50, 300)


def validate_input(data):
    """Return a list of human-readable error strings; empty list means valid."""
    errors = []

    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        errors.append(f"Missing required field(s): {', '.join(missing)}")
        return errors  # can't safely check ranges on fields that aren't there

    if not isinstance(data['age'], (int, float)) or not (AGE_RANGE[0] <= data['age'] <= AGE_RANGE[1]):
        errors.append(f"Age must be between {AGE_RANGE[0]} and {AGE_RANGE[1]}")

    if not isinstance(data['bmi'], (int, float)) or not (BMI_RANGE[0] <= data['bmi'] <= BMI_RANGE[1]):
        errors.append(f"BMI must be between {BMI_RANGE[0]} and {BMI_RANGE[1]}")

    if not isinstance(data['blood_glucose_level'], (int, float)) or not (
        GLUCOSE_RANGE[0] <= data['blood_glucose_level'] <= GLUCOSE_RANGE[1]
    ):
        errors.append(f"Blood glucose level must be between {GLUCOSE_RANGE[0]} and {GLUCOSE_RANGE[1]}")

    if data['hypertension'] not in [0, 1]:
        errors.append("Hypertension must be 0 (No) or 1 (Yes)")

    if data['heart_disease'] not in [0, 1]:
        errors.append("Heart disease must be 0 (No) or 1 (Yes)")

    if data['gender'] not in VALID_GENDERS:
        errors.append(f"Gender must be one of: {', '.join(VALID_GENDERS)}")

    if data['smoking_history'] not in VALID_SMOKING_HISTORY:
        errors.append(f"Smoking history must be one of: {', '.join(VALID_SMOKING_HISTORY)}")

    return errors


def preprocess_input(data, preprocessor):
    """Preprocess a single input dict using the saved preprocessor."""
    df_input = pd.DataFrame([data])
    return preprocessor.transform(df_input)
