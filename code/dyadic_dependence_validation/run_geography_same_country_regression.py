#!/usr/bin/env python3
"""Fit the reduced CI model with geography and same-country status only."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
CI_FILE = ROOT / "data" / "results" / "cultural_validation" / "city_pair_ci.csv"
CITY_FILE = ROOT / "data" / "results" / "cultural_validation" / "city_country_mapping.csv"
OUTPUT = ROOT / "data" / "results" / "dyadic_dependence_validation"
DOC_OUTPUT = ROOT / "docs" / "dyadic_dependence_validation"
K = 1000
N_PERMUTATIONS = 9999
RANDOM_SEED = 20260814
EARTH_RADIUS_KM = 6371.0088


def zscore(values):
    values = np.asarray(values, dtype=float)
    return (values - values.mean()) / values.std(ddof=0)


def haversine_matrix(longitude, latitude):
    lon = np.radians(np.asarray(longitude, dtype=float))
    lat = np.radians(np.asarray(latitude, dtype=float))
    dlon = lon[:, None] - lon[None, :]
    dlat = lat[:, None] - lat[None, :]
    a = np.sin(dlat / 2.0) ** 2 + (
        np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def symmetric_ci_matrix(frame, cities):
    city_index = {city: index for index, city in enumerate(cities)}
    matrix = np.full((len(cities), len(cities)), np.nan, dtype=float)
    np.fill_diagonal(matrix, 1.0)
    for row in frame.itertuples(index=False):
        i = city_index[row.city_1]
        j = city_index[row.city_2]
        matrix[i, j] = matrix[j, i] = float(row.ci_symmetric)
    if np.isnan(matrix).any():
        raise RuntimeError("The CI matrix is incomplete")
    return matrix


def pair_matrix(values, upper, size):
    matrix = np.zeros((size, size), dtype=float)
    matrix[upper] = values
    matrix[(upper[1], upper[0])] = values
    return matrix


def permutation_p_value(y, focal, nuisance, upper, permutations, direction):
    """Partial-regression test with simultaneous row/column permutations."""
    nuisance_inverse = np.linalg.pinv(nuisance)
    residual_y = y - nuisance @ (nuisance_inverse @ y)
    residual_focal = focal - nuisance @ (nuisance_inverse @ focal)
    denominator = float(residual_focal @ residual_focal)
    observed = float((residual_y @ residual_focal) / denominator)
    residual_matrix = pair_matrix(residual_focal, upper, len(np.unique(upper)))

    extreme = 0
    for permutation in permutations:
        permuted_focal = residual_matrix[np.ix_(permutation, permutation)][upper]
        coefficient = float((residual_y @ permuted_focal) / denominator)
        if direction == "negative":
            extreme += coefficient <= observed
        else:
            extreme += coefficient >= observed
    return observed, float((extreme + 1) / (len(permutations) + 1))


def main():
    cities = pd.read_csv(CITY_FILE)
    ci = pd.read_csv(CI_FILE)
    if len(cities) != 130 or cities.city.nunique() != 130:
        raise RuntimeError("Expected 130 unique cities")

    city_names = cities.city.tolist()
    upper = np.triu_indices(len(city_names), 1)
    distance_matrix = haversine_matrix(cities.longitude, cities.latitude)
    log_distance = np.log(distance_matrix[upper])
    country = cities.iso3.fillna(cities.country).astype(str).to_numpy()
    same_country_matrix = (country[:, None] == country[None, :]).astype(float)
    np.fill_diagonal(same_country_matrix, 0.0)
    same_country = same_country_matrix[upper]
    ci_matrix = symmetric_ci_matrix(ci[ci.k == K], city_names)
    ci_values = ci_matrix[upper]

    raw_predictors = {
        "log_geographic_distance": log_distance,
        "same_country": same_country,
    }
    standardized_predictors = {
        name: zscore(values) for name, values in raw_predictors.items()
    }
    predictor_names = list(raw_predictors)
    y = zscore(ci_values)
    standardized_design = np.column_stack(
        [np.ones(len(y)), *[standardized_predictors[name] for name in predictor_names]]
    )
    raw_design = np.column_stack(
        [np.ones(len(y)), *[raw_predictors[name] for name in predictor_names]]
    )
    beta = np.linalg.lstsq(standardized_design, y, rcond=None)[0]
    raw_beta = np.linalg.lstsq(raw_design, ci_values, rcond=None)[0]
    fitted = standardized_design @ beta
    residual = y - fitted
    r_squared = float(1.0 - (residual @ residual) / (y @ y))
    adjusted_r_squared = float(
        1.0 - (1.0 - r_squared) * (len(y) - 1) / (len(y) - len(beta))
    )

    rng = np.random.default_rng(RANDOM_SEED)
    permutations = np.asarray(
        [rng.permutation(len(city_names)) for _ in range(N_PERMUTATIONS)],
        dtype=np.int16,
    )
    directions = {
        "log_geographic_distance": "negative",
        "same_country": "positive",
    }
    rows = []
    for index, name in enumerate(predictor_names, start=1):
        nuisance_names = [item for item in predictor_names if item != name]
        nuisance = np.column_stack(
            [np.ones(len(y)), *[standardized_predictors[item] for item in nuisance_names]]
        )
        partial_beta, p_value = permutation_p_value(
            y, standardized_predictors[name], nuisance, upper,
            permutations, directions[name],
        )
        if not np.isclose(partial_beta, beta[index], atol=1e-10):
            raise RuntimeError(f"Partial-regression coefficient mismatch for {name}")
        rows.append({
            "k": K,
            "predictor": name,
            "standardized_beta": float(beta[index]),
            "unstandardized_coefficient": float(raw_beta[index]),
            "permutation_p_one_sided": p_value,
            "expected_direction": directions[name],
            "model_r_squared": r_squared,
            "adjusted_r_squared": adjusted_r_squared,
            "n_cities": len(city_names),
            "n_city_pairs": len(y),
            "n_permutations": N_PERMUTATIONS,
            "method": "multiple regression with simultaneous row-column city-label permutation inference",
        })

    result = pd.DataFrame(rows)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    DOC_OUTPUT.mkdir(parents=True, exist_ok=True)
    result.to_csv(
        OUTPUT / "geography_same_country_regression_k1000.csv", index=False
    )

    def p_text(value):
        return "$<0.001$" if value < 0.001 else f"${value:.3f}$"

    indexed = result.set_index("predictor")
    geo = indexed.loc["log_geographic_distance"]
    national = indexed.loc["same_country"]
    table = rf"""\begin{{table}}[!htbp]
\centering
\caption{{\textbf{{Covered Index regression on geographic and national dependence.}} Standardized coefficients are reported. Statistical significance was evaluated using 9,999 simultaneous row--column city-label permutations.}}
\label{{tab:ci-geography-country-regression}}
\begin{{tabular}}{{lrr}}
\toprule
Predictor & Standardized $\beta$ & $P$ \\
\midrule
$\log(\mathrm{{Geographic\ distance}})$ & {geo.standardized_beta:.3f} & {p_text(geo.permutation_p_one_sided)} \\
Same country & {national.standardized_beta:.3f} & {p_text(national.permutation_p_one_sided)} \\
\midrule
$R^2$ & \multicolumn{{2}}{{r}}{{{r_squared:.3f}}} \\
Adjusted $R^2$ & \multicolumn{{2}}{{r}}{{{adjusted_r_squared:.3f}}} \\
City pairs & \multicolumn{{2}}{{r}}{{8,385}} \\
\bottomrule
\end{{tabular}}
\end{{table}}
"""
    (DOC_OUTPUT / "geography_same_country_regression_k1000.tex").write_text(
        table, encoding="utf-8"
    )
    metadata = {
        "model": "CI ~ log(geographic distance) + same-country status",
        "historical_connection_included": False,
        "ci": "symmetric Covered Index",
        "prototype_resolution": K,
        "n_cities": len(city_names),
        "n_city_pairs": len(y),
        "permutation": "simultaneous row-column city-label permutation",
        "tests": "one-sided in preregistered directions",
        "n_permutations": N_PERMUTATIONS,
        "random_seed": RANDOM_SEED,
        "r_squared": r_squared,
        "adjusted_r_squared": adjusted_r_squared,
    }
    (OUTPUT / "geography_same_country_regression_k1000.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
