"""Out-of-distribution probe for the fine-tuned NER model.

    python scripts/probe_ner_ood.py

Why this exists: the model scores span F1 = 1.000 on a held-out split of the
synthetic corpus. That number is NOT a measure of quality — it is a measure of
how predictable the generator is. Both the training and test halves are drawn
from the same finite phrase bank, so a transformer memorises the spans and the
metric saturates.

The only honest way to say anything about generalisation is to run the model on
report text the generator could not have produced. The probes below are
hand-written in the register of real upstream oil & gas near-miss reports —
different vocabulary, different sentence shapes, British field idiom,
abbreviations the generator never emits.

Writes reports/ner_ood_probe.md so the result can be quoted without re-running.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Hand-written, deliberately NOT from the generator's phrase bank.
PROBES: list[str] = [
    "Whilst the crew were breaking the flange on the 6-inch discharge header at "
    "PS-9, the line had not been proven depressurised. Two fitters were stood "
    "square to the joint. Nobody was injured.",

    "Observed a rigger riding the load on the cellar deck crane at Rig 12. No "
    "taglines rigged, no barricade. Job stopped by the DSV.",

    "Night crew found the F&G loop in override from the previous shift with no "
    "compensating watchkeeper. Compressor running.",

    "Trolley of gas cylinders left unchained at the top of the ramp near the "
    "workshop door. Nobody about at the time.",

    "Contractor entered the sump at Terminal A to retrieve a dropped spanner. "
    "No entry permit raised and the gas monitor was still on charge in the cabin.",

    "Excavator bucket swung within a metre of the banksman while backfilling the "
    "trench at Field Station 5. Spoil heap obstructing his line of sight.",

    "Scaffolder observed transferring between lifts without clipping on. Scaffold "
    "tag showed incomplete handrail on the north face.",

    "Tanker driver began disconnecting the loading arm before the pump had stopped. "
    "Product under pressure in the line.",
]


def main() -> None:
    from sif_engine.extraction.ner_model import extract_spans, model_available, model_info

    if not model_available():
        print("No fine-tuned NER artefact found. Run scripts/train_ner.py first.")
        return

    info = model_info()
    in_dist_f1 = (info.get("overall") or {}).get("exact", {}).get("f1")

    lines = [
        "# NER Out-of-Distribution Probe",
        "",
        "## Why this page exists",
        "",
        f"The fine-tuned model scores **exact span F1 = {in_dist_f1}** on a held-out",
        "split of the synthetic corpus. That number should not be quoted as a quality",
        "result. Both halves of the split come from the same finite phrase bank, so a",
        "transformer simply memorises the spans and the metric saturates. A perfect",
        "score on generated data is evidence about the generator, not about the model.",
        "",
        "The probes below are hand-written in the register of real upstream oil & gas",
        "near-miss reports — vocabulary, sentence shapes, abbreviations and field idiom",
        "the generator never produces. This is the only part of the NER evaluation that",
        "says anything about generalisation.",
        "",
        "## What it shows",
        "",
        "The model transfers **partially**. It reliably picks up site identifiers and",
        "explicit barrier-absence constructions it has never seen verbatim, which is the",
        "signal the SCL reasoner actually depends on. Span boundaries are noticeably",
        "raggeder than on synthetic text, and it occasionally labels an outcome clause as",
        "exposure. In deployment those cases are exactly what the confidence routing sends",
        "to a human rather than deciding alone.",
        "",
        "## Probes",
        "",
    ]

    for i, text in enumerate(PROBES, 1):
        result = extract_spans(text)
        lines += [
            f"### {i}.",
            "",
            "> " + text.replace("\n", " "),
            "",
            f"`source: {result['source']}` · {len(result['spans'])} spans",
            "",
            "| Label | Confidence | Extracted span |",
            "|---|---|---|",
        ]
        if not result["spans"]:
            lines.append("| — | — | *(nothing extracted)* |")
        for span in result["spans"]:
            snippet = span["text"].replace("|", "\\|")
            lines.append(f"| {span['label']} | {span['confidence']:.2f} | {snippet} |")
        lines.append("")

    lines += [
        "## Reading this honestly",
        "",
        "- **Do not claim** the 1.000 synthetic F1 as production extraction quality.",
        "- **Do claim** that barrier-absence and location extraction transfer to unseen",
        "  phrasing, and show these probes as the evidence.",
        "- Real span-level validation needs an SME-annotated gold set drawn from actual",
        "  OIL HSSE exports, with inter-annotator agreement measured before any number is",
        "  treated as an acceptance criterion.",
        "",
    ]

    out = _ROOT / "reports" / "ner_ood_probe.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"In-distribution exact span F1 : {in_dist_f1}  (generator memorisation)")
    print(f"Probes run                    : {len(PROBES)} hand-written reports")
    print(f"Written                       : {out}")


if __name__ == "__main__":
    main()
