#!/usr/bin/env python3
"""Test the geographic-distance baseline of the symmetric Covered Index."""

from pathlib import Path
import json

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
CI_FILE = ROOT / "data" / "results" / "cultural_validation" / "city_pair_ci.csv"
CITY_FILE = ROOT / "data" / "results" / "cultural_validation" / "city_country_mapping.csv"
OUTPUT = ROOT / "data" / "results" / "geographic_baseline_validation"
N_PERMUTATIONS = 9999
RANDOM_SEED = 20260808
EARTH_RADIUS_KM = 6371.0088


def haversine_matrix(longitude, latitude):
    """Return pairwise great-circle distances in kilometres."""
    lon = np.radians(np.asarray(longitude, dtype=float))
    lat = np.radians(np.asarray(latitude, dtype=float))
    dlon = lon[:, None] - lon[None, :]
    dlat = lat[:, None] - lat[None, :]
    a = np.sin(dlat / 2.0) ** 2 + (
        np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def symmetric_ci_matrix(frame, cities):
    index = {city: position for position, city in enumerate(cities)}
    matrix = np.eye(len(cities), dtype=float)
    for row in frame.itertuples(index=False):
        i, j = index[row.city_1], index[row.city_2]
        matrix[i, j] = matrix[j, i] = row.ci_symmetric
    return matrix


def qap_statistics(ci_matrix, log_distance, upper, permutations):
    """Calculate observed statistics and one-sided negative-tail QAP P values."""
    ci_values = ci_matrix[upper]
    x_centered = log_distance - log_distance.mean()
    y_centered = ci_values - ci_values.mean()
    x_sum_squares = np.dot(x_centered, x_centered)
    slope = float(np.dot(x_centered, y_centered) / x_sum_squares)

    distance_ranks = stats.rankdata(log_distance)
    ci_ranks = stats.rankdata(ci_values)
    rank_matrix = np.zeros_like(ci_matrix)
    rank_matrix[upper] = ci_ranks
    rank_matrix[(upper[1], upper[0])] = ci_ranks
    x_rank_centered = distance_ranks - distance_ranks.mean()
    rank_denominator = np.sqrt(
        np.dot(x_rank_centered, x_rank_centered)
        * np.dot(ci_ranks - ci_ranks.mean(), ci_ranks - ci_ranks.mean())
    )
    rho = float(np.dot(x_rank_centered, ci_ranks - ci_ranks.mean()) / rank_denominator)

    slope_null = np.empty(len(permutations), dtype=float)
    rho_null = np.empty(len(permutations), dtype=float)
    for iteration, permutation in enumerate(permutations):
        permuted_ci = ci_matrix[np.ix_(permutation, permutation)][upper]
        slope_null[iteration] = np.dot(
            x_centered, permuted_ci - permuted_ci.mean()
        ) / x_sum_squares
        permuted_ranks = rank_matrix[np.ix_(permutation, permutation)][upper]
        rho_null[iteration] = np.dot(
            x_rank_centered, permuted_ranks - permuted_ranks.mean()
        ) / rank_denominator

    slope_p = float((1 + np.sum(slope_null <= slope)) / (len(permutations) + 1))
    rho_p = float((1 + np.sum(rho_null <= rho)) / (len(permutations) + 1))
    return slope, slope_p, rho, rho_p


def main():
    city_table = pd.read_csv(CITY_FILE)
    ci = pd.read_csv(CI_FILE)
    cities = city_table.city.tolist()
    if len(cities) != 130 or len(set(cities)) != 130:
        raise RuntimeError("Expected 130 unique cities")

    distance_matrix = haversine_matrix(city_table.longitude, city_table.latitude)
    upper = np.triu_indices(len(cities), 1)
    distance_km = distance_matrix[upper]
    if np.any(distance_km <= 0):
        raise RuntimeError("All off-diagonal city distances must be positive")
    log_distance = np.log(distance_km)

    rng = np.random.default_rng(RANDOM_SEED)
    permutations = [rng.permutation(len(cities)) for _ in range(N_PERMUTATIONS)]
    rows = []
    for k in (200, 500, 1000):
        frame = ci[ci.k == k]
        ci_matrix = symmetric_ci_matrix(frame, cities)
        ci_values = ci_matrix[upper]
        slope, slope_p, rho, rho_p = qap_statistics(
            ci_matrix, log_distance, upper, permutations
        )
        intercept = float(ci_values.mean() - slope * log_distance.mean())
        standardized_beta = float(
            slope * log_distance.std(ddof=0) / ci_values.std(ddof=0)
        )
        fitted = intercept + slope * log_distance
        r_squared = float(1 - np.sum((ci_values - fitted) ** 2) /
                          np.sum((ci_values - ci_values.mean()) ** 2))
        rows.append({
            "k": k,
            "n_cities": len(cities),
            "n_city_pairs": len(distance_km),
            "minimum_distance_km": float(distance_km.min()),
            "median_distance_km": float(np.median(distance_km)),
            "maximum_distance_km": float(distance_km.max()),
            "spearman_rho": rho,
            "spearman_qap_p_one_sided": rho_p,
            "ols_intercept": intercept,
            "ols_beta_log_distance": slope,
            "standardized_beta": standardized_beta,
            "r_squared": r_squared,
            "qap_beta_p_one_sided": slope_p,
            "n_permutations": N_PERMUTATIONS,
            "random_seed": RANDOM_SEED,
        })

    result = pd.DataFrame(rows)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT / "geographic_baseline_results.csv", index=False)
    metadata = {
        "distance_definition": "Great-circle distance between city raster centroids (km)",
        "model": "symmetric CI_ij ~ natural log(great-circle distance_ij)",
        "inference": "one-sided negative-tail node-label QAP permutation",
        "permutations": N_PERMUTATIONS,
        "random_seed": RANDOM_SEED,
        "diagonal_excluded": True,
    }
    (OUTPUT / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
