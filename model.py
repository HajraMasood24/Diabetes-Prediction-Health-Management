"""
Trains the diabetes-prediction neural network on the preprocessed data
produced by preprocessing.py, evaluates it, tunes the decision threshold,
and saves the trained model + an evaluation figure.

Run directly: python model.py  (run preprocessing.py first)
"""
import os
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')

import numpy as np
import tensorflow as tf
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, roc_curve,
    precision_score, recall_score, f1_score,
)
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

import config

TEAL = '#1D9E75'
CORAL = '#D85A30'
RANDOM_SEED = 42

CANDIDATE_THRESHOLDS = [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7]


def load_training_data():
    X_train = np.load('X_train_original.npy')
    X_test = np.load('X_test_preprocessed.npy')
    y_train = np.load('y_train_original.npy')
    y_test = np.load('y_test_preprocessed.npy')

    print(f"X_train: {X_train.shape}  X_test: {X_test.shape}")
    print(f"y_train class balance: {np.bincount(y_train.astype(int))}")
    return X_train, X_test, y_train, y_test


def build_model(input_dim):
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(128, activation='relu', input_shape=(input_dim,)),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.4),

        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.3),

        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dropout(0.2),

        tf.keras.layers.Dense(1, activation='sigmoid'),
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=[
            'accuracy',
            tf.keras.metrics.AUC(name='auc'),
            tf.keras.metrics.Precision(name='precision'),
            tf.keras.metrics.Recall(name='recall'),
        ],
    )
    return model


def train_model(model, X_train, y_train, class_weight_dict):
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_auc', patience=7, restore_best_weights=True, mode='max', verbose=1,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            config.MODEL_PATH_FALLBACK, monitor='val_auc', save_best_only=True, mode='max', verbose=0,
        ),
    ]

    return model.fit(
        X_train, y_train,
        epochs=50,
        batch_size=256,
        validation_split=0.15,
        callbacks=callbacks,
        class_weight=class_weight_dict,
        verbose=1,
    )


def tune_threshold(y_test, y_pred_prob):
    """Try a range of thresholds and return the one with the best F1 score."""
    best_f1 = 0
    best_threshold = 0.5

    print("\n--- Threshold Tuning ---")
    for t in CANDIDATE_THRESHOLDS:
        y_pred_t = (y_pred_prob >= t).astype(int)
        p = precision_score(y_test, y_pred_t, zero_division=0)
        r = recall_score(y_test, y_pred_t, zero_division=0)
        f1 = f1_score(y_test, y_pred_t, zero_division=0)
        print(f"Threshold {t:.2f} | Precision={p:.2f}  Recall={r:.2f}  F1={f1:.2f}")
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = t

    print(f"\nBest threshold: {best_threshold}  (F1={best_f1:.2f})")
    print(f"Use this value in prediction.py:  probability >= {best_threshold}")
    return best_threshold


def plot_evaluation(history, y_test, y_pred_prob, y_pred_best, best_threshold, roc_auc, output_path='model_evaluation.png'):
    sns.set_theme(style='whitegrid', font='DejaVu Sans')
    plt.rcParams.update({
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.titlesize': 11, 'axes.titleweight': 'bold',
        'axes.titlepad': 10, 'font.size': 10,
    })

    fig = plt.figure(figsize=(18, 10))
    fig.suptitle('Deep Learning Model — Training & Evaluation (Class Weights)', fontsize=15, fontweight='bold', y=0.98)

    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.38, wspace=0.35, top=0.91, bottom=0.10, left=0.07, right=0.97)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])
    ax4 = fig.add_subplot(gs[1, 0])
    ax5 = fig.add_subplot(gs[1, 1])
    ax6 = fig.add_subplot(gs[1, 2])

    ax1.plot(history.history['loss'], color=CORAL, linewidth=2, label='Train')
    ax1.plot(history.history['val_loss'], color=TEAL, linewidth=2, label='Val')
    ax1.set_title('Training vs Validation Loss')
    ax1.set_xlabel('Epoch'); ax1.set_ylabel('Loss')
    ax1.legend(frameon=False, fontsize=9)

    ax2.plot(history.history['accuracy'], color=CORAL, linewidth=2, label='Train')
    ax2.plot(history.history['val_accuracy'], color=TEAL, linewidth=2, label='Val')
    ax2.set_title('Training vs Validation Accuracy')
    ax2.set_xlabel('Epoch'); ax2.set_ylabel('Accuracy')
    ax2.legend(frameon=False, fontsize=9)

    ax3.plot(history.history['auc'], color=CORAL, linewidth=2, label='Train')
    ax3.plot(history.history['val_auc'], color=TEAL, linewidth=2, label='Val')
    ax3.set_title('Training vs Validation AUC')
    ax3.set_xlabel('Epoch'); ax3.set_ylabel('AUC')
    ax3.legend(frameon=False, fontsize=9)

    cm = confusion_matrix(y_test, y_pred_best)
    sns.heatmap(
        cm, annot=True, fmt='d', cmap='RdYlGn',
        xticklabels=['Non-diabetic', 'Diabetic'], yticklabels=['Non-diabetic', 'Diabetic'],
        linewidths=0.5, ax=ax4,
    )
    ax4.set_title(f'Confusion Matrix (threshold={best_threshold})')
    ax4.set_xlabel('Predicted'); ax4.set_ylabel('Actual')

    fpr, tpr, _ = roc_curve(y_test, y_pred_prob)
    ax5.plot(fpr, tpr, color=CORAL, linewidth=2, label=f'AUC = {roc_auc:.3f}')
    ax5.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5)
    ax5.set_title('ROC Curve')
    ax5.set_xlabel('False Positive Rate'); ax5.set_ylabel('True Positive Rate')
    ax5.legend(frameon=False, fontsize=9)

    ax6.hist(y_pred_prob[y_test == 0], bins=40, alpha=0.6, color=TEAL, label='Non-diabetic', edgecolor=TEAL, linewidth=0.6)
    ax6.hist(y_pred_prob[y_test == 1], bins=40, alpha=0.6, color=CORAL, label='Diabetic', edgecolor=CORAL, linewidth=0.6)
    ax6.axvline(best_threshold, color='gray', linestyle='--', linewidth=1, label=f'Threshold {best_threshold}')
    ax6.set_title('Predicted Probability Distribution')
    ax6.set_xlabel('Predicted Probability'); ax6.set_ylabel('Count')
    ax6.legend(frameon=False, fontsize=9)

    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.show()
    print(f"Plot saved as {output_path}")


def run():
    tf.random.set_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    X_train, X_test, y_train, y_test = load_training_data()

    class_weights = compute_class_weight(class_weight='balanced', classes=np.unique(y_train), y=y_train)
    class_weight_dict = dict(enumerate(class_weights))
    print(f"\nClass weights: {class_weight_dict}")
    print(f"  Non-diabetic weight: {class_weight_dict[0]:.3f}")
    print(f"  Diabetic weight:     {class_weight_dict[1]:.3f}")

    model = build_model(X_train.shape[1])
    model.summary()

    print("\nTraining model with class weights...")
    history = train_model(model, X_train, y_train, class_weight_dict)

    print("\n--- Test Set Evaluation (threshold=0.5) ---")
    model.evaluate(X_test, y_test, verbose=1)

    y_pred_prob = model.predict(X_test, verbose=0).flatten()
    y_pred = (y_pred_prob >= 0.5).astype(int)

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Non-diabetic', 'Diabetic']))

    roc_auc = roc_auc_score(y_test, y_pred_prob)
    print(f"ROC-AUC Score: {roc_auc:.4f}")

    best_threshold = tune_threshold(y_test, y_pred_prob)
    y_pred_best = (y_pred_prob >= best_threshold).astype(int)
    print(f"\n--- Classification Report at threshold={best_threshold} ---")
    print(classification_report(y_test, y_pred_best, target_names=['Non-diabetic', 'Diabetic']))

    model.save(config.MODEL_PATH_PRIMARY)
    print(f"\nModel saved as {config.MODEL_PATH_PRIMARY}")

    plot_evaluation(history, y_test, y_pred_prob, y_pred_best, best_threshold, roc_auc)


if __name__ == '__main__':
    run()
