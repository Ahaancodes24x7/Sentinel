# PS 26165 — Model 3: MLP Neural Network Evaluation

Trained on `report_text_preprocessed` (Stage 0 output), same train/test split (random_state=42, stratified) used for Baseline 1 and Baseline 2, so results are directly comparable.


## Model 3 — MLP Neural Network (2 hidden layers: 128 -> 64, ReLU, Adam)

Trained for 37 epochs (early-stopped: True); final training loss: 0.0588

Precision: 0.859 | Recall: 0.796 | F1: 0.826 | F2: 0.808

ROC-AUC: 0.928 | PR-AUC: 0.916 | Brier: 0.0785

Confusion matrix [[TN,FP],[FN,TP]]: [[384, 25], [39, 152]]


**4-bucket routing on test set:** {'HIGH_CONF_NON_SIF': 401, 'HIGH_CONF_SIF': 153, 'LOW_CONF_REVIEW': 46}


## Model 3b — MLP Neural Network (LSR tagging, multi-class)

Trained for 68 epochs (early-stopped: True)

```
                         precision    recall  f1-score   support

         Confined Space       1.00      1.00      1.00        12
                Driving       1.00      1.00      1.00        22
       Energy Isolation       0.86      0.93      0.89        82
               Hot Work       0.80      0.33      0.47        12
           Line of Fire       0.45      0.43      0.44        23
Safe Mechanical Lifting       0.35      0.40      0.37        20
      Working at Height       0.44      0.40      0.42        10

               accuracy                           0.75       181
              macro avg       0.70      0.64      0.66       181
           weighted avg       0.75      0.75      0.74       181

```


## Comparison to prior models (same test set, same random_state=42 split)

| Model | Precision | Recall | F1 | F2 | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|
| Baseline 1 (rule, preprocessed) | 0.836 | 0.508 | 0.632 | — | — | — |
| Baseline 2 (TF-IDF + LogReg, preprocessed) | 0.833 | 0.864 | 0.848 | 0.858 | 0.927 | 0.917 |
| **Model 3 (MLP, preprocessed)** | 0.859 | 0.796 | 0.826 | 0.808 | 0.928 | 0.916 |


**Verdict: Model 3 does NOT earn its place.** Recall changed by -0.068 and F2 by -0.050 relative to Baseline 2 — on the metric this project has committed to prioritizing (recall/F2, per the VelocityEHS PSIF precedent), the simpler linear model is equal or better. This is a real, honest result, not a disappointing one: with ~2,400 training examples and high-dimensional sparse TF-IDF input, a 128->64 MLP has far more capacity than the data supports, and linear models are well known to generalize better than deeper nonlinear ones in exactly this low-data / high-dimensional-sparse-feature regime. **Recommendation: keep Baseline 2 (TF-IDF + Logistic Regression) as the working SIF-potential classifier** until a pretrained transformer (fine-tuned on a machine with GPU/internet access) is evaluated, since transfer learning from pretrained language representations is the principled way to add capacity without needing more labeled data than this project currently has.
