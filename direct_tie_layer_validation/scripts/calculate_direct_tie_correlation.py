#!/usr/bin/env python3
"""Correlate the Direct Tie layer with symmetric Covered Index."""

from pathlib import Path
import json
import re
import unicodedata

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
HISTORICAL = ROOT / "historical_city_connection_layers_138x138.xlsx"
CI_FILE = ROOT / "cultural_validation" / "output" / "city_pair_ci.csv"
OUT = ROOT / "direct_tie_layer_validation" / "output"
SEED = 20260806
N_PERM = 9999

ALIASES = {
    "Beira": "Beria", "Brasília": "Brazilia", "City of Tshwane": "Tshwane",
    "Havana": "Habana", "Lisbon": "Lisboa", "Malacca": "Melaka",
    "Mexico City": "Mexico", "Milan": "Milano", "NCT of Delhi": "Delhi",
    "Nairobi": "Narobi", "New York City": "Newyork", "Quebec City": "Quebec",
    "Quezon City": "LungsodQuezon", "Saint Petersburg": "St.Petersburg",
    "Setúbal": "Setobal", "Seville": "Sevilla", "São Paulo": "SanPaulo",
    "The Hague": "Denhaag", "Turin": "Torino",
}


def normalize(name):
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", text)


def auc_from_scores(y, score):
    positive = score[y == 1]
    negative = score[y == 0]
    ranks = stats.rankdata(np.concatenate([positive, negative]))
    rank_sum = ranks[:len(positive)].sum()
    return float((rank_sum - len(positive)*(len(positive)+1)/2) / (len(positive)*len(negative)))


def main():
    city_list = pd.read_excel(HISTORICAL, sheet_name="City List")
    matrix = pd.read_excel(HISTORICAL, sheet_name="Direct Tie Matrix", index_col=0)
    ci = pd.read_csv(CI_FILE)
    ci_cities = sorted(set(ci.city_1) | set(ci.city_2))
    normalized_ci = {normalize(city): city for city in ci_cities}

    mapping_rows = []
    for row in city_list.itertuples(index=False):
        ci_city = ALIASES.get(row.city, normalized_ci.get(normalize(row.city)))
        mapping_rows.append({
            "historical_city": row.city,
            "ci_city": ci_city,
            "matched": ci_city is not None,
            "continent": row.continent,
            "country": row.country,
        })
    mapping = pd.DataFrame(mapping_rows)
    mapping.to_csv(OUT / "city_name_mapping.csv", index=False)
    matched = mapping[mapping.matched].copy()
    if len(matched) != 130 or matched.ci_city.nunique() != 130:
        raise RuntimeError("Expected 130 one-to-one city matches")

    historical_names = matched.historical_city.tolist()
    ci_names = matched.ci_city.tolist()
    tie_matrix = matrix.loc[historical_names, historical_names].to_numpy(dtype=np.int8)
    upper = np.triu_indices(len(matched), 1)
    direct_tie = tie_matrix[upper]
    countries = matched.country.tolist()
    cross_country = np.array([countries[i] != countries[j] for i, j in zip(*upper)])

    ci_matrices = {}
    for k in (200, 500, 1000):
        m = np.eye(len(matched), dtype=float)
        index = {name: i for i, name in enumerate(ci_names)}
        for row in ci[ci.k == k].itertuples(index=False):
            i, j = index[row.city_1], index[row.city_2]
            m[i, j] = m[j, i] = row.ci_symmetric
        ci_matrices[k] = m

    rng = np.random.default_rng(SEED)
    permutations = [rng.permutation(len(matched)) for _ in range(N_PERM)]
    rows, nulls = [], {}
    for k, ci_matrix in ci_matrices.items():
        scores = ci_matrix[upper]
        pearson = float(stats.pearsonr(direct_tie, scores).statistic)
        spearman = float(stats.spearmanr(direct_tie, scores).statistic)
        yes, no = scores[direct_tie == 1], scores[direct_tie == 0]
        difference = float(yes.mean() - no.mean())
        pooled_sd = np.sqrt(
            ((len(yes)-1)*yes.var(ddof=1) + (len(no)-1)*no.var(ddof=1)) / (len(scores)-2)
        )
        pearson_null = np.empty(N_PERM)
        spearman_null = np.empty(N_PERM)
        cross_country_null = np.empty(N_PERM)
        ranked_scores = stats.rankdata(scores)
        cross_scores = scores[cross_country]
        cross_tie = direct_tie[cross_country]
        cross_pearson = float(stats.pearsonr(cross_tie, cross_scores).statistic)
        cross_spearman = float(stats.spearmanr(cross_tie, cross_scores).statistic)
        for n, perm in enumerate(permutations):
            perm_tie = tie_matrix[np.ix_(perm, perm)][upper]
            pearson_null[n] = np.corrcoef(perm_tie, scores)[0, 1]
            spearman_null[n] = np.corrcoef(perm_tie, ranked_scores)[0, 1]
            cross_country_null[n] = np.corrcoef(perm_tie[cross_country], cross_scores)[0, 1]
        pearson_p = float((1 + np.sum(pearson_null >= pearson)) / (N_PERM + 1))
        spearman_p = float((1 + np.sum(spearman_null >= spearman)) / (N_PERM + 1))
        cross_p = float((1 + np.sum(cross_country_null >= cross_pearson)) / (N_PERM + 1))
        nulls[f"pearson_k{k}"] = pearson_null
        nulls[f"spearman_k{k}"] = spearman_null
        nulls[f"cross_country_pearson_k{k}"] = cross_country_null
        rows.append({
            "k": k,
            "n_cities": len(matched),
            "n_city_pairs": len(direct_tie),
            "n_direct_tie_pairs": int(direct_tie.sum()),
            "direct_tie_prevalence": float(direct_tie.mean()),
            "mean_ci_direct_tie": float(yes.mean()),
            "mean_ci_no_direct_tie": float(no.mean()),
            "mean_difference": difference,
            "cohen_d": float(difference / pooled_sd),
            "roc_auc": auc_from_scores(direct_tie, scores),
            "pearson_r": pearson,
            "pearson_city_permutation_p_one_sided": pearson_p,
            "spearman_rho": spearman,
            "spearman_city_permutation_p_one_sided": spearman_p,
            "cross_country_n_pairs": int(cross_country.sum()),
            "cross_country_n_direct_tie_pairs": int(cross_tie.sum()),
            "cross_country_mean_ci_direct_tie": float(cross_scores[cross_tie == 1].mean()),
            "cross_country_mean_ci_no_direct_tie": float(cross_scores[cross_tie == 0].mean()),
            "cross_country_mean_difference": float(cross_scores[cross_tie == 1].mean() - cross_scores[cross_tie == 0].mean()),
            "cross_country_pearson_r": cross_pearson,
            "cross_country_spearman_rho": cross_spearman,
            "cross_country_pearson_city_permutation_p_one_sided": cross_p,
        })

    result = pd.DataFrame(rows)
    result.to_csv(OUT / "direct_tie_correlation_results.csv", index=False)
    np.savez_compressed(OUT / "direct_tie_permutation_nulls.npz", **nulls)
    metadata = {
        "layer": "Direct Tie Matrix",
        "definition": "At least one qualifying direct city-to-city transfer record exists in either direction.",
        "historical_cities": len(city_list),
        "matched_cities": len(matched),
        "unmatched_historical_cities": mapping.loc[~mapping.matched, "historical_city"].tolist(),
        "diagonal_excluded": True,
        "ci_definition": "mean of CI(A->B) and CI(B->A)",
        "permutations": N_PERM,
        "random_seed": SEED,
    }
    (OUT / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(result.to_string(index=False))
    print("\nUnmatched:", ", ".join(metadata["unmatched_historical_cities"]))


if __name__ == "__main__":
    main()
