# SIH PS 26165 AI/ML Engine

This is the AI/ML codebase for SIH PS 26165, detecting Serious Injury & Fatality precursors in oil and gas safety reports.

- Stage 0: deterministic preprocessing
- Stage 1: NLP extraction and field classifiers
- Stage 2: ontology-driven SCL reasoning
- Stage 3: calibration and confidence routing
- Stage 4: recurring-pattern discovery and recommendations

```text
pip install -e .
pytest tests/
python scripts/generate_synthetic_data.py
python scripts/train_baselines.py
```