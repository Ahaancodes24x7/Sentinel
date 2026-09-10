"""PS 26165 transformer stage — Part 1: frozen DistilBERT [CLS] embeddings
+ XGBoost (the VelocityEHS PSIF paper's own methodology).

DistilBERT stays frozen (eval mode, no_grad) — no fine-tuning here. Only
the XGBoost classifier on top is trained. See
SIH_26165_Transformer_Stage_LLM_Prompt.md Part 1 for the full spec this
implements.

Run:  python scripts/train_transformer_part1_bert_xgboost.py
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import torch
import xgboost as xgb
from transformers import AutoModel, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _transformer_common import (  # noqa: E402
    MODELS_DIR,
    REPORTS_DIR,
    Timer,
    compute_metrics,
    hardware_info,
    load_split,
)

MODEL_NAME = "distilbert-base-uncased"
MAX_LENGTH = 128
BATCH_SIZE = 32


@torch.no_grad()
def embed_cls(texts: list[str], tokenizer, model, device) -> np.ndarray:
    model.eval()
    out = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        enc = tokenizer(
            batch, padding=True, truncation=True, max_length=MAX_LENGTH, return_tensors="pt"
        ).to(device)
        hidden = model(**enc).last_hidden_state  # (B, T, 768)
        cls = hidden[:, 0, :]  # [CLS] token
        out.append(cls.cpu().numpy())
        if (i // BATCH_SIZE) % 20 == 0:
            print(f"  embedded {i + len(batch)}/{len(texts)}")
    return np.vstack(out)


def main() -> None:
    hw = hardware_info()
    print(f"hardware: {hw}")
    device = torch.device(hw["device"])

    train_df, val_df, test_df = load_split()
    print(f"split: train={len(train_df)} val={len(val_df)} test={len(test_df)}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).to(device)
    for p in model.parameters():
        p.requires_grad_(False)

    with Timer("embed_train") as t_emb_train:
        X_train = embed_cls(train_df.text_proc.tolist(), tokenizer, model, device)
    with Timer("embed_val"):
        X_val = embed_cls(val_df.text_proc.tolist(), tokenizer, model, device)
    with Timer("embed_test"):
        X_test = embed_cls(test_df.text_proc.tolist(), tokenizer, model, device)

    y_train = train_df.sif_potential.values
    y_val = val_df.sif_potential.values
    y_test = test_df.sif_potential.values

    n_pos = int((y_train == 1).sum())
    n_neg = int((y_train == 0).sum())
    scale_pos_weight = n_neg / n_pos
    print(f"train class balance: pos={n_pos} neg={n_neg} scale_pos_weight={scale_pos_weight:.3f}")

    clf = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        early_stopping_rounds=20,
        random_state=42,
        n_jobs=-1,
    )

    with Timer("xgb_fit") as t_fit:
        clf.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    print(f"best_iteration={clf.best_iteration}")

    y_prob = clf.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)
    metrics = compute_metrics(y_test, y_pred, y_prob)
    metrics["train_seconds"] = round(t_fit.elapsed, 1)
    metrics["embed_seconds"] = round(t_emb_train.elapsed, 1)
    metrics["hardware"] = hw
    metrics["scale_pos_weight"] = round(scale_pos_weight, 4)
    metrics["best_iteration"] = int(clf.best_iteration) if clf.best_iteration is not None else None

    importances = clf.feature_importances_
    top_idx = np.argsort(-importances)[:20]
    metrics["top_feature_importance"] = [
        {"embedding_dim": int(i), "importance": round(float(importances[i]), 5)} for i in top_idx
    ]

    print("\n=== Part 1: DistilBERT (frozen) + XGBoost ===")
    print(json.dumps({k: v for k, v in metrics.items() if k != "top_feature_importance"}, indent=2))

    save_pickle = {"model": clf, "model_name": MODEL_NAME, "max_length": MAX_LENGTH}
    with open(MODELS_DIR / "part1_bert_xgboost.pkl", "wb") as f:
        pickle.dump(save_pickle, f)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_DIR / "transformer_part1_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # cache embeddings for Part 3 (hybrid) reuse, keyed by report_id
    np.savez(
        MODELS_DIR / "part1_embeddings.npz",
        X_train=X_train, X_val=X_val, X_test=X_test,
        train_ids=train_df.report_id.values, val_ids=val_df.report_id.values, test_ids=test_df.report_id.values,
    )
    print("Saved: models/transformers/part1_bert_xgboost.pkl, part1_embeddings.npz, "
          "reports/transformer_part1_metrics.json")


if __name__ == "__main__":
    main()
