"""CLI entry point for generating the clearly-labelled synthetic UA/UC corpus.

    python scripts/generate_synthetic_data.py --n 25000

Writes data/synthetic/synthetic_uauc_reports.csv plus a companion
dataset_card.md documenting exactly how the corpus was built and what it may
and may not be used to claim.
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from sif_engine.data_generation.synthetic_generator import (  # noqa: E402
    PLANTED_PATTERNS,
    generate,
)


def write_dataset_card(rows: list[dict], out_dir: Path, n: int, seed: int) -> None:
    sif_rate = sum(r["sif_potential"] for r in rows) / len(rows)
    truth_rate = sum(r["sif_potential_truth"] for r in rows) / len(rows)
    span_total = sum(len(json.loads(r["spans"])) for r in rows)
    sites = Counter(r["site"] for r in rows)
    energy = Counter(r["energy_type"] for r in rows)
    lsr = Counter(r["lsr_tag"] for r in rows if r["lsr_tag"] != "N/A")

    lines = [
        "# Synthetic UA/UC Dataset Card",
        "",
        "**THIS IS NOT OIL INDIA DATA.** Every row carries `source=\"synthetic\"`.",
        "The corpus exists so the pipeline can be built and measured before any",
        "real OIL HSSE export is available. Metrics computed on it are *internal",
        "consistency validation*, not production validation.",
        "",
        "## Provenance",
        "",
        f"- Rows: **{len(rows):,}** (requested {n:,})",
        f"- Seed: `{seed}` (fully reproducible)",
        "- Window: 12 months ending 2026-09-01",
        f"- Gold NER spans: **{span_total:,}** across 5 entity types",
        "  (ACTIVITY, HAZARD, BARRIER, EXPOSURE, LOCATION)",
        "",
        "## Labelling logic (EEI SCL Model)",
        "",
        "```",
        "sif_potential = high_energy(energy_type)",
        "                AND exposure != no_exposure",
        "                AND NOT (barrier confirmed AND barrier is a DIRECT control)",
        "```",
        "",
        "The label is **independent of the stated outcome**. A no-injury near-miss",
        "with an absent barrier is positive; a first-aid case behind a verified",
        "mechanical barrier is negative. A confirmed *administrative* control",
        "(permit, journey plan) does not clear a high-energy exposure the way a",
        "confirmed *engineering* control does — the SCL direct-control test.",
        "",
        f"- Positive rate (as labelled, incl. 3% injected ambiguity): **{sif_rate:.1%}**",
        f"- Positive rate (noise-free ground truth): **{truth_rate:.1%}**",
        "- `sif_potential_truth` is retained so label-noise robustness can be measured.",
        "",
        "## Injected realism",
        "",
        "- Abbreviation substitution (PTW, LOTO, JSA, H2S, SIMOPS)",
        "- Field typos (`confimed`, `maintainance`, `wielding`, `isolaton`, ...)",
        "- Code-mixed Hindi/Assamese-influenced phrasing appended to ~35% of noisy rows",
        "- Terse fragment reports (~16%)",
        "- Inconsistent casing, trailing shift-log notes",
        "- ~35% of rows are left clean, mirroring a mix of careful and hurried reporters",
        "",
        "## Planted structure (so pattern discovery has real signal)",
        "",
        "| pattern_id | kind | site | barrier failure | n |",
        "|---|---|---|---|---|",
    ]
    for p in PLANTED_PATTERNS:
        lines.append(
            f"| `{p.pattern_id}` | {p.kind} | {p.site} | {p.energy_type} / {p.barrier_status} | {p.count} |"
        )
    lines += [
        "",
        "`emerging` patterns are concentrated in the final ~25% of the timeline so the",
        "CUSUM/EWMA early-warning layer has a genuine step change to detect.",
        "`sporadic_high_severity` patterns are deliberately too small to cluster as",
        "'recurring' — they must surface through the outlier view instead.",
        "",
        "## Distribution",
        "",
        "### Sites",
        "",
        "| site | reports |",
        "|---|---|",
    ]
    for s, c in sites.most_common():
        lines.append(f"| {s} | {c:,} |")
    lines += ["", "### Energy types", "", "| energy type | reports |", "|---|---|"]
    for e, c in energy.most_common():
        lines.append(f"| {e} | {c:,} |")
    lines += ["", "### Life-Saving Rule tags (positives only)", "", "| LSR | reports |", "|---|---|"]
    for k, c in lsr.most_common():
        lines.append(f"| {k} | {c:,} |")
    lines += [
        "",
        "## Known limitations",
        "",
        "- Generated from a finite phrase bank; a model can overfit the generator.",
        "- Real reports contain equipment tags, org-specific jargon and narrative",
        "  digressions this generator does not reproduce.",
        "- Real validation requires an OIL SME-reviewed gold set on real exports.",
        "",
    ]
    (out_dir / "dataset_card.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic UA/UC corpus.")
    parser.add_argument("--n", type=int, default=25000, help="number of reports")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    rows = generate(n=args.n, seed=args.seed, months=args.months)

    base_dir = Path(__file__).resolve().parent.parent
    out_file = Path(args.out) if args.out else base_dir / "data" / "synthetic" / "synthetic_uauc_reports.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())
    with open(out_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    write_dataset_card(rows, out_file.parent, args.n, args.seed)

    sif_rate = sum(r["sif_potential"] for r in rows) / len(rows)
    spans = sum(len(json.loads(r["spans"])) for r in rows)
    print(f"Generated {len(rows):,} synthetic reports -> {out_file}")
    print(f"  SIF-potential rate : {sif_rate:.3f}")
    print(f"  gold spans         : {spans:,}")
    print(f"  unique texts       : {len({r['report_text'] for r in rows}):,}")
    print(f"  dataset card       : {out_file.parent / 'dataset_card.md'}")


if __name__ == "__main__":
    main()
