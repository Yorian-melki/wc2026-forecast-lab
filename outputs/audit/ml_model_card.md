# ML Model Card — WC2026 1X2 match model

- **Type**: multinomial logistic regression (sklearn 1.9.0)
- **Features**: pre-match rolling-Elo diff (incl. home adv), neutral flag
- **Training data**: martj42 international results 1990–2018 (25108 matches)
- **Validation**: held-out 2019–2022 (3580 matches), leak-free temporal split
- **Baseline**: Elo-only formula on the same elo_diff
- **Gate result**: ACCEPTED
- **Intended use**: single-match 1X2 probabilities; NOT a tournament simulator replacement
- **Limitations**: 2 features only; no xG/lineup/rest-day features (avoided leakage & overfit); does not model goal counts; tournament sim still uses CalibratedEloMatchModel
- **Ethical/▸honesty**: not 'xG-calibrated'; not 'validated' beyond the stated temporal split
