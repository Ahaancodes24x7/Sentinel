"""Assembles aiml/reports/transformer_evaluation_report.md from:
  - aiml/reports/metrics.json                          (B1-B5 classical-ML ladder, sentinel-v2.0)
  - aiml/reports/transformer_part1_metrics.json          (frozen DistilBERT + XGBoost)
  - aiml/reports/transformer_part2_<name>_metrics.json   (one per fine-tuned model)
  - aiml/reports/transformer_part3_hybrid_*_metrics.json (one per hybrid variant run)

Run this LAST, after Parts 1-3 have all produced their metrics files.
"""

from __future__ import annotations

import json
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
OUT_PATH = REPORTS_DIR / "transformer_evaluation_report.md"


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def row(name: str, m: dict | None) -> str:
    if m is None:
        return f"| {name} | — | — | — | — | — | — | — | — |"
    def g(k, fmt="{:.3f}"):
        v = m.get(k)
        return fmt.format(v) if isinstance(v, (int, float)) else "—"
    return (
        f"| {name} | {g('precision')} | {g('recall')} | {g('f1')} | {g('f2')} | "
        f"{g('roc_auc')} | {g('pr_auc')} | {g('brier','{:.4f}')} | {m.get('train_seconds','—')} |"
    )


def main() -> None:
    baselines = load_json(REPORTS_DIR / "metrics.json") or {}
    b = baselines.get("baselines", {})

    b1 = b.get("B1_rule_keyword")
    b2 = b.get("B2_tfidf_logreg")
    b4 = b.get("B4_calibrated_production")
    b5 = b.get("B5_hybrid_reasoner")

    part1 = load_json(REPORTS_DIR / "transformer_part1_metrics.json")
    part2_files = sorted(REPORTS_DIR.glob("transformer_part2_*_metrics.json"))
    part2 = {f.stem.replace("transformer_part2_", "").replace("_metrics", ""): load_json(f) for f in part2_files}
    part3_files = sorted(REPORTS_DIR.glob("transformer_part3_*_metrics.json"))
    part3 = {f.stem.replace("transformer_", "").replace("_metrics", ""): load_json(f) for f in part3_files}

    b2_f2 = (b2 or {}).get("f2", 0.0)

    lines = []
    lines.append("# PS 26165 / Sentinel — Transformer Stage Evaluation Report\n")
    lines.append(
        "Benchmarked against the CURRENT B1-B5 classical-ML ladder "
        "(`aiml/reports/model_evaluation_report.md`, model_version `sentinel-v2.0`, "
        "25,000-row dataset), not the older ~3,000-row table embedded in "
        "`SIH_26165_Transformer_Stage_LLM_Prompt.md`. Split reproduced exactly "
        "(stratified 60/20/20 on `sif_potential`, `random_state=42`, via "
        "`train_test_split(test_size=0.4)` then `train_test_split(test_size=0.5)` "
        "on the remainder) so `test_df` here is IDENTICAL to B1-B5's test_df, not "
        "merely the same size — see `_transformer_common.py` for why the literal "
        "'test_size=0.2' instruction in the prompt was not followed.\n"
    )
    lines.append(
        f"> **Validation status: internal consistency only**, same caveat as the rest "
        "of this project's reports — measured on the synthetic corpus, not real OIL "
        "HSE data.\n"
    )

    lines.append("## Comparison table\n")
    lines.append("| Model | Precision | Recall | F1 | F2 | ROC-AUC | PR-AUC | Brier | Train (s) |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    lines.append(row("B1 keyword / rule", b1))
    lines.append(row("B2 TF-IDF + LogReg", b2))
    lines.append(row("B4 calibrated word+char (production)", b4))
    lines.append(row("B5 hybrid extraction + SCL reasoner", b5))
    lines.append(row("Part 1: DistilBERT (frozen) + XGBoost", part1))
    for name, m in part2.items():
        lines.append(row(f"Part 2: fine-tuned {name}", m))
    for name, m in part3.items():
        lines.append(row(f"Part 3: {name}", m))
    lines.append("")

    lines.append("## Verdict\n")

    candidates = {"Part 1 (DistilBERT+XGBoost)": part1}
    candidates.update({f"Part 2 ({k})": v for k, v in part2.items()})
    candidates.update({f"Part 3 ({k})": v for k, v in part3.items()})
    candidates = {k: v for k, v in candidates.items() if v is not None}

    if candidates:
        best_name = max(candidates, key=lambda k: candidates[k].get("f2", 0.0))
        best_f2 = candidates[best_name]["f2"]
        if best_f2 > b2_f2:
            lines.append(
                f"**{best_name}** beats Baseline 2 (F2 {best_f2:.3f} vs {b2_f2:.3f}) and is the "
                "recommended production Stage 1 SIF-potential classifier, on the measured numbers "
                "above.\n"
            )
        else:
            lines.append(
                f"**Nothing beats Baseline 2.** Best transformer variant ({best_name}) scores "
                f"F2={best_f2:.3f} against Baseline 2's F2={b2_f2:.3f} ({(best_f2-b2_f2):+.3f}). "
                "**Recommendation: keep B2/B4 (TF-IDF + Logistic Regression) as the production Stage 1 "
                "SIF-potential classifier.**\n\n"
                "Most likely reason: this is a ~25,000-row *synthetic, template-generated* corpus. "
                "Transformers' main advantage over linear bag-of-words models is capturing semantic "
                "nuance and generalizing across paraphrase/surface-form variation that a template "
                "generator, by construction, does not introduce — every category is realised from a "
                "finite phrase bank, so a linear model can recover the label by recognising the "
                "template as reliably as a transformer can from reading the situation (see this "
                "project's own 'saturated metrics' caveat in `model_evaluation_report.md`). "
                "Transformers' advantage is expected to show up more clearly on messier, more varied "
                "real-world text (typos, code-mixing, free-form phrasing) than this generator produces. "
                "**This result does not predict how these models will compare on real OIL India data — "
                "it only tells us which one currently wins on this specific synthetic corpus.**\n"
            )
    else:
        lines.append("No transformer metrics found — run Parts 1-3 before building this report.\n")

    lines.append("## Training time and hardware\n")
    lines.append("| Model | Hardware | Train time (s) |")
    lines.append("|---|---|---|")
    for label, m in [("Part 1 (DistilBERT+XGBoost)", part1)] + list(part2.items()) + list(part3.items()):
        if m is None:
            continue
        hw = m.get("hardware", {})
        device = hw.get("gpu_name") or hw.get("device", "cpu")
        lines.append(f"| {label} | {device} | {m.get('train_seconds', '—')} |")
    lines.append("")

    lines.append("## Notes\n")
    lines.append(
        "- Part 1 XGBoost feature importances are over raw BERT embedding dimensions "
        "(0-767), which are NOT individually interpretable the way NegEx features are — "
        "an importance ranking over them does not mean any single dimension has "
        "domain meaning; see `transformer_part1_metrics.json`'s `top_feature_importance` "
        "for the raw ranking, reported for completeness only.\n"
        "- Part 3's hybrid vector is [transformer embedding] + "
        "[NegExSafetyFeatureExtractor's 30 named dims], fit on train and transformed on "
        "train+val+test, per `feature_extractor.py`.\n"
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
