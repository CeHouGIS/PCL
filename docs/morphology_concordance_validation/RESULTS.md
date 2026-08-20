# Morphology-concordance validation results

Primary criterion: sliced-Wasserstein similarity between city distributions of self-contrast MoCo patch embeddings. This is the most conservative available no-new-data criterion because it precedes spatial/temporal contrast design and PCL prototype refinement.

| K | city pairs | Spearman rho | one-sided QAP P | standardized morphology beta | one-sided MRQAP P | model R2 | mean CI Q5 - Q1 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 200 | 8,385 | 0.4238 | 0.0001 | 0.1947 | 0.0001 | 0.4696 | 0.0733 |
| 500 | 8,385 | 0.4257 | 0.0001 | 0.1887 | 0.0001 | 0.4906 | 0.0713 |
| 1,000 | 8,385 | 0.4230 | 0.0001 | 0.1984 | 0.0001 | 0.4624 | 0.0681 |

MRQAP controls log geographic distance, same-country status, the absolute log MoCo sample-count ratio and the log PCL prototype-count product. Inference uses 9,999 simultaneous city-row/column label permutations.

Mean CI rises monotonically across morphology-similarity quintiles at every resolution:

| Quintile | K=200 | K=500 | K=1,000 |
|---:|---:|---:|---:|
| Q1, lowest | 0.7350 | 0.7353 | 0.7352 |
| Q2 | 0.7579 | 0.7588 | 0.7567 |
| Q3 | 0.7714 | 0.7710 | 0.7686 |
| Q4 | 0.7852 | 0.7851 | 0.7821 |
| Q5, highest | 0.8083 | 0.8067 | 0.8033 |

The result supports internal cross-representation morphological construct validity. Because both representations originate from the same imagery and a related model family, it must not be described as independent external morphology validation or causal evidence.
