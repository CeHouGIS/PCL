# Internal morphology-concordance validation

This experiment tests whether the final PCL Covered Index (CI) agrees with city morphology distributions derived from the already available pre-prototype MoCo representations. It introduces no external dataset.

## Definition

For each city, patch embeddings are L2-normalized and projected onto 128 deterministic random directions. The empirical distribution on every direction is represented by 99 quantiles. For cities $i$ and $j$, the approximated sliced-Wasserstein distance is

$$
D^{\mathrm{SW}}_{ij}
=
\frac{1}{128}
\sum_{r=1}^{128}
\frac{1}{99}
\sum_{q=1}^{99}
\left|Q_{ir}(q)-Q_{jr}(q)\right|,
$$

and is converted to similarity as

$$
S^{\mathrm{morph}}_{ij}
=
\exp\left(-D^{\mathrm{SW}}_{ij}/\operatorname{median}(D^{\mathrm{SW}})\right).
$$

The primary criterion uses self-contrast MoCo because it excludes the spatial/temporal positive-pair design and PCL prototype refinement used by the final model. Temporal, spatial and spatiotemporal MoCo representations are retained as robustness analyses.

## Inference

The symmetric CI is correlated with $S^{\mathrm{morph}}$ using Spearman correlation and 9,999 simultaneous city-row/column QAP permutations. MRQAP estimates the standardized morphology-similarity coefficient while controlling for log geographic distance, same-country status, the absolute log MoCo sample-count ratio and the log PCL prototype-count product. The focal morphology matrix is permuted at the city-label level for inference.

The visualization divides the primary morphology similarity into global city-pair quintiles and compares CI across the same five groups for $K=200$, 500 and 1,000.

## Results

The conservative self-contrast criterion is positively associated with CI at every prototype resolution:

| $K$ | Spearman $r_s$ | QAP $P$ | standardized morphology coefficient | MRQAP $P$ | mean CI difference, Q5 $-$ Q1 |
|---:|---:|---:|---:|---:|---:|
| 200 | 0.424 | 0.0001 | 0.195 | 0.0001 | 0.073 |
| 500 | 0.426 | 0.0001 | 0.189 | 0.0001 | 0.071 |
| 1,000 | 0.423 | 0.0001 | 0.198 | 0.0001 | 0.068 |

The temporal ($r_s=0.592$--$0.604$), spatial ($r_s=0.513$--$0.521$) and spatiotemporal ($r_s=0.678$--$0.699$) representations show the same positive concordance, with one-sided QAP and MRQAP $P=0.0001$ throughout. These strategies are robustness checks rather than the primary criterion because their training design overlaps more closely with the final PCL representation.

## Run

```bash
python3 code/morphology_concordance_validation/calculate_morphology_concordance.py
python3 code/morphology_concordance_validation/plot_morphology_concordance.py
```

## Interpretation boundary

This is an internal, cross-representation construct-validation experiment. MoCo and PCL use the same satellite imagery and related model family, so the result demonstrates cross-objective representation concordance and robustness rather than fully independent external morphometric validity. Raw SemAxis indicators or independent vector morphology data would still be required for the stronger external test.
