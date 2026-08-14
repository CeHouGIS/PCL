# Dyadic-dependence diagnostics and city-label permutation regression

This analysis does not attempt to show that city-pair observations are i.i.d. Instead, it diagnoses dependence induced by geography, national context, and repeated city membership, and then uses node-label permutation inference for the historical-association models.

## Inputs

- `cultural_validation/output/city_pair_ci.csv`: directed and symmetric Covered Index (CI) for `K = 200, 500, 1000`.
- `cultural_validation/output/city_country_mapping.csv`: city coordinates used to calculate great-circle distance.
- `historical_city_connection_layers_138x138.xlsx`: historical direct-tie and shared-regime matrices, and the country definition in `City List`.

All 130 cities were matched one-to-one, giving 8,385 undirected city pairs and 16,770 directed city pairs after excluding self-pairs. Symmetric CI is the mean of `CI(i -> j)` and `CI(j -> i)`; directed CI is retained for the source/target-city fixed-effects analysis.

## Analyses

1. **Geographic dependence.** Spearman's correlation between symmetric CI and great-circle distance. Because Spearman correlation is invariant under a monotonic log transformation, the statistic is identical for distance and log distance. Its one-sided significance is evaluated by simultaneously permuting the row and column labels of the distance matrix 9,999 times.
2. **Same-country dependence.** The difference in mean symmetric CI between same-country and cross-country pairs, with one-sided city-label permutation inference. Country membership follows the historical workbook so that the national-context and historical-link layers use the same definition.
3. **Shared-city dependence.** Directed CI is regressed on source-city effects, target-city effects, and both sets of city effects. The resulting `R^2` measures how much pairwise CI variation is systematically attributable to repeated city identity.
4. **Controlled historical association.** Separate multiple linear regressions test direct ties and shared regimes after controlling for log geographic distance and same-country status. The reported coefficients are standardized. Significance is assessed by simultaneously permuting the row and column city labels of each residualized focal-predictor matrix, thereby retaining the dependence among pairs that share a city.

All permutation tests use 9,999 permutations and seed `20260814`. Directional, one-sided tests are used because all hypotheses were specified in advance: CI should decrease with distance and increase for same-country or historically connected pairs.

## Reproduce

```bash
python3 dyadic_dependence_validation/scripts/run_dyadic_dependence_validation.py
python3 dyadic_dependence_validation/scripts/plot_dyadic_dependence_validation.py
```

The scripts generate aggregate CSV results, a manuscript-ready LaTeX regression table (`permutation_regression_table_k1000.tex`), and the K=1,000 four-panel figure in `output/`. The pair-level audit table and TIFF are generated locally but intentionally excluded from Git.

## Main K=1,000 findings

- Geographic distance was negatively associated with CI (`r_s = -0.1793`, city-label permutation `P = 0.0001`).
- Same-country pairs had a mean CI 0.1031 higher than cross-country pairs (0.8700 versus 0.7669; city-label permutation `P = 0.0001`).
- Source- and target-city fixed effects jointly explained 46.36% of directed CI variation (`adjusted R^2 = 45.53%`).
- After controlling for log distance and same-country status, shared regime remained positively associated with CI (`beta = 0.0691`, permutation `P = 0.0122`). Direct tie remained positive but was not statistically significant (`beta = 0.0339`, permutation `P = 0.1730`).

Thus, strict i.i.d. inference is inappropriate for these dyadic observations. The shared-regime result remains robust to the two explicit controls, whereas the direct-tie result should not be described as independently significant after adjustment.
