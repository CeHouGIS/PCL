#!/usr/bin/env python3
"""Validate PCL-CI against city distributions from pre-prototype MoCo features."""

from pathlib import Path
import json

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
CI_FILE = ROOT / "data" / "results" / "cultural_validation" / "city_pair_ci.csv"
CITY_FILE = ROOT / "data" / "results" / "cultural_validation" / "city_country_mapping.csv"
FEATURE_ROOT = ROOT / "data" / "features" / "Moco"
OUTPUT = ROOT / "data" / "results" / "morphology_concordance_validation"

STRATEGIES = {
    "self": "feature_self",
    "temporal": "feature_temporal",
    "spatial": "feature_spatial",
    "spatiotemporal": "feature_spatial_temporal",
}
PRIMARY_STRATEGY = "self"
N_PROJECTIONS = 128
N_QUANTILES = 99
N_PERMUTATIONS = 9999
RANDOM_SEED = 20260814
EARTH_RADIUS_KM = 6371.0088


def zscore(values):
    values = np.asarray(values, dtype=float)
    standard_deviation = values.std(ddof=0)
    if standard_deviation == 0:
        raise ValueError("Cannot standardize a constant variable")
    return (values - values.mean()) / standard_deviation


def haversine_matrix(longitude, latitude):
    lon = np.radians(np.asarray(longitude, dtype=float))
    lat = np.radians(np.asarray(latitude, dtype=float))
    dlon = lon[:, None] - lon[None, :]
    dlat = lat[:, None] - lat[None, :]
    a = np.sin(dlat / 2.0) ** 2 + (
        np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def symmetric_matrix(frame, value_column, cities, diagonal=0.0):
    city_index = {city: index for index, city in enumerate(cities)}
    matrix = np.full((len(cities), len(cities)), np.nan, dtype=float)
    np.fill_diagonal(matrix, diagonal)
    for row in frame.itertuples(index=False):
        i = city_index[row.city_1]
        j = city_index[row.city_2]
        value = getattr(row, value_column)
        matrix[i, j] = matrix[j, i] = value
    if np.isnan(matrix).any():
        raise ValueError(f"Incomplete pair matrix for {value_column}")
    return matrix


def city_distribution_signatures(cities, feature_directory, projections, quantiles):
    """Represent each city by projected empirical quantile functions."""
    signatures = []
    sample_counts = []
    for city in cities:
        feature_path = feature_directory / f"{city}.npy"
        if not feature_path.exists():
            raise FileNotFoundError(feature_path)
        features = np.load(feature_path).astype(np.float32)
        if features.ndim != 2 or features.shape[1] != projections.shape[0]:
            raise ValueError(f"Unexpected feature shape for {city}: {features.shape}")
        features /= np.maximum(np.linalg.norm(features, axis=1, keepdims=True), 1e-12)
        projected = features @ projections
        signature = np.quantile(projected, quantiles, axis=0).T.astype(np.float32)
        signatures.append(signature)
        sample_counts.append(len(features))
    return signatures, np.asarray(sample_counts, dtype=int)


def sliced_wasserstein_pairs(signatures, upper):
    """Approximate W1 by mean quantile difference across random projections."""
    distances = np.asarray(
        [
            np.mean(np.abs(signatures[i] - signatures[j]))
            for i, j in zip(*upper)
        ],
        dtype=float,
    )
    scale = float(np.median(distances))
    if scale <= 0:
        raise ValueError("Sliced-Wasserstein median scale must be positive")
    similarities = np.exp(-distances / scale)
    return distances, similarities, scale


def pair_matrix(values, upper, size, diagonal=0.0):
    matrix = np.full((size, size), diagonal, dtype=float)
    matrix[upper] = values
    matrix[(upper[1], upper[0])] = values
    return matrix


def qap_mrqap(ci_values, similarity_values, similarity_matrix, controls,
              upper, permutations, batch_size=128):
    """Spearman QAP and focal-predictor node-label permutation MRQAP."""
    y_rank = stats.rankdata(ci_values)
    x_rank = stats.rankdata(similarity_values)
    y_rank_centered = y_rank - y_rank.mean()
    x_rank_centered = x_rank - x_rank.mean()
    rank_denominator = np.sqrt(
        np.dot(y_rank_centered, y_rank_centered)
        * np.dot(x_rank_centered, x_rank_centered)
    )
    observed_rho = float(np.dot(y_rank_centered, x_rank_centered) / rank_denominator)
    rank_matrix = pair_matrix(x_rank, upper, similarity_matrix.shape[0])

    y = zscore(ci_values)
    x = zscore(similarity_values)
    control_design = np.column_stack(
        [np.ones(len(y))] + [zscore(values) for values in controls.values()]
    )
    control_inverse = np.linalg.pinv(control_design)
    residual_y = y - control_design @ (control_inverse @ y)
    residual_x = x - control_design @ (control_inverse @ x)
    observed_beta = float(
        np.dot(residual_x, residual_y) / np.dot(residual_x, residual_x)
    )

    full_design = np.column_stack(
        [np.ones(len(y)), x]
        + [zscore(values) for values in controls.values()]
    )
    coefficients = np.linalg.lstsq(full_design, y, rcond=None)[0]
    fitted = full_design @ coefficients
    r_squared = float(1 - np.sum((y - fitted) ** 2) / np.sum(y ** 2))

    standardized_matrix = pair_matrix(x, upper, similarity_matrix.shape[0])
    rho_null = np.empty(len(permutations), dtype=float)
    beta_null = np.empty(len(permutations), dtype=float)
    for start in range(0, len(permutations), batch_size):
        stop = min(start + batch_size, len(permutations))
        batch = permutations[start:stop]
        rank_batch = np.column_stack(
            [rank_matrix[np.ix_(permutation, permutation)][upper] for permutation in batch]
        )
        rho_null[start:stop] = y_rank_centered @ (
            rank_batch - x_rank.mean()
        ) / rank_denominator

        x_batch = np.column_stack(
            [
                standardized_matrix[np.ix_(permutation, permutation)][upper]
                for permutation in batch
            ]
        )
        residual_batch = x_batch - control_design @ (control_inverse @ x_batch)
        beta_null[start:stop] = (
            residual_y @ residual_batch
        ) / np.sum(residual_batch ** 2, axis=0)

    rho_p = float(
        (1 + np.sum(rho_null >= observed_rho)) / (len(permutations) + 1)
    )
    beta_p = float(
        (1 + np.sum(beta_null >= observed_beta)) / (len(permutations) + 1)
    )
    return observed_rho, rho_p, observed_beta, beta_p, r_squared


def main():
    city_table = pd.read_csv(CITY_FILE)
    ci = pd.read_csv(CI_FILE)
    cities = city_table.city.tolist()
    if len(cities) != 130 or len(set(cities)) != 130:
        raise RuntimeError("Expected 130 unique cities")

    upper = np.triu_indices(len(cities), 1)
    pair_table = pd.DataFrame({
        "city_1": np.asarray(cities)[upper[0]],
        "city_2": np.asarray(cities)[upper[1]],
    })

    rng = np.random.default_rng(RANDOM_SEED)
    projections = rng.normal(size=(128, N_PROJECTIONS)).astype(np.float32)
    projections /= np.linalg.norm(projections, axis=0, keepdims=True)
    quantiles = np.linspace(0.01, 0.99, N_QUANTILES)

    similarity_matrices = {}
    sample_counts = None
    scales = {}
    for strategy, directory_name in STRATEGIES.items():
        signatures, counts = city_distribution_signatures(
            cities, FEATURE_ROOT / directory_name, projections, quantiles
        )
        if sample_counts is None:
            sample_counts = counts
        elif not np.array_equal(sample_counts, counts):
            raise ValueError("MoCo strategies have inconsistent city sample counts")
        distance, similarity, scale = sliced_wasserstein_pairs(signatures, upper)
        pair_table[f"{strategy}_distance"] = distance
        pair_table[f"{strategy}_similarity"] = similarity
        similarity_matrices[strategy] = pair_matrix(
            similarity, upper, len(cities), diagonal=1.0
        )
        scales[strategy] = scale

    distance_matrix = haversine_matrix(city_table.longitude, city_table.latitude)
    log_distance = np.log(distance_matrix[upper])
    same_country = (
        city_table.iso3.to_numpy()[upper[0]] == city_table.iso3.to_numpy()[upper[1]]
    ).astype(float)
    log_sample_ratio = np.abs(
        np.log(sample_counts[upper[0]] / sample_counts[upper[1]])
    )
    pair_table["distance_km"] = distance_matrix[upper]
    pair_table["same_country"] = same_country.astype(int)
    pair_table["moco_sample_count_1"] = sample_counts[upper[0]]
    pair_table["moco_sample_count_2"] = sample_counts[upper[1]]

    permutations = np.asarray(
        [rng.permutation(len(cities)) for _ in range(N_PERMUTATIONS)],
        dtype=np.int16,
    )
    result_rows = []
    quintile_rows = []
    primary_quintile = pd.qcut(
        pair_table[f"{PRIMARY_STRATEGY}_similarity"].rank(method="first"),
        5,
        labels=[1, 2, 3, 4, 5],
    ).astype(int).to_numpy()
    pair_table["primary_similarity_quintile"] = primary_quintile

    for k in (200, 500, 1000):
        frame = ci[ci.k == k]
        ci_matrix = symmetric_matrix(frame, "ci_symmetric", cities, diagonal=1.0)
        ci_values = ci_matrix[upper]
        prototype_product = symmetric_matrix(
            frame.assign(
                prototype_product=frame.n_prototypes_1 * frame.n_prototypes_2
            ),
            "prototype_product",
            cities,
            diagonal=1.0,
        )[upper]
        controls = {
            "log_geographic_distance": log_distance,
            "same_country": same_country,
            "log_moco_sample_ratio": log_sample_ratio,
            "log_prototype_product": np.log(prototype_product),
        }

        for strategy in STRATEGIES:
            similarities = pair_table[f"{strategy}_similarity"].to_numpy()
            rho, rho_p, beta, beta_p, r_squared = qap_mrqap(
                ci_values,
                similarities,
                similarity_matrices[strategy],
                controls,
                upper,
                permutations,
            )
            result_rows.append({
                "k": k,
                "strategy": strategy,
                "primary_strategy": strategy == PRIMARY_STRATEGY,
                "n_cities": len(cities),
                "n_city_pairs": len(ci_values),
                "spearman_rho": rho,
                "spearman_qap_p_one_sided": rho_p,
                "standardized_morphology_beta": beta,
                "mrqap_p_one_sided": beta_p,
                "mrqap_r_squared": r_squared,
                "n_permutations": N_PERMUTATIONS,
            })

        for quintile in range(1, 6):
            values = ci_values[primary_quintile == quintile]
            quintile_rows.append({
                "k": k,
                "quintile": quintile,
                "n_city_pairs": len(values),
                "mean_ci": float(values.mean()),
                "median_ci": float(np.median(values)),
                "ci_q05": float(np.quantile(values, 0.05)),
                "ci_q25": float(np.quantile(values, 0.25)),
                "ci_q75": float(np.quantile(values, 0.75)),
                "ci_q95": float(np.quantile(values, 0.95)),
            })

    results = pd.DataFrame(result_rows)
    quintiles = pd.DataFrame(quintile_rows)
    q1 = quintiles[quintiles.quintile == 1].set_index("k").mean_ci
    q5 = quintiles[quintiles.quintile == 5].set_index("k").mean_ci
    results["mean_ci_q5_minus_q1"] = results.k.map(q5 - q1)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pair_table.to_csv(OUTPUT / "moco_morphology_similarity_pairs.csv", index=False)
    results.to_csv(OUTPUT / "morphology_concordance_results.csv", index=False)
    quintiles.to_csv(OUTPUT / "morphology_similarity_quintiles.csv", index=False)
    metadata = {
        "validation_type": "internal cross-representation morphological construct validation",
        "primary_strategy": PRIMARY_STRATEGY,
        "primary_strategy_rationale": (
            "Self-contrast MoCo excludes spatial/temporal positive-pair design and "
            "PCL prototype refinement."
        ),
        "city_distribution": (
            f"{N_PROJECTIONS} random projections x {N_QUANTILES} empirical quantiles"
        ),
        "distance": "approximated sliced-Wasserstein-1 distance",
        "similarity": "exp(-distance / global median pair distance)",
        "ci": "symmetric mean of CI(A->B) and CI(B->A)",
        "mrqap_controls": [
            "log geographic distance",
            "same-country indicator",
            "absolute log MoCo sample-count ratio",
            "log PCL prototype-count product",
        ],
        "permutation": "one-sided simultaneous city-row/column label permutation",
        "n_permutations": N_PERMUTATIONS,
        "random_seed": RANDOM_SEED,
        "limitation": (
            "MoCo and PCL use the same imagery and related model family; this is not "
            "an independent external morphometric validation."
        ),
        "sliced_wasserstein_median_scales": scales,
    }
    (OUTPUT / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
