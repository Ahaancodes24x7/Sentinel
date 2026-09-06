"""Reusable classification metrics for baseline and production models."""

from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, precision_recall_fscore_support, roc_auc_score


def compute_metrics(y_true, y_pred, y_prob=None) -> dict:
    """Compute precision, recall, F1, F2, optional ranking/calibration metrics, and confusion matrix."""
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    f2 = 5 * precision * recall / (4 * precision + recall) if precision + recall else 0.0
    result = {"precision": precision, "recall": recall, "f1": f1, "f2": f2, "confusion_matrix": confusion_matrix(y_true, y_pred).tolist()}
    if y_prob is not None:
        result.update({"roc_auc": roc_auc_score(y_true, y_prob), "pr_auc": average_precision_score(y_true, y_prob), "brier": brier_score_loss(y_true, y_prob)})
    return result