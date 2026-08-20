#!/usr/bin/env python3
"""Diagnose dyadic dependence and run city-label permutation regressions."""

from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
CI_FILE = ROOT / "data" / "results" / "cultural_validation" / "city_pair_ci.csv"
CITY_FILE = ROOT / "data" / "results" / "cultural_validation" / "city_country_mapping.csv"
HISTORICAL_FILE = ROOT / "data" / "raw" / "historical_city_connection_layers_138x138.xlsx"
OUTPUT = ROOT / "data" / "results" / "dyadic_dependence_validation"
DOC_OUTPUT = ROOT / "docs" / "dyadic_dependence_validation"
K_VALUES = (200, 500, 1000)
N_PERMUTATIONS = 9999
RANDOM_SEED = 20260814
EARTH_RADIUS_KM = 6371.0088

sys.path.insert(0, str(ROOT / "code" / "direct_tie_layer_validation"))
from calculate_direct_tie_correlation import ALIASES, normalize  # noqa: E402


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


def historical_city_mapping(cities):
    city_list = pd.read_excel(HISTORICAL_FILE, sheet_name="City List")
    normalized_cities = {normalize(city): city for city in cities}
    matched = []
    for row in city_list.itertuples(index=False):
        ci_city = ALIASES.get(row.city, normalized_cities.get(normalize(row.city)))
        if ci_city is not None:
            matched.append((row.city, ci_city, row.country))
    if len(matched) != len(cities):
        raise RuntimeError(f"Expected {len(cities)} matched historical cities")
    if len({ci_city for _, ci_city, _ in matched}) != len(cities):
        raise RuntimeError("Historical-to-CI city matching is not one-to-one")
    return matched


def historical_matrix(sheet_name, cities, matched):
    historical = pd.read_excel(HISTORICAL_FILE, sheet_name=sheet_name, index_col=0)

    historical_names = [historical_name for historical_name, _, _ in matched]
    historical = historical.loc[historical_names, historical_names]
    historical_to_ci = {
        historical_name: ci_city for historical_name, ci_city, _ in matched
    }
    city_index = {city: index for index, city in enumerate(cities)}
    matrix = np.zeros((len(cities), len(cities)), dtype=float)
    for position, city_a in enumerate(historical_names):
        for city_b in historical_names[position + 1:]:
            i = city_index[historical_to_ci[city_a]]
            j = city_index[historical_to_ci[city_b]]
            matrix[i, j] = matrix[j, i] = int(historical.loc[city_a, city_b])
    return matrix


def ci_matrices(frame, cities):
    city_index = {city: index for index, city in enumerate(cities)}
    directed = np.full((len(cities), len(cities)), np.nan, dtype=float)
    symmetric = np.full_like(directed, np.nan)
    np.fill_diagonal(directed, 1.0)
    np.fill_diagonal(symmetric, 1.0)
    for row in frame.itertuples(index=False):
        i = city_index[row.city_1]
        j = city_index[row.city_2]
        directed[i, j] = row.ci_1_to_2
        directed[j, i] = row.ci_2_to_1
        symmetric[i, j] = symmetric[j, i] = row.ci_symmetric
    if np.isnan(directed).any() or np.isnan(symmetric).any():
        raise ValueError("Incomplete CI matrix")
    return directed, symmetric


def pair_matrix(values, upper, size, diagonal=0.0):
    matrix = np.full((size, size), diagonal, dtype=float)
    matrix[upper] = values
    matrix[(upper[1], upper[0])] = values
    return matrix


def dependence_diagnostics(ci_by_k, distance_matrix, same_country_matrix,
                           upper, permutations, batch_size=128):
    distance_values = distance_matrix[upper]
    log_distance = np.log(distance_values)
    distance_ranks = stats.rankdata(log_distance)
    distance_rank_matrix = pair_matrix(
        distance_ranks, upper, distance_matrix.shape[0]
    )
    distance_rank_centered = distance_ranks - distance_ranks.mean()
    same_country = same_country_matrix[upper]
    same_count = int(same_country.sum())
    cross_count = len(same_country) - same_count

    observed = {}
    rho_null = {k: np.empty(len(permutations), dtype=float) for k in K_VALUES}
    delta_null = {k: np.empty(len(permutations), dtype=float) for k in K_VALUES}
    for k in K_VALUES:
        ci_values = ci_by_k[k][upper]
        ci_ranks = stats.rankdata(ci_values)
        ci_rank_centered = ci_ranks - ci_ranks.mean()
        denominator = np.sqrt(
            np.dot(ci_rank_centered, ci_rank_centered)
            * np.dot(distance_rank_centered, distance_rank_centered)
        )
        rho = float(np.dot(ci_rank_centered, distance_rank_centered) / denominator)
        delta = float(
            ci_values[same_country == 1].mean()
            - ci_values[same_country == 0].mean()
        )
        observed[k] = {
            "ci_values": ci_values,
            "ci_rank_centered": ci_rank_centered,
            "rho_denominator": denominator,
            "rho": rho,
            "delta": delta,
            "same_mean": float(ci_values[same_country == 1].mean()),
            "cross_mean": float(ci_values[same_country == 0].mean()),
        }

    for start in range(0, len(permutations), batch_size):
        stop = min(start + batch_size, len(permutations))
        batch = permutations[start:stop]
        distance_batch = np.column_stack(
            [
                distance_rank_matrix[np.ix_(permutation, permutation)][upper]
                for permutation in batch
            ]
        )
        same_batch = np.column_stack(
            [
                same_country_matrix[np.ix_(permutation, permutation)][upper]
                for permutation in batch
            ]
        )
        for k in K_VALUES:
            result = observed[k]
            rho_null[k][start:stop] = (
                result["ci_rank_centered"]
                @ (distance_batch - distance_ranks.mean())
                / result["rho_denominator"]
            )
            same_sum = result["ci_values"] @ same_batch
            total_sum = result["ci_values"].sum()
            delta_null[k][start:stop] = (
                same_sum / same_count
                - (total_sum - same_sum) / cross_count
            )

    rows = []
    for k in K_VALUES:
        result = observed[k]
        rho_p = float(
            (1 + np.sum(rho_null[k] <= result["rho"]))
            / (len(permutations) + 1)
        )
        delta_p = float(
            (1 + np.sum(delta_null[k] >= result["delta"]))
            / (len(permutations) + 1)
        )
        rows.append({
            "k": k,
            "n_cities": distance_matrix.shape[0],
            "n_city_pairs": len(distance_values),
            "n_same_country_pairs": same_count,
            "n_cross_country_pairs": cross_count,
            "spearman_ci_vs_log_distance": result["rho"],
            "geographic_qap_p_one_sided": rho_p,
            "mean_ci_same_country": result["same_mean"],
            "mean_ci_cross_country": result["cross_mean"],
            "same_country_mean_difference": result["delta"],
            "same_country_qap_p_one_sided": delta_p,
        })
    return pd.DataFrame(rows)


def fixed_effect_results(directed_by_k):
    size = next(iter(directed_by_k.values())).shape[0]
    source, target = np.where(~np.eye(size, dtype=bool))
    intercept = np.ones(len(source), dtype=float)
    identity = np.eye(size, dtype=float)
    source_design = np.column_stack([intercept, identity[source, :-1]])
    target_design = np.column_stack([intercept, identity[target, :-1]])
    both_design = np.column_stack(
        [intercept, identity[source, :-1], identity[target, :-1]]
    )
    designs = {
        "intercept_only": intercept[:, None],
        "source_city": source_design,
        "target_city": target_design,
        "source_and_target_city": both_design,
    }
    rows = []
    for k in K_VALUES:
        y = directed_by_k[k][source, target]
        total_sum_squares = np.sum((y - y.mean()) ** 2)
        for model, design in designs.items():
            coefficients = np.linalg.lstsq(design, y, rcond=None)[0]
            fitted = design @ coefficients
            residual_sum_squares = np.sum((y - fitted) ** 2)
            r_squared = float(1 - residual_sum_squares / total_sum_squares)
            rank = int(np.linalg.matrix_rank(design))
            adjusted = float(
                1 - (1 - r_squared) * (len(y) - 1) / (len(y) - rank)
            )
            rows.append({
                "k": k,
                "model": model,
                "n_directed_city_pairs": len(y),
                "n_parameters_rank": rank,
                "r_squared": r_squared,
                "adjusted_r_squared": adjusted,
                "fitted_effect_sd": float(np.std(fitted, ddof=0)),
                "residual_sd": float(np.std(y - fitted, ddof=0)),
            })
    return pd.DataFrame(rows)


def controlled_permutation_regression(
        ci_by_k, historical_matrices, log_distance, same_country,
        upper, permutations, batch_size=128):
    """Fit standardized regressions with dependence-aware city permutations."""
    rows = []
    for relationship, historical_matrix in historical_matrices.items():
        raw_predictors = {
            "historical_connection": historical_matrix[upper],
            "log_geographic_distance": log_distance,
            "same_country": same_country,
        }
        standardized_predictors = {
            name: zscore(values) for name, values in raw_predictors.items()
        }
        predictor_names = list(standardized_predictors)
        standardized_design = np.column_stack(
            [np.ones(len(log_distance))]
            + [standardized_predictors[name] for name in predictor_names]
        )
        raw_design = np.column_stack(
            [np.ones(len(log_distance))]
            + [raw_predictors[name] for name in predictor_names]
        )

        observed = {k: {} for k in K_VALUES}
        for k in K_VALUES:
            y_raw = ci_by_k[k][upper]
            y = zscore(y_raw)
            coefficients = np.linalg.lstsq(standardized_design, y, rcond=None)[0]
            raw_coefficients = np.linalg.lstsq(raw_design, y_raw, rcond=None)[0]
            fitted = standardized_design @ coefficients
            r_squared = float(1 - np.sum((y - fitted) ** 2) / np.sum(y ** 2))
            observed[k].update({
                "y": y,
                "coefficients": coefficients,
                "raw_coefficients": raw_coefficients,
                "r_squared": r_squared,
            })

        for predictor_index, focal_name in enumerate(predictor_names, start=1):
            nuisance_names = [name for name in predictor_names if name != focal_name]
            nuisance = np.column_stack(
                [np.ones(len(log_distance))]
                + [standardized_predictors[name] for name in nuisance_names]
            )
            nuisance_inverse = np.linalg.pinv(nuisance)
            focal = standardized_predictors[focal_name]
            residual_focal = focal - nuisance @ (nuisance_inverse @ focal)
            residual_matrix = pair_matrix(
                residual_focal, upper, historical_matrix.shape[0]
            )
            denominator = np.dot(residual_focal, residual_focal)
            null_coefficients = {
                k: np.empty(len(permutations), dtype=float) for k in K_VALUES
            }
            for k in K_VALUES:
                y = observed[k]["y"]
                observed[k]["residual_y"] = y - nuisance @ (nuisance_inverse @ y)

            for start in range(0, len(permutations), batch_size):
                stop = min(start + batch_size, len(permutations))
                batch = permutations[start:stop]
                focal_batch = np.column_stack([
                    residual_matrix[np.ix_(permutation, permutation)][upper]
                    for permutation in batch
                ])
                for k in K_VALUES:
                    null_coefficients[k][start:stop] = (
                        observed[k]["residual_y"] @ focal_batch / denominator
                    )

            expected_direction = "negative" if focal_name == "log_geographic_distance" else "positive"
            for k in K_VALUES:
                coefficient = float(observed[k]["coefficients"][predictor_index])
                if expected_direction == "negative":
                    extreme = np.sum(null_coefficients[k] <= coefficient)
                else:
                    extreme = np.sum(null_coefficients[k] >= coefficient)
                p_value = float((1 + extreme) / (len(permutations) + 1))
                rows.append({
                    "k": k,
                    "historical_model": relationship,
                    "predictor": focal_name,
                    "standardized_beta": coefficient,
                    "unstandardized_coefficient": float(
                        observed[k]["raw_coefficients"][predictor_index]
                    ),
                    "permutation_p_one_sided": p_value,
                    "expected_direction": expected_direction,
                    "model_r_squared": observed[k]["r_squared"],
                    "n_city_pairs": len(log_distance),
                    "n_permutations": len(permutations),
                    "method": (
                        "multiple linear regression with simultaneous "
                        "row-column city-label permutation inference"
                    ),
                })
    return pd.DataFrame(rows)


def write_regression_table(regression):
    selected = regression[regression.k == 1000].set_index(
        ["historical_model", "predictor"]
    )

    def coefficient(model, predictor):
        row = selected.loc[(model, predictor)]
        p_value = row.permutation_p_one_sided
        p_text = "<0.001" if p_value < 0.001 else f"{p_value:.3f}"
        return f"{row.standardized_beta:.3f} $({p_text})$"

    direct_r2 = selected.loc[("direct_tie", "historical_connection")].model_r_squared
    regime_r2 = selected.loc[("shared_regime", "historical_connection")].model_r_squared
    table = rf"""\begin{{table}}[!htbp]
\centering
\caption{{\textbf{{Associations between historical connections and the Covered Index after controlling for geographic and national dependence.}} Standardized coefficients are reported, with one-sided city-label permutation $P$ values in parentheses. Statistical significance was assessed using 9,999 simultaneous row--column city-label permutations.}}
\label{{tab:permutation-regression}}
\begin{{tabular}}{{lcc}}
\toprule
Predictor & Direct-tie model & Shared-regime model \\
\midrule
Direct tie & {coefficient('direct_tie', 'historical_connection')} & --- \\
Shared historical regime & --- & {coefficient('shared_regime', 'historical_connection')} \\
$\log(\mathrm{{Geographic\ distance}})$ & {coefficient('direct_tie', 'log_geographic_distance')} & {coefficient('shared_regime', 'log_geographic_distance')} \\
Same country & {coefficient('direct_tie', 'same_country')} & {coefficient('shared_regime', 'same_country')} \\
\midrule
$R^2$ & {direct_r2:.3f} & {regime_r2:.3f} \\
City pairs & 8,385 & 8,385 \\
Permutations & 9,999 & 9,999 \\
\bottomrule
\end{{tabular}}
\end{{table}}
"""
    (DOC_OUTPUT / "permutation_regression_table_k1000.tex").write_text(
        table, encoding="utf-8"
    )


def main():
    city_table = pd.read_csv(CITY_FILE)
    ci = pd.read_csv(CI_FILE)
    cities = city_table.city.tolist()
    if len(cities) != 130 or len(set(cities)) != 130:
        raise RuntimeError("Expected 130 unique cities")
    upper = np.triu_indices(len(cities), 1)

    distance_matrix = haversine_matrix(city_table.longitude, city_table.latitude)
    historical_mapping = historical_city_mapping(cities)
    historical_country = {
        ci_city: country for _, ci_city, country in historical_mapping
    }
    country_labels = np.asarray([historical_country[city] for city in cities])
    same_country_matrix = (
        country_labels[:, None] == country_labels[None, :]
    ).astype(float)
    np.fill_diagonal(same_country_matrix, 0.0)
    direct_tie_matrix = historical_matrix(
        "Direct Tie Matrix", cities, historical_mapping
    )
    shared_regime_matrix = historical_matrix(
        "Shared Regime Matrix", cities, historical_mapping
    )

    directed_by_k = {}
    symmetric_by_k = {}
    for k in K_VALUES:
        directed_by_k[k], symmetric_by_k[k] = ci_matrices(ci[ci.k == k], cities)

    rng = np.random.default_rng(RANDOM_SEED)
    permutations = np.asarray(
        [rng.permutation(len(cities)) for _ in range(N_PERMUTATIONS)],
        dtype=np.int16,
    )
    diagnostics = dependence_diagnostics(
        symmetric_by_k,
        distance_matrix,
        same_country_matrix,
        upper,
        permutations,
    )
    fixed_effects = fixed_effect_results(directed_by_k)
    controlled = controlled_permutation_regression(
        symmetric_by_k,
        {"direct_tie": direct_tie_matrix, "shared_regime": shared_regime_matrix},
        np.log(distance_matrix[upper]),
        same_country_matrix[upper],
        upper,
        permutations,
    )

    pair_table = pd.DataFrame({
        "city_1": np.asarray(cities)[upper[0]],
        "city_2": np.asarray(cities)[upper[1]],
        "distance_km": distance_matrix[upper],
        "same_country": same_country_matrix[upper].astype(int),
        "direct_tie": direct_tie_matrix[upper].astype(int),
        "shared_regime": shared_regime_matrix[upper].astype(int),
    })
    for k in K_VALUES:
        pair_table[f"ci_symmetric_k{k}"] = symmetric_by_k[k][upper]

    OUTPUT.mkdir(parents=True, exist_ok=True)
    DOC_OUTPUT.mkdir(parents=True, exist_ok=True)
    diagnostics.to_csv(OUTPUT / "dependence_diagnostics_results.csv", index=False)
    fixed_effects.to_csv(OUTPUT / "shared_city_fixed_effects_results.csv", index=False)
    controlled.to_csv(
        OUTPUT / "city_label_permutation_regression_results.csv", index=False
    )
    write_regression_table(controlled)
    pair_table.to_csv(OUTPUT / "dyadic_pair_audit_table.csv", index=False)
    metadata = {
        "objective": (
            "Diagnose violations of strict i.i.d. assumptions in complete city-pair data "
            "and evaluate historical associations with dependence-aware inference."
        ),
        "n_cities": len(cities),
        "n_undirected_pairs": len(upper[0]),
        "n_directed_pairs": len(cities) * (len(cities) - 1),
        "ci_for_diagnostics": "mean of CI(i->j) and CI(j->i)",
        "ci_for_fixed_effects": "directed CI(i->j)",
        "permutation": "simultaneous city-row/column label permutation",
        "n_permutations": N_PERMUTATIONS,
        "random_seed": RANDOM_SEED,
        "regression_method": (
            "multiple linear regression with simultaneous row-column "
            "city-label permutation inference"
        ),
        "regression_controls": [
            "natural-log geographic distance", "same-country status"
        ],
        "same_country_source": (
            "country field in historical_city_connection_layers_138x138.xlsx / City List"
        ),
    }
    (OUTPUT / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("\nDependence diagnostics")
    print(diagnostics.to_string(index=False))
    print("\nShared-city fixed effects")
    print(fixed_effects.to_string(index=False))
    print("\nControlled city-label permutation regressions")
    print(controlled.to_string(index=False))


if __name__ == "__main__":
    main()
