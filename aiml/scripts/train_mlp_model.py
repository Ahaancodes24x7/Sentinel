"""
PS 26165 — Next model: a real, fully-trained neural network (MLP).

ENVIRONMENT NOTE:
What THIS script builds: a genuine multi-layer, nonlinear neural
network — scikit-learn's MLPClassifier (hidden layers: 128 -> 64, ReLU activations,
Adam optimizer, real backprop, early stopping on a held-out validation split) —
trained end-to-end on the same TF-IDF features Baseline 2 used.
This benchmark model is evaluated against Baseline 1 and Baseline 2 on identical data.

Models trained here:
  MODEL 3   — MLP neural network (SIF-potential, binary)
  MODEL 3b  — MLP neural network (LSR tagging, multi-class)
"""

import pickle
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    precision_recall_fscore_support, roc_auc_score, average_precision_score,
    confusion_matrix, classification_report, brier_score_loss
)
from sklearn.preprocessing import LabelEncoder
from sklearn.frozen import FrozenEstimator

from sif_engine.preprocessing import preprocess_report

RANDOM_STATE = 42

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "synthetic" / "synthetic_uauc_reports.csv"
MLP_DIR = BASE_DIR / "models" / "mlp"
REPORT_PATH = BASE_DIR / "reports" / "mlp_model_evaluation_report.md"

# Baseline 2 reference metrics (from model_evaluation_report.md)
BASELINE2_P, BASELINE2_R, BASELINE2_F1, BASELINE2_F2 = 0.833, 0.864, 0.848, 0.858
BASELINE2_ROC, BASELINE2_PRAUC = 0.927, 0.917


def train_and_eval():
    MLP_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH, keep_default_na=False, na_values=[])
    df["report_text_preprocessed"] = df["report_text"].apply(preprocess_report)

    train_df, test_df = train_test_split(
        df, test_size=0.2, random_state=RANDOM_STATE, stratify=df.sif_potential
    )
    test_df = test_df.copy()

    report_lines = []
    report_lines.append("# PS 26165 — Model 3: MLP Neural Network Evaluation\n")
    report_lines.append(
        "Trained on `report_text_preprocessed` (Stage 0 output), same train/test split "
        "(random_state=42, stratified) used for Baseline 1 and Baseline 2, so results are "
        "directly comparable.\n"
    )

    # ---------------------------------------------------------------------------
    # MODEL 3 — MLP (multi-layer perceptron) on TF-IDF features, SIF-potential
    # ---------------------------------------------------------------------------
    print("Training Model 3 (MLP SIF-potential)...")
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=8000, stop_words="english")
    X_train = vectorizer.fit_transform(train_df.report_text_preprocessed).toarray()
    X_test = vectorizer.transform(test_df.report_text_preprocessed).toarray()
    y_train = train_df.sif_potential.values
    y_test = test_df.sif_potential.values

    X_tr_fit, X_calib, y_tr_fit, y_calib = train_test_split(
        X_train, y_train, test_size=0.15, random_state=RANDOM_STATE, stratify=y_train
    )

    mlp = MLPClassifier(
        hidden_layer_sizes=(128, 64),
        activation="relu",
        solver="adam",
        alpha=1e-4,
        learning_rate_init=1e-3,
        max_iter=300,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=15,
        random_state=RANDOM_STATE,
    )
    mlp.fit(X_tr_fit, y_tr_fit)

    print(f"MLP trained for {mlp.n_iter_} iterations (stopped early: {mlp.n_iter_ < 300})")
    print(f"Final training loss: {mlp.loss_:.4f}")
    print(f"Best validation score during training: {mlp.best_validation_score_:.4f}")

    calibrated_mlp = CalibratedClassifierCV(FrozenEstimator(mlp), method="sigmoid")
    calibrated_mlp.fit(X_calib, y_calib)

    y_pred = calibrated_mlp.predict(X_test)
    y_prob = calibrated_mlp.predict_proba(X_test)[:, 1]

    p, r, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary", zero_division=0)
    beta = 2
    f2 = (1 + beta**2) * (p * r) / (beta**2 * p + r) if (p + r) > 0 else 0.0
    roc_auc = roc_auc_score(y_test, y_prob)
    pr_auc = average_precision_score(y_test, y_prob)
    brier = brier_score_loss(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred)

    report_lines.append("\n## Model 3 — MLP Neural Network (2 hidden layers: 128 -> 64, ReLU, Adam)\n")
    report_lines.append(f"Trained for {mlp.n_iter_} epochs (early-stopped: {mlp.n_iter_ < 300}); "
                         f"final training loss: {mlp.loss_:.4f}\n")
    report_lines.append(f"Precision: {p:.3f} | Recall: {r:.3f} | F1: {f1:.3f} | F2: {f2:.3f}\n")
    report_lines.append(f"ROC-AUC: {roc_auc:.3f} | PR-AUC: {pr_auc:.3f} | Brier: {brier:.4f}\n")
    report_lines.append(f"Confusion matrix [[TN,FP],[FN,TP]]: {cm.tolist()}\n")

    def bucket(prob, pred):
        if pred == 1 and prob >= 0.75:
            return "HIGH_CONF_SIF"
        if pred == 1 and prob < 0.75:
            return "LOW_CONF_REVIEW"
        if pred == 0 and prob <= 0.25:
            return "HIGH_CONF_NON_SIF"
        return "LOW_CONF_REVIEW"

    test_df["sif_prob_mlp"] = y_prob
    test_df["sif_pred_mlp"] = y_pred
    test_df["bucket_mlp"] = [bucket(pr, pd_) for pr, pd_ in zip(y_prob, y_pred)]
    bucket_counts = test_df["bucket_mlp"].value_counts().to_dict()
    report_lines.append(f"\n**4-bucket routing on test set:** {bucket_counts}\n")

    # ---------------------------------------------------------------------------
    # MODEL 3b — MLP for LSR tagging (multi-class)
    # ---------------------------------------------------------------------------
    print("Training Model 3b (MLP LSR tagging)...")
    lsr_df = df[df.lsr_tag != "N/A"].copy()
    lsr_train, lsr_test = train_test_split(
        lsr_df, test_size=0.2, random_state=RANDOM_STATE, stratify=lsr_df.lsr_tag
    )
    lsr_vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=8000, stop_words="english")
    Xl_train = lsr_vectorizer.fit_transform(lsr_train.report_text_preprocessed).toarray()
    Xl_test = lsr_vectorizer.transform(lsr_test.report_text_preprocessed).toarray()

    lsr_mlp = MLPClassifier(
        hidden_layer_sizes=(128, 64), activation="relu", solver="adam", alpha=1e-4,
        learning_rate_init=1e-3, max_iter=300, early_stopping=True, validation_fraction=0.1,
        n_iter_no_change=15, random_state=RANDOM_STATE,
    )
    lsr_label_encoder = LabelEncoder()
    y_lsr_train_enc = lsr_label_encoder.fit_transform(lsr_train.lsr_tag)
    lsr_mlp.fit(Xl_train, y_lsr_train_enc)
    lsr_pred_enc = lsr_mlp.predict(Xl_test)
    lsr_pred = lsr_label_encoder.inverse_transform(lsr_pred_enc)

    report_lines.append(f"\n## Model 3b — MLP Neural Network (LSR tagging, multi-class)\n")
    report_lines.append(f"Trained for {lsr_mlp.n_iter_} epochs (early-stopped: {lsr_mlp.n_iter_ < 300})\n")
    report_lines.append("```\n" + classification_report(lsr_test.lsr_tag, lsr_pred, zero_division=0) + "\n```\n")

    # ---------------------------------------------------------------------------
    # Save real trained artifacts into aiml/models/mlp/
    # ---------------------------------------------------------------------------
    sif_artifact = {"vectorizer": vectorizer, "model": calibrated_mlp}
    lsr_artifact = {"vectorizer": lsr_vectorizer, "model": lsr_mlp, "label_encoder": lsr_label_encoder}

    with open(MLP_DIR / "mlp_sif_model.pkl", "wb") as f:
        pickle.dump(sif_artifact, f)
    with open(MLP_DIR / "sif_classifier_model3_mlp.pkl", "wb") as f:
        pickle.dump(sif_artifact, f)

    with open(MLP_DIR / "mlp_lsr_model.pkl", "wb") as f:
        pickle.dump(lsr_artifact, f)
    with open(MLP_DIR / "lsr_classifier_model3b_mlp.pkl", "wb") as f:
        pickle.dump(lsr_artifact, f)

    # Save individual components as well
    with open(MLP_DIR / "vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open(MLP_DIR / "label_encoder.pkl", "wb") as f:
        pickle.dump(lsr_label_encoder, f)

    print(f"Saved MLP model artifacts to {MLP_DIR}")

    report_lines.append(
        "\n## Comparison to prior models (same test set, same random_state=42 split)\n\n"
        "| Model | Precision | Recall | F1 | F2 | ROC-AUC | PR-AUC |\n"
        "|---|---|---|---|---|---|---|\n"
        "| Baseline 1 (rule, preprocessed) | 0.836 | 0.508 | 0.632 | — | — | — |\n"
        f"| Baseline 2 (TF-IDF + LogReg, preprocessed) | {BASELINE2_P:.3f} | {BASELINE2_R:.3f} | "
        f"{BASELINE2_F1:.3f} | {BASELINE2_F2:.3f} | {BASELINE2_ROC:.3f} | {BASELINE2_PRAUC:.3f} |\n"
        f"| **Model 3 (MLP, preprocessed)** | {p:.3f} | {r:.3f} | {f1:.3f} | {f2:.3f} | {roc_auc:.3f} | {pr_auc:.3f} |\n\n"
    )

    recall_delta = r - BASELINE2_R
    f2_delta = f2 - BASELINE2_F2
    if recall_delta > 0.01 and f2_delta > 0.01:
        verdict = (
            f"**Verdict: Model 3 wins.** Recall improved by {recall_delta:+.3f} and F2 by {f2_delta:+.3f} "
            "over Baseline 2 — the added nonlinear capacity earns its place. Promote Model 3 to the "
            "production candidate."
        )
    else:
        verdict = (
            f"**Verdict: Model 3 does NOT earn its place.** Recall changed by {recall_delta:+.3f} and F2 by "
            f"{f2_delta:+.3f} relative to Baseline 2 — on the metric this project has committed to "
            "prioritizing (recall/F2, per the VelocityEHS PSIF precedent), the simpler linear model is "
            "equal or better. This is a real, honest result, not a disappointing one: with ~2,400 training "
            "examples and high-dimensional sparse TF-IDF input, a 128->64 MLP has far more capacity than the "
            "data supports, and linear models are well known to generalize better than deeper nonlinear ones "
            "in exactly this low-data / high-dimensional-sparse-feature regime. **Recommendation: keep "
            "Baseline 2 (TF-IDF + Logistic Regression) as the working SIF-potential classifier** until a "
            "pretrained transformer (fine-tuned on a machine with GPU/internet access) "
            "is evaluated, since transfer learning from pretrained language representations is the "
            "principled way to add capacity without needing more labeled data than this project currently has."
        )
    report_lines.append(verdict + "\n")

    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(report_lines))

    print(f"Report written to {REPORT_PATH}")
    print(verdict)


if __name__ == "__main__":
    train_and_eval()
