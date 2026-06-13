# P2.5 Ablation Study

Additive decomposition of model components across 4 temporal splits.
Rule: Δ < 0.01 NLL on large splits treated as noise, not victory.

## NLL per split (lower = better)

| Model | train_pre2015_test_2015_2018 | train_pre2019_test_2019_2022 | wc2022_holdout | train_pre2023_test_2023_2025 | Avg |
|:------|:---: | :---: | :---: | :---: | :---: |
| Random (1/3, 1/3, 1/3) | 1.09861 | 1.09861 | 1.09861 | 1.09861 | **1.09861** |
| Empirical frequency | 1.05391 | 1.04572 | 1.07361 | 1.05479 | **1.05701** |
| Elo only (no home adv) | 0.95942 | 0.92475 | 1.02685 | 0.91284 | **0.95596** |
| Elo + home advantage | 0.93575 | 0.90141 | 1.03798 | 0.89994 | **0.94377** |
| Elo + calibrated draw | 0.92391 | 0.88600 | 1.02753 | 0.88717 | **0.93115** |
| Independent Poisson (global) | 0.92250 | 0.87779 | 1.04297 | 0.88288 | **0.93154** |
| Elo + DC rho only (no residuals) | 0.92149 | 0.87677 | 1.04516 | 0.88173 | **0.93129** |
| Hybrid, rho=0 (residuals, no DC) | 0.92773 | 0.87690 | 1.03079 | 0.88557 | **0.93025** |
| Full Hybrid (residuals + DC rho) | 0.92756 | 0.87449 | 1.03251 | 0.88174 | **0.92907** |

## Brier score per split (lower = better)

| Model | train_pre2015_test_2015_2018 | train_pre2019_test_2019_2022 | wc2022_holdout | train_pre2023_test_2023_2025 | Avg |
|:------|:---: | :---: | :---: | :---: | :---: |
| Random (1/3, 1/3, 1/3) | 0.66667 | 0.66667 | 0.66667 | 0.66667 | **0.66667** |
| Empirical frequency | 0.63572 | 0.63000 | 0.65052 | 0.63669 | **0.63823** |
| Elo only (no home adv) | 0.56779 | 0.54374 | 0.60247 | 0.53725 | **0.56281** |
| Elo + home advantage | 0.55177 | 0.52788 | 0.61093 | 0.52918 | **0.55494** |
| Elo + calibrated draw | 0.54441 | 0.51837 | 0.60905 | 0.52080 | **0.54816** |
| Independent Poisson (global) | 0.54430 | 0.51497 | 0.61008 | 0.52075 | **0.54753** |
| Elo + DC rho only (no residuals) | 0.54363 | 0.51447 | 0.60998 | 0.52008 | **0.54704** |
| Hybrid, rho=0 (residuals, no DC) | 0.54386 | 0.51327 | 0.60556 | 0.51871 | **0.54535** |
| Full Hybrid (residuals + DC rho) | 0.54308 | 0.51225 | 0.60625 | 0.51727 | **0.54471** |

## Incremental contribution of each component

Average NLL gain from adding each layer to the previous:

| Layer change | Avg ΔNLL | Direction |
|:-------------|:--------:|:---------:|
| A→D: +home advantage | -0.15484 | ✓ improves |
| D→E: +calibrated draw | -0.01262 | ✓ improves |
| E→F: Poisson vs logistic (global) | +0.00038 | ~ noise |
| F→G: +DC rho (no residuals) | -0.00025 | ~ noise |
| E→H: +per-team residuals (no DC) | -0.00091 | ~ noise |
| H→I: +DC rho correction | -0.00117 | ✓ improves |
| E→I: full hybrid vs Elo-calib | -0.00208 | ✓ improves |

## Production candidates

Model is marked PRODUCTION_CANDIDATE if it beats E (elo_calib) on avg NLL.

| Model | Avg NLL | vs elo_calib | Status |
|:------|:-------:|:------------:|:------:|
| Random (1/3, 1/3, 1/3) | 1.09861 | +0.16746 | REJECTED |
| Empirical frequency | 1.05701 | +0.12585 | REJECTED |
| Elo only (no home adv) | 0.95596 | +0.02481 | REJECTED |
| Elo + home advantage | 0.94377 | +0.01262 | REJECTED |
| Elo + calibrated draw | 0.93115 | +0.00000 | REFERENCE |
| Independent Poisson (global) | 0.93154 | +0.00038 | EXPERIMENTAL |
| Elo + DC rho only (no residuals) | 0.93129 | +0.00013 | EXPERIMENTAL |
| Hybrid, rho=0 (residuals, no DC) | 0.93025 | -0.00091 | EXPERIMENTAL |
| Full Hybrid (residuals + DC rho) | 0.92907 | -0.00208 | EXPERIMENTAL |
