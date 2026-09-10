"""PS 26165 transformer stage — Part 3: hybrid transformer embedding +
NegEx feature concatenation.

Concatenates [transformer embedding] + [NegExSafetyFeatureExtractor's
30-dim output] and trains a final classifier on the combined vector. This
is the actual architectural point of the transformer-stage exercise: the
transformer captures general semantic similarity, but has no guarantee of
capturing this project's negation-scope barrier-status requirement (e.g.
"not re-verified" vs "re-verified") the way the purpose-built NegEx
extractor does — see feature_extractor.py's module docstring.

--embedding_source part1_bert   : reuse Part 1's cached frozen-DistilBERT
                                   [CLS] embeddings (models/transformers/part1_embeddings.npz)
                                   + XGBoost head.
--embedding_source finetuned    : re-embed with a Part-2 fine-tuned encoder's
                                   own [CLS] hidden state (its "pooled output")
                                   + a small MLP/LogReg head.

Run (after Part 1 and Part 2 have both been evaluated and the winner on F2
is known):
  python scripts/train_transformer_part3_hybrid.py --embedding_source part1_bert
  python scripts/train_transformer_part3_hybrid.py --embedding_source finetuned --finetuned_dir models/transformers/deberta_v3_small/final --classifier mlp
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import torch
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _transformer_common import (  # noqa: E402
    MODELS_DIR,
    REPORTS_DIR,
    Timer,
    compute_metrics,
    hardware_info,
    load_split,
)
from sif_engine.extraction.feature_extractor import NegExSafetyFeatureExtractor  # noqa: E402

MAX_LENGTH = 128
BATCH_SIZE = 32


@torch.no_grad()
def embed_finetuned(texts: list[str], tokenizer, model, device) -> np.ndarray:
    model.eval()
    out = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        enc = tokenizer(batch, padding=True, truncation=True, max_length=MAX_LENGTH, return_tensors="pt").to(device)
        hidden = model.base_model(**enc).last_hidden_state
        out.append(hidden[:, 0, :].cpu().numpy())
    return np.vstack(out)


def get_embeddings(args, train_df, val_df, test_df):
    if args.embedding_source == "part1_bert":
        cached = np.load(MODELS_DIR / "part1_embeddings.npz", allow_pickle=True)
        # cached was saved in the same load_split() order; ids let us verify alignment
        assert (cached["train_ids"] == train_df.report_id.values).all(), "train split mismatch vs cached embeddings"
        assert (cached["val_ids"] == val_df.report_id.values).all(), "val split mismatch vs cached embeddings"
        assert (cached["test_ids"] == test_df.report_id.values).all(), "test split mismatch vs cached embeddings"
        return cached["X_train"], cached["X_val"], cached["X_test"], "distilbert-base-uncased (frozen, Part 1 cache)"

    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    hw = hardware_info()
    device = torch.device(hw["device"])
    tokenizer = AutoTokenizer.from_pretrained(args.finetuned_dir)
    model = AutoModelForSequenceClassification.from_pretrained(args.finetuned_dir).to(device)

    with Timer("embed_finetuned_train"):
        X_train = embed_finetuned(train_df.text_proc.tolist(), tokenizer, model, device)
    with Timer("embed_finetuned_val"):
        X_val = embed_finetuned(val_df.text_proc.tolist(), tokenizer, model, device)
    with Timer("embed_finetuned_test"):
        X_test = embed_finetuned(test_df.text_proc.tolist(), tokenizer, model, device)
    return X_train, X_val, X_test, f"{args.finetuned_dir} (fine-tuned, pooled [CLS] hidden state)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--embedding_source", choices=["part1_bert", "finetuned"], required=True)
    ap.add_argument("--finetuned_dir", default=None, help="required if embedding_source=finetuned")
    ap.add_argument("--classifier", choices=["xgboost", "mlp", "logreg"], default=None,
                     help="defaults to xgboost for part1_bert, mlp for finetuned")
    args = ap.parse_args()
    if args.embedding_source == "finetuned" and not args.finetuned_dir:
        raise SystemExit("--finetuned_dir is required when --embedding_source=finetuned")
    if args.classifier is None:
        args.classifier = "xgboost" if args.embedding_source == "part1_bert" else "mlp"

    hw = hardware_info()
    print(f"hardware: {hw}")

    train_df, val_df, test_df = load_split()
    print(f"split: train={len(train_df)} val={len(val_df)} test={len(test_df)}")

    with Timer("get_embeddings"):
        emb_train, emb_val, emb_test, embedding_desc = get_embeddings(args, train_df, val_df, test_df)
    print(f"embedding source: {embedding_desc} (dim={emb_train.shape[1]})")

    negex = NegExSafetyFeatureExtractor()
    negex.fit(train_df.text_proc)  # stateless, but fit-on-train for pipeline-shape discipline
    with Timer("negex_transform"):
        feat_train = negex.transform(train_df.text_proc)
        feat_val = negex.transform(val_df.text_proc)
        feat_test = negex.transform(test_df.text_proc)
    print(f"NegEx feature dim: {feat_train.shape[1]}")

    X_train = np.hstack([emb_train, feat_train])
    X_val = np.hstack([emb_val, feat_val])
    X_test = np.hstack([emb_test, feat_test])
    print(f"hybrid vector dim: {X_train.shape[1]} ({emb_train.shape[1]} embedding + {feat_train.shape[1]} NegEx)")

    y_train = train_df.sif_potential.values
    y_val = val_df.sif_potential.values
    y_test = test_df.sif_potential.values

    if args.classifier == "xgboost":
        n_pos, n_neg = int((y_train == 1).sum()), int((y_train == 0).sum())
        clf = xgb.XGBClassifier(
            n_estimators=500, max_depth=6, learning_rate=0.05,
            subsample=0.9, colsample_bytree=0.9,
            scale_pos_weight=n_neg / n_pos, eval_metric="logloss",
            early_stopping_rounds=20, random_state=42, n_jobs=-1,
        )
        with Timer("fit_hybrid_clf") as t_fit:
            clf.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        y_prob = clf.predict_proba(X_test)[:, 1]
        scaler = None
    elif args.classifier == "mlp":
        scaler = StandardScaler().fit(X_train)
        Xt, Xv, Xte = scaler.transform(X_train), scaler.transform(X_val), scaler.transform(X_test)
        clf = MLPClassifier(
            hidden_layer_sizes=(128, 64), activation="relu", solver="adam",
            alpha=1e-4, early_stopping=True, n_iter_no_change=10,
            validation_fraction=0.15, max_iter=200, random_state=42,
        )
        with Timer("fit_hybrid_clf") as t_fit:
            clf.fit(Xt, y_train)
        y_prob = clf.predict_proba(Xte)[:, 1]
    else:  # logreg
        scaler = StandardScaler().fit(X_train)
        Xt, Xte = scaler.transform(X_train), scaler.transform(X_test)
        clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, random_state=42)
        with Timer("fit_hybrid_clf") as t_fit:
            clf.fit(Xt, y_train)
        y_prob = clf.predict_proba(Xte)[:, 1]

    y_pred = (y_prob >= 0.5).astype(int)
    metrics = compute_metrics(y_test, y_pred, y_prob)
    metrics["train_seconds"] = round(t_fit.elapsed, 1)
    metrics["hardware"] = hw
    metrics["embedding_source"] = embedding_desc
    metrics["classifier"] = args.classifier
    metrics["hybrid_dim"] = int(X_train.shape[1])
    metrics["negex_dim"] = int(feat_train.shape[1])
    metrics["embedding_dim"] = int(emb_train.shape[1])

    print("\n=== Part 3: Hybrid (transformer embedding + NegEx) ===")
    print(json.dumps(metrics, indent=2))

    out_name = f"part3_hybrid_{args.embedding_source}_{args.classifier}"
    with open(MODELS_DIR / f"{out_name}.pkl", "wb") as f:
        pickle.dump({"classifier": clf, "scaler": scaler, "args": vars(args)}, f)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_DIR / f"transformer_{out_name}_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Saved: models/transformers/{out_name}.pkl, reports/transformer_{out_name}_metrics.json")


if __name__ == "__main__":
    main()
