# Additional cultural cross-validation

## Data sources

1. **Hofstede 6D**: power distance, individualism, masculinity, uncertainty avoidance, long-term orientation, and indulgence. Country profiles were standardized before calculating root-mean-square Euclidean distance.
2. **EcoCultural Dataset — Schwartz values**: harmony, embeddedness, hierarchy, mastery, affective autonomy, intellectual autonomy, and egalitarianism.
3. **EcoCultural Dataset — Big Five**: extraversion, agreeableness, conscientiousness, neuroticism, and openness.
4. **EcoCultural Dataset — Moral foundations**: authority, fairness, harm, ingroup, and purity.
5. **EcoCultural Dataset — Fundamental motives**: eleven motive dimensions reported in the source dataset.
6. **CEPII common language**: whether at least 9% of the population in both countries speaks a common language.

The four EcoCultural domains were selected from independent psychological sources. EcoCultural fields reproducing Hofstede dimensions or a precomputed cultural-distance index were excluded.

## Results

Values below are partial correlations between external cultural distance and symmetric CI, controlling log geographic distance, contiguity, city pixel-count imbalance, and prototype-count product. Negative values support the hypothesis that culturally more distant countries have less similar city morphology.

| External criterion | K=200 | K=500 | K=1000 | Inference after Holm correction across 18 tests |
|---|---:|---:|---:|---|
| Hofstede 6D | -0.246 | -0.224 | -0.255 | Significant at all scales (adjusted P=0.018) |
| Schwartz values | -0.223 | -0.212 | -0.290 | Significant at all scales (adjusted P=0.018–0.042) |
| Big Five | -0.079 | -0.087 | -0.105 | Not significant |
| Moral foundations | 0.030 | 0.057 | 0.013 | Not significant |
| Fundamental motives | -0.193 | -0.093 | -0.171 | Not significant after multiplicity correction |
| CEPII common language | 0.078 | 0.047 | 0.040 | Not significant |

Hofstede uses 30 matched countries and 3,512 city pairs; Schwartz values use 28 countries and 2,880 city pairs. The other domain-specific analyses contain 21–46 countries and 2,026–7,948 city pairs.

## Interpretation

The positive result is reproducible with two external constructs that describe broad societal value systems: Hofstede's national-culture dimensions and Schwartz's cultural values. It is not reproduced for all cultural proxies. In particular, personality, moral foundations, and a binary common-language relation do not independently predict CI after geographic and sampling controls.

The evidence therefore supports a narrower claim: satellite-derived urban morphology contains information about macro-level societal value orientations. It does not support the stronger claim that morphology captures every aspect of culture.

Inference uses 999 country-label permutations. Holm-adjusted P values correct across all six datasets and three prototype scales. The analysis remains associational and country-level; it does not establish causal direction or within-country city culture.
