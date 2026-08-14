"""
Loads the raw diabetes dataset, cleans it, fits a preprocessing pipeline,
and saves the preprocessed train/test splits plus the fitted preprocessor
to disk for model.py to train on.

Run directly: python preprocessing.py
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from imblearn.over_sampling import SMOTE
import joblib

import config

NUMERIC_FEATURES = ['age', 'bmi', 'blood_glucose_level']
CATEGORICAL_FEATURES = ['gender', 'smoking_history']
BINARY_FEATURES = ['hypertension', 'heart_disease']

BMI_CLIP_MAX = 50
GLUCOSE_CLIP_MAX = 300

RANDOM_STATE = 42


def load_and_clean(csv_path=None):
    """Load the raw CSV and apply basic cleaning steps."""
    df = pd.read_csv(csv_path or config.DATASET_CSV_PATH)

    df = df.drop(columns=['HbA1c_level'], errors='ignore')
    df['smoking_history'] = df['smoking_history'].replace('No Info', 'never')

    print(df.head())
    print(df.info())

    df = df.drop_duplicates()
    print(f"\nAfter removing duplicates: {df.shape[0]} rows")

    df['bmi'] = df['bmi'].clip(upper=BMI_CLIP_MAX)
    df['blood_glucose_level'] = df['blood_glucose_level'].clip(upper=GLUCOSE_CLIP_MAX)

    return df


def build_preprocessor():
    return ColumnTransformer([
        ('num', StandardScaler(), NUMERIC_FEATURES),
        ('cat', OneHotEncoder(drop='first', sparse_output=False), CATEGORICAL_FEATURES),
        ('bin', 'passthrough', BINARY_FEATURES),
    ])


def run():
    df = load_and_clean()

    X = df.drop('diabetes', axis=1)
    y = df['diabetes']

    preprocessor = build_preprocessor()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    X_train_scaled = preprocessor.fit_transform(X_train)
    X_test_scaled = preprocessor.transform(X_test)

    # Original (non-SMOTE) data — used for class_weight training in model.py
    X_train_original = X_train_scaled.astype(np.float32)
    y_train_original = y_train.values.astype(np.float32)
    np.save('X_train_original.npy', X_train_original)
    np.save('y_train_original.npy', y_train_original)
    print("\nOriginal training data saved (for class_weight method)")
    print(f"Original class balance: {np.bincount(y_train_original.astype(int))}")

    # SMOTE-balanced version — kept for reference/comparison
    smote = SMOTE(random_state=RANDOM_STATE)
    X_train_balanced, y_train_balanced = smote.fit_resample(X_train_scaled, y_train)

    X_train_balanced = X_train_balanced.astype(np.float32)
    X_test_scaled = X_test_scaled.astype(np.float32)
    y_train_balanced = y_train_balanced.astype(np.float32)
    y_test = y_test.astype(np.float32)

    np.save('X_train_preprocessed.npy', X_train_balanced)
    np.save('X_test_preprocessed.npy', X_test_scaled)
    np.save('y_train_preprocessed.npy', y_train_balanced)
    np.save('y_test_preprocessed.npy', y_test)

    joblib.dump(preprocessor, config.PREPROCESSOR_PATH)

    print("\nSMOTE training data shape:", X_train_balanced.shape)
    print("Original training data shape:", X_train_original.shape)
    print("Testing data shape:", X_test_scaled.shape)
    print("Preprocessing completed successfully!")


if __name__ == '__main__':
    run()
