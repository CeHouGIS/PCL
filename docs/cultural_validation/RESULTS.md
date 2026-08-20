# Cultural similarity validation results

Main external criterion: PSW2024 dyadic cultural distance computed from WVS/EVS responses (2021 wave).
Same-country city pairs are excluded because the external data are country-level.
Negative correlations mean that culturally more distant countries have lower city-morphology similarity.

Cities mapped: 130; country mapping methods: {'contains': 126, 'nearest': 4}.

| K | matched cross-country city pairs | countries | Spearman r | r for >5000 km | partial r | country-permutation p | incremental R2 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 200 | 4693 | 34 | -0.4058 | -0.2980 | -0.3552 | 0.0010 | 0.08107 |
| 500 | 4693 | 34 | -0.3996 | -0.3039 | -0.3292 | 0.0010 | 0.06573 |
| 1000 | 4693 | 34 | -0.4433 | -0.3671 | -0.3883 | 0.0010 | 0.09666 |

Partial correlations control log geographic distance, contiguity, city pixel-count ratio, and prototype-count product.
The permutation test shuffles cultural identities at country level and is the primary inference; naive pair-level p-values are retained only for diagnostics.
The analysis establishes association/predictive validity, not a causal direction from culture to morphology.
