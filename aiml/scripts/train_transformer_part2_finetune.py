"""PS 26165 transformer stage — Part 2: end-to-end fine-tuning.

Fine-tunes a given encoder (distilbert-base-uncased / microsoft/deberta-v3-small
/ microsoft/deberta-v3-base) END TO END for SIF-potential binary classification,
unlike Part 1's frozen-embedding + XGBoost approach. Uses the HF Trainer API
with a class-weighted loss (the dataset is ~43% positive but still imbalanced
enough, and this project has committed to a recall-priority stance) and
metric_for_best_model="recall" per this project's own reasoning: a missed
SIF-potential report is categorically worse than an extra false positive.

Run:
  python scripts/train_transformer_part2_finetune.py --model_name distilbert-base-uncased --output_name distilbert_finetuned
  python scripts/train_transformer_part2_finetune.py --model_name microsoft/deberta-v3-small --output_name deberta_v3_small
  python scripts/train_transformer_part2_finetune.py --model_name microsoft/deberta-v3-base --output_name deberta_v3_base
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _transformer_common import (  # noqa: E402
    MODELS_DIR,
    REPORTS_DIR,
    Timer,
    compute_metrics as full_compute_metrics,
    hardware_info,
    load_split,
)
from sif_engine.confidence.calibration import f_beta  # noqa: E402

MAX_LENGTH = 128


def build_datasets(tokenizer, train_df, val_df, test_df):
    def tok(batch):
        return tokenizer(batch["text_proc"], truncation=True, max_length=MAX_LENGTH)

    cols = ["text_proc", "sif_potential"]
    ds_train = Dataset.from_pandas(train_df[cols].rename(columns={"sif_potential": "labels"}))
    ds_val = Dataset.from_pandas(val_df[cols].rename(columns={"sif_potential": "labels"}))
    ds_test = Dataset.from_pandas(test_df[cols].rename(columns={"sif_potential": "labels"}))

    ds_train = ds_train.map(tok, batched=True).remove_columns(["text_proc"])
    ds_val = ds_val.map(tok, batched=True).remove_columns(["text_proc"])
    ds_test = ds_test.map(tok, batched=True).remove_columns(["text_proc"])
    return ds_train, ds_val, ds_test


def epoch_compute_metrics(eval_pred):
    logits, labels = eval_pred
    probs = torch.softmax(torch.tensor(logits), dim=-1)[:, 1].numpy()
    preds = (probs >= 0.5).astype(int)
    from sklearn.metrics import precision_recall_fscore_support, roc_auc_score, average_precision_score

    p, r, f1, _ = precision_recall_fscore_support(labels, preds, average="binary", zero_division=0)
    try:
        roc = roc_auc_score(labels, probs)
        pr = average_precision_score(labels, probs)
    except ValueError:
        roc, pr = 0.0, 0.0
    return {
        "precision": float(p),
        "recall": float(r),
        "f1": float(f1),
        "f2": f_beta(float(p), float(r), 2.0),
        "roc_auc": float(roc),
        "pr_auc": float(pr),
    }


class WeightedTrainer(Trainer):
    def __init__(self, *args, class_weights=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        # Cast weights to match logits' dtype, not just device: some
        # checkpoints (e.g. deberta-v3) are auto-loaded in fp16 regardless of
        # TrainingArguments.fp16, so a plain .to(device) leaves a fp32/fp16
        # mismatch that CrossEntropyLoss rejects.
        weight = self.class_weights.to(device=logits.device, dtype=logits.dtype)
        loss_fct = nn.CrossEntropyLoss(weight=weight)
        loss = loss_fct(logits.view(-1, model.config.num_labels), labels.view(-1))
        return (loss, outputs) if return_outputs else loss


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_name", required=True)
    ap.add_argument("--output_name", required=True)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--batch_size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    args = ap.parse_args()

    hw = hardware_info()
    print(f"hardware: {hw}")

    train_df, val_df, test_df = load_split()
    print(f"split: train={len(train_df)} val={len(val_df)} test={len(test_df)}")

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    # Force fp32 weights regardless of the checkpoint's stored torch_dtype
    # (deberta-v3 checkpoints are published in fp16, which HF auto-loads
    # unless overridden here - that mismatch is what broke both the fp16
    # GradScaler path and the plain-fp32 loss-weight path above).
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name, num_labels=2, torch_dtype=torch.float32
    )

    ds_train, ds_val, ds_test = build_datasets(tokenizer, train_df, val_df, test_df)
    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    y_train = train_df.sif_potential.values
    n_pos = int((y_train == 1).sum())
    n_neg = int((y_train == 0).sum())
    # inverse-frequency class weights, normalized so they average to 1.0
    w_pos = (n_pos + n_neg) / (2.0 * n_pos)
    w_neg = (n_pos + n_neg) / (2.0 * n_neg)
    class_weights = torch.tensor([w_neg, w_pos], dtype=torch.float32)
    print(f"class weights [neg, pos] = {class_weights.tolist()}")

    output_dir = MODELS_DIR / args.output_name
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=64,
        learning_rate=args.lr,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        load_best_model_at_end=True,
        metric_for_best_model="recall",
        greater_is_better=True,
        logging_steps=50,
        report_to=[],
        # DeBERTa-v2/v3's disentangled-attention autograd ops (XSoftmax /
        # StableDropout) do not produce gradients GradScaler can unscale
        # cleanly, which raises "Attempting to unscale FP16 gradients" under
        # fp16 AMP (a known HF/DeBERTa interaction, not specific to this
        # dataset) - so fp16 is only enabled for non-DeBERTa encoders.
        fp16=hw["device"] == "cuda" and "deberta" not in args.model_name.lower(),
        seed=42,
    )

    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=ds_train,
        eval_dataset=ds_val,
        data_collator=collator,
        compute_metrics=epoch_compute_metrics,
        class_weights=class_weights,
    )

    with Timer(f"finetune_{args.output_name}") as t_train:
        trainer.train()

    with Timer("predict_test"):
        pred_out = trainer.predict(ds_test)
    logits = pred_out.predictions
    probs = torch.softmax(torch.tensor(logits), dim=-1)[:, 1].numpy()
    preds = (probs >= 0.5).astype(int)
    y_test = test_df.sif_potential.values

    metrics = full_compute_metrics(y_test, preds, probs)
    metrics["train_seconds"] = round(t_train.elapsed, 1)
    metrics["hardware"] = hw
    metrics["model_name"] = args.model_name
    metrics["epochs"] = args.epochs
    metrics["batch_size"] = args.batch_size
    metrics["learning_rate"] = args.lr
    metrics["class_weights"] = class_weights.tolist()

    print(f"\n=== Part 2: fine-tuned {args.model_name} ===")
    print(json.dumps(metrics, indent=2))

    trainer.save_model(str(output_dir / "final"))
    tokenizer.save_pretrained(str(output_dir / "final"))

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_DIR / f"transformer_part2_{args.output_name}_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Saved: models/transformers/{args.output_name}/final/, "
          f"reports/transformer_part2_{args.output_name}_metrics.json")


if __name__ == "__main__":
    main()
