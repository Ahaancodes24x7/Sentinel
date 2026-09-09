"""Fine-tune DistilBERT for safety-event span extraction (Stage 1).

    python scripts/train_ner.py --samples 12000 --epochs 3

Trains a token-classification head over five entity types (ACTIVITY, HAZARD,
BARRIER, EXPOSURE, LOCATION) using the gold character spans emitted by the
synthetic generator, and evaluates with span-level precision/recall/F1 in both
EXACT and PARTIAL (overlap) matching modes.

Partial match is reported deliberately: "gas isolation valve" vs "isolation
valve" is a near-miss extraction that a reviewer would accept with one click,
and scoring it as a total failure would misrepresent how usable the output is.
Both numbers are shown so neither can be quoted misleadingly.

A plain PyTorch loop is used rather than `Trainer` — fewer moving parts, no
dependence on a fast-moving high-level API, and the whole thing stays readable
and CPU-friendly for an on-prem deployment.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sif_engine.extraction.ner_model import (  # noqa: E402
    BASE_MODEL,
    ENTITY_TYPES,
    ID2LABEL,
    LABEL2ID,
    LABELS,
    MODEL_DIR,
)

DATA_PATH = _ROOT / "data" / "synthetic" / "synthetic_uauc_reports.csv"


# --------------------------------------------------------------------------
# Span-level evaluation
# --------------------------------------------------------------------------


def spans_from_bio(tokens_offsets, label_ids, text: str) -> list[tuple[str, int, int]]:
    """Decode BIO predictions back into (label, start, end) character spans."""
    spans: list[tuple[str, int, int]] = []
    current_label = None
    current_start = None
    current_end = None

    for (start, end), lid in zip(tokens_offsets, label_ids):
        if start == end:
            continue
        tag = ID2LABEL.get(int(lid), "O")
        if tag == "O":
            if current_label is not None:
                spans.append((current_label, current_start, current_end))
                current_label = None
            continue
        prefix, _, entity = tag.partition("-")
        if prefix == "B" or current_label != entity:
            if current_label is not None:
                spans.append((current_label, current_start, current_end))
            current_label, current_start, current_end = entity, start, end
        else:
            current_end = end

    if current_label is not None:
        spans.append((current_label, current_start, current_end))
    return spans


def score_spans(gold: list[tuple], pred: list[tuple], mode: str = "exact") -> tuple[int, int, int]:
    """Return (true_positives, n_pred, n_gold) for one document."""
    used = set()
    tp = 0
    for g in gold:
        for i, p in enumerate(pred):
            if i in used or p[0] != g[0]:
                continue
            if mode == "exact":
                hit = (p[1] == g[1] and p[2] == g[2])
            else:                      # partial: any character overlap
                hit = (p[1] < g[2] and p[2] > g[1])
            if hit:
                used.add(i)
                tp += 1
                break
    return tp, len(pred), len(gold)


def prf(tp: int, n_pred: int, n_gold: int) -> dict[str, float]:
    precision = tp / n_pred if n_pred else 0.0
    recall = tp / n_gold if n_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4),
            "f1": round(f1, 4), "tp": tp, "n_pred": n_pred, "n_gold": n_gold}


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=12000)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--max-length", type=int, default=192)
    ap.add_argument("--data", default=str(DATA_PATH))
    args = ap.parse_args()

    import torch
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    torch.manual_seed(42)
    random.seed(42)
    np.random.seed(42)
    torch.set_num_threads(max(1, (__import__("os").cpu_count() or 4)))

    print(f"Loading {args.data}")
    df = pd.read_csv(args.data).fillna("")
    df = df.sample(min(args.samples, len(df)), random_state=42).reset_index(drop=True)
    print(f"  {len(df):,} reports for NER training")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    records = []
    for _, row in df.iterrows():
        spans = json.loads(row["spans"]) if row["spans"] else []
        if not spans:
            continue
        records.append({"text": str(row["report_text"]), "spans": spans})
    print(f"  {len(records):,} usable (with gold spans)")

    split = int(len(records) * 0.85)
    train_recs, test_recs = records[:split], records[split:]
    print(f"  train={len(train_recs):,} test={len(test_recs):,}")

    def encode(rec):
        enc = tokenizer(rec["text"], truncation=True, max_length=args.max_length,
                        padding="max_length", return_offsets_mapping=True)
        offsets = enc["offset_mapping"]
        labels = []
        for idx, (start, end) in enumerate(offsets):
            if start == end or enc["attention_mask"][idx] == 0:
                labels.append(-100)
                continue
            tag = "O"
            for span in rec["spans"]:
                s, e = span["span"]
                if start < e and end > s:            # any overlap
                    tag = f"B-{span['label']}" if start <= s else f"I-{span['label']}"
                    break
            labels.append(LABEL2ID.get(tag, 0))
        return {
            "input_ids": enc["input_ids"],
            "attention_mask": enc["attention_mask"],
            "labels": labels,
            "offset_mapping": offsets,
        }

    class NERDataset(Dataset):
        def __init__(self, recs):
            self.items = [encode(r) for r in recs]

        def __len__(self):
            return len(self.items)

        def __getitem__(self, i):
            it = self.items[i]
            return {
                "input_ids": torch.tensor(it["input_ids"]),
                "attention_mask": torch.tensor(it["attention_mask"]),
                "labels": torch.tensor(it["labels"]),
            }

    print("Encoding...")
    t0 = time.time()
    train_ds = NERDataset(train_recs)
    print(f"  encoded in {time.time() - t0:.0f}s")

    model = AutoModelForTokenClassification.from_pretrained(
        BASE_MODEL, num_labels=len(LABELS),
        id2label=ID2LABEL, label2id=LABEL2ID,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    total_steps = len(loader) * args.epochs
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=args.lr, total_steps=total_steps, pct_start=0.1
    )

    print(f"Training {args.epochs} epochs x {len(loader)} steps (batch {args.batch_size})")
    model.train()
    step = 0
    t_train = time.time()
    for epoch in range(args.epochs):
        running = 0.0
        for batch in loader:
            optimizer.zero_grad()
            out = model(**batch)
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            running += float(out.loss)
            step += 1
            if step % 50 == 0:
                elapsed = time.time() - t_train
                rate = step / elapsed
                eta = (total_steps - step) / rate if rate > 0 else 0
                print(f"  epoch {epoch + 1} step {step}/{total_steps} "
                      f"loss={running / 50:.4f} {rate:.2f} it/s ETA {eta / 60:.1f}m",
                      flush=True)
                running = 0.0
    print(f"  trained in {(time.time() - t_train) / 60:.1f} min")

    # ---------------------------------------------------------------- evaluate
    print("Evaluating span extraction...")
    model.eval()
    totals = {
        "exact": defaultdict(lambda: [0, 0, 0]),
        "partial": defaultdict(lambda: [0, 0, 0]),
    }
    overall = {"exact": [0, 0, 0], "partial": [0, 0, 0]}

    with torch.no_grad():
        for rec in test_recs:
            enc = tokenizer(rec["text"], truncation=True, max_length=args.max_length,
                            return_offsets_mapping=True, return_tensors="pt")
            offsets = enc.pop("offset_mapping")[0].tolist()
            logits = model(**enc).logits[0]
            pred_ids = logits.argmax(-1).tolist()
            pred_spans = spans_from_bio(offsets, pred_ids, rec["text"])
            gold_spans = [(s["label"], s["span"][0], s["span"][1]) for s in rec["spans"]]

            for mode in ("exact", "partial"):
                tp, npred, ngold = score_spans(gold_spans, pred_spans, mode)
                overall[mode][0] += tp
                overall[mode][1] += npred
                overall[mode][2] += ngold
                for ent in ENTITY_TYPES:
                    g = [s for s in gold_spans if s[0] == ent]
                    pr = [s for s in pred_spans if s[0] == ent]
                    etp, enp, eng = score_spans(g, pr, mode)
                    totals[mode][ent][0] += etp
                    totals[mode][ent][1] += enp
                    totals[mode][ent][2] += eng

    metrics = {
        "base_model": BASE_MODEL,
        "n_train": len(train_recs),
        "n_test": len(test_recs),
        "epochs": args.epochs,
        "max_length": args.max_length,
        "overall": {m: prf(*overall[m]) for m in ("exact", "partial")},
        "per_entity": {
            m: {ent: prf(*totals[m][ent]) for ent in ENTITY_TYPES}
            for m in ("exact", "partial")
        },
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    print(f"  span F1 exact   = {metrics['overall']['exact']['f1']:.4f}")
    print(f"  span F1 partial = {metrics['overall']['partial']['f1']:.4f}")
    for ent in ENTITY_TYPES:
        e = metrics["per_entity"]["exact"][ent]
        p = metrics["per_entity"]["partial"][ent]
        print(f"    {ent:<10} exact F1={e['f1']:.3f}  partial F1={p['f1']:.3f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(MODEL_DIR))
    tokenizer.save_pretrained(str(MODEL_DIR))
    (MODEL_DIR / "sentinel_meta.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    (_ROOT / "reports" / "ner_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    print(f"Saved -> {MODEL_DIR}")


if __name__ == "__main__":
    main()
