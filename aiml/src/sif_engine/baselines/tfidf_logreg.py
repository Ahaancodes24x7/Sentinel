"""TF-IDF plus calibrated logistic-regression baselines."""

from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .evaluate import compute_metrics


def _train(df, label_column: str, text_column: str = "report_text_preprocessed"):
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=5000, stop_words="english")
    X = vectorizer.fit_transform(df[text_column])
    model = CalibratedClassifierCV(LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42), method="sigmoid", cv=5)
    model.fit(X, df[label_column].values)
    probability = model.predict_proba(X)[:, 1]
    prediction = model.predict(X)
    return vectorizer, model, compute_metrics(df[label_column].values, prediction, probability)


def train_sif_classifier(df):
    """Train the binary SIF classifier and return vectorizer, model, metrics."""
    return _train(df, "sif_potential")


def train_lsr_classifier(df):
    """Train the LSR classifier on rows with an applicable LSR tag."""
    subset = df[df.lsr_tag != "N/A"].copy()
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=5000, stop_words="english")
    X = vectorizer.fit_transform(subset["report_text_preprocessed"])
    model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    model.fit(X, subset.lsr_tag)
    return vectorizer, model, {"classification": model.score(X, subset.lsr_tag)}


def train_eval_baseline2(df, text_col: str = "report_text_preprocessed", label: str = "sif_potential", save_artifacts: bool = False):
    """Compatibility entry point for the baseline training workflow."""
    return _train(df, label, text_col)