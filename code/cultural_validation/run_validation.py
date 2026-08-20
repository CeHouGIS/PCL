#!/usr/bin/env python3
"""Validate satellite-derived city morphology against WVS/EVS cultural distance.

Inputs are the unpacked PCL archive, Natural Earth country boundaries, CEPII
GeoDist, and the PSW2024 dyadic cultural-distance panel. Outputs are CSV tables,
figures, and a Markdown summary. No model checkpoint is required.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from osgeo import gdal, ogr
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "data" / "external" / "cultural_validation"
OUT = ROOT / "data" / "results" / "cultural_validation"
IMAGE_OUTPUT = ROOT / "images" / "cultural_validation"
DOC_OUTPUT = ROOT / "docs" / "cultural_validation"
OUT.mkdir(parents=True, exist_ok=True)
IMAGE_OUTPUT.mkdir(parents=True, exist_ok=True)
DOC_OUTPUT.mkdir(parents=True, exist_ok=True)
SEED = 20260803


def city_centres_and_countries() -> pd.DataFrame:
    shp = EXT / "natural_earth" / "ne_10m_admin_0_countries.shp"
    ds = ogr.Open(str(shp))
    layer = ds.GetLayer()
    countries = []
    for feature in layer:
        geom = feature.GetGeometryRef().Clone()
        countries.append(
            {
                "iso3": feature.GetField("ISO_A3"),
                "adm0_a3": feature.GetField("ADM0_A3"),
                "name": feature.GetField("ADMIN"),
                "geom": geom,
            }
        )

    rows = []
    for tif in sorted((ROOT / "data" / "rasters" / "merge" / "200").glob("*.tif")):
        raster = gdal.Open(str(tif))
        gt = raster.GetGeoTransform()
        lon = gt[0] + raster.RasterXSize * gt[1] / 2
        lat = gt[3] + raster.RasterYSize * gt[5] / 2
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(lon, lat)
        hit = [c for c in countries if c["geom"].Intersects(point)]
        method = "contains"
        if not hit:
            hit = [min(countries, key=lambda c: c["geom"].Distance(point))]
            method = "nearest"
        c = hit[0]
        iso3 = c["iso3"] if c["iso3"] and c["iso3"] != "-99" else c["adm0_a3"]
        rows.append(
            {
                "city": tif.stem,
                "longitude": lon,
                "latitude": lat,
                "iso3": iso3,
                "country": c["name"],
                "mapping_method": method,
            }
        )
    result = pd.DataFrame(rows)
    result.to_csv(OUT / "city_country_mapping.csv", index=False)
    return result


def load_city(k: int, city: str):
    tif = ROOT / "data" / "rasters" / "merge" / str(k) / f"{city}.tif"
    labels = gdal.Open(str(tif)).ReadAsArray().astype(int)
    vals, counts = np.unique(labels[labels >= 0], return_counts=True)
    vectors, weights, used = [], [], []
    for label, count in zip(vals, counts):
        p = ROOT / "data" / "rasters" / "clusters" / str(k) / "avg_feature" / f"{city}_patch_{label}.npy"
        if p.exists():
            vectors.append(np.load(p).astype(np.float64))
            weights.append(count)
            used.append(label)
    vectors = np.stack(vectors)
    vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
    weights = np.asarray(weights, dtype=np.float64)
    weights /= weights.sum()
    return vectors, weights, len(vals), len(used), int(np.sum(counts))


def directed_ci(a, b) -> float:
    return float(np.sum(a[1] * np.max(a[0] @ b[0].T, axis=1)))


def calculate_ci(mapping: pd.DataFrame) -> pd.DataFrame:
    cities = mapping.city.tolist()
    location = mapping.set_index("city").to_dict("index")
    all_rows = []
    for k in (200, 500, 1000):
        cache = {city: load_city(k, city) for city in cities}
        for i, a in enumerate(cities):
            for b in cities[i + 1 :]:
                ab = directed_ci(cache[a], cache[b])
                ba = directed_ci(cache[b], cache[a])
                all_rows.append(
                    {
                        "k": k,
                        "city_1": a,
                        "city_2": b,
                        "iso3_1": location[a]["iso3"],
                        "iso3_2": location[b]["iso3"],
                        "ci_1_to_2": ab,
                        "ci_2_to_1": ba,
                        "ci_symmetric": (ab + ba) / 2,
                        "ci_asymmetry_abs": abs(ab - ba),
                        "n_pixels_1": cache[a][4],
                        "n_pixels_2": cache[b][4],
                        "n_prototypes_1": cache[a][3],
                        "n_prototypes_2": cache[b][3],
                    }
                )
    result = pd.DataFrame(all_rows)
    result.to_csv(OUT / "city_pair_ci.csv", index=False)
    return result


def merge_external(ci: pd.DataFrame) -> pd.DataFrame:
    culture = pd.read_csv(EXT / "cultural_distance_PSW2024.csv")
    culture = culture[culture.year == 2021].copy()
    culture = culture.rename(columns={"countrycode_1": "iso3_1", "countrycode_2": "iso3_2"})
    culture = culture[["iso3_1", "iso3_2", "cultdist", "cultdist_std", "n_questions"]]

    # The Stata release is used because the legacy BIFF .xls file is not
    # parsed reliably by current xlrd versions.
    cepii = pd.read_stata(EXT / "dist_cepii.dta")
    cepii = cepii.rename(columns={"iso_o": "iso3_1", "iso_d": "iso3_2"})
    use = [
        "iso3_1", "iso3_2", "contig", "comlang_off", "comlang_ethno",
        "colony", "comcol", "smctry", "dist", "distw",
    ]
    merged = ci.merge(culture, on=["iso3_1", "iso3_2"], how="left")
    merged = merged.merge(cepii[use], on=["iso3_1", "iso3_2"], how="left")
    merged["log_distance"] = np.log1p(merged["dist"])
    merged["same_country"] = (merged.iso3_1 == merged.iso3_2).astype(int)
    merged["log_pixel_ratio"] = np.abs(np.log(merged.n_pixels_1 / merged.n_pixels_2))
    merged["log_proto_product"] = np.log(merged.n_prototypes_1 * merged.n_prototypes_2)
    merged.to_csv(OUT / "analysis_dataset_all_pairs.csv", index=False)
    return merged


def zscore(x):
    x = np.asarray(x, dtype=float)
    return (x - np.mean(x)) / np.std(x, ddof=0)


def ols_table(df: pd.DataFrame, y: str, xs: list[str]):
    cols = [y] + xs
    d = df[cols].dropna()
    Y = zscore(d[y].to_numpy())
    Xcols = [zscore(d[x].to_numpy()) for x in xs]
    X = np.column_stack([np.ones(len(d))] + Xcols)
    beta, _, _, _ = np.linalg.lstsq(X, Y, rcond=None)
    residual = Y - X @ beta
    dof = len(Y) - X.shape[1]
    sigma2 = residual @ residual / dof
    vcov = sigma2 * np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(vcov))
    tval = beta / se
    pval = 2 * stats.t.sf(np.abs(tval), dof)
    r2 = 1 - (residual @ residual) / np.sum((Y - Y.mean()) ** 2)
    return {
        "n": len(d), "r2": float(r2),
        "terms": ["intercept"] + xs,
        "beta": beta.tolist(), "se_naive": se.tolist(), "p_naive": pval.tolist(),
    }


def residualize(values, controls):
    y = zscore(values)
    X = np.column_stack([np.ones(len(y))] + [zscore(controls[c]) for c in controls])
    return y - X @ np.linalg.lstsq(X, y, rcond=None)[0]


def permutation_partial_test(df: pd.DataFrame, n_perm=999):
    controls = ["log_distance", "contig", "log_pixel_ratio", "log_proto_product"]
    needed = ["ci_symmetric", "cultdist", "iso3_1", "iso3_2"] + controls
    d = df[needed].dropna().reset_index(drop=True)
    morph_res = residualize(d.ci_symmetric.to_numpy(), {c: d[c].to_numpy() for c in controls})
    culture_res = residualize(d.cultdist.to_numpy(), {c: d[c].to_numpy() for c in controls})
    observed = stats.pearsonr(morph_res, culture_res).statistic

    # Permute cultural identities at country level while retaining the geographic controls.
    countries = sorted(set(d.iso3_1) | set(d.iso3_2))
    lookup = {
        tuple(sorted((r.iso3_1, r.iso3_2))): r.cultdist
        for r in d[["iso3_1", "iso3_2", "cultdist"]].drop_duplicates().itertuples(index=False)
    }
    rng = np.random.default_rng(SEED)
    permuted = []
    for _ in range(n_perm):
        shuffled = rng.permutation(countries)
        mapping = dict(zip(countries, shuffled))
        vals = np.array([
            lookup.get(tuple(sorted((mapping[a], mapping[b]))), np.nan)
            for a, b in zip(d.iso3_1, d.iso3_2)
        ])
        ok = np.isfinite(vals)
        if ok.sum() < len(vals) * 0.8:
            continue
        ctr = {c: d.loc[ok, c].to_numpy() for c in controls}
        cr = residualize(vals[ok], ctr)
        mr = residualize(d.loc[ok, "ci_symmetric"].to_numpy(), ctr)
        permuted.append(stats.pearsonr(mr, cr).statistic)
    permuted = np.asarray(permuted)
    p = (1 + np.sum(np.abs(permuted) >= abs(observed))) / (1 + len(permuted))
    return float(observed), float(p), permuted


def analyse(merged: pd.DataFrame):
    results = {"source": "PSW2024 WVS/EVS cultural distance, 2021 wave", "scales": {}}
    model_rows = []
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.1), sharey=True)
    for ax, k in zip(axes, (200, 500, 1000)):
        d = merged[(merged.k == k) & (merged.same_country == 0)].dropna(
            subset=["ci_symmetric", "cultdist", "dist"]
        ).copy()
        rho, rho_p = stats.spearmanr(d.ci_symmetric, d.cultdist)
        distant = d[d.dist >= 5000]
        far_rho, far_p = stats.spearmanr(distant.ci_symmetric, distant.cultdist)
        base_x = ["log_distance", "contig", "log_pixel_ratio", "log_proto_product"]
        full_x = base_x + ["cultdist"]
        extended_x = full_x + ["comlang_off", "comlang_ethno", "colony", "comcol"]
        base = ols_table(d, "ci_symmetric", base_x)
        full = ols_table(d, "ci_symmetric", full_x)
        extended = ols_table(d, "ci_symmetric", extended_x)
        partial_r, perm_p, null = permutation_partial_test(d)
        np.save(OUT / f"permutation_null_k{k}.npy", null)
        results["scales"][str(k)] = {
            "n_city_pairs": len(d),
            "n_countries": len(set(d.iso3_1) | set(d.iso3_2)),
            "spearman_ci_vs_cultural_distance": float(rho),
            "spearman_p_naive": float(rho_p),
            "distant_over_5000km_n": len(distant),
            "distant_spearman": float(far_rho),
            "distant_p_naive": float(far_p),
            "partial_r_controlling_geography_and_sample_size": partial_r,
            "country_label_permutation_p": perm_p,
            "base_model": base,
            "culture_model": full,
            "extended_model": extended,
            "incremental_r2_culture": full["r2"] - base["r2"],
        }
        for label, model in [("base", base), ("culture", full), ("extended", extended)]:
            for term, beta, se, p in zip(model["terms"], model["beta"], model["se_naive"], model["p_naive"]):
                model_rows.append({"k": k, "model": label, "n": model["n"], "r2": model["r2"], "term": term, "beta_standardized": beta, "se_naive": se, "p_naive": p})

        # Hexbin is robust to the many overlapping city pairs sharing country scores.
        hb = ax.hexbin(d.cultdist, d.ci_symmetric, gridsize=28, mincnt=1, cmap="viridis")
        slope, intercept = np.polyfit(d.cultdist, d.ci_symmetric, 1)
        xx = np.linspace(d.cultdist.min(), d.cultdist.max(), 100)
        ax.plot(xx, intercept + slope * xx, color="crimson", lw=1.8)
        ax.set_title(f"K={k}: Spearman r={rho:.3f}")
        ax.set_xlabel("WVS/EVS cultural distance")
        if k == 200:
            ax.set_ylabel("Symmetric Covered Index")
    fig.subplots_adjust(left=.07, right=.90, bottom=.16, top=.88, wspace=.12)
    cax = fig.add_axes([.92, .18, .015, .68])
    fig.colorbar(hb, cax=cax, label="City-pair count")
    fig.savefig(IMAGE_OUTPUT / "ci_vs_cultural_distance.png", dpi=220)
    fig.savefig(IMAGE_OUTPUT / "ci_vs_cultural_distance.pdf")
    plt.close(fig)

    with open(OUT / "validation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    pd.DataFrame(model_rows).to_csv(OUT / "regression_results.csv", index=False)
    return results


def write_summary(mapping, merged, results):
    lines = [
        "# Cultural similarity validation results",
        "",
        "Main external criterion: PSW2024 dyadic cultural distance computed from WVS/EVS responses (2021 wave).",
        "Same-country city pairs are excluded because the external data are country-level.",
        "Negative correlations mean that culturally more distant countries have lower city-morphology similarity.",
        "",
        f"Cities mapped: {len(mapping)}; country mapping methods: {mapping.mapping_method.value_counts().to_dict()}.",
        "",
        "| K | matched cross-country city pairs | countries | Spearman r | r for >5000 km | partial r | country-permutation p | incremental R2 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for k in (200, 500, 1000):
        r = results["scales"][str(k)]
        lines.append(
            f"| {k} | {r['n_city_pairs']} | {r['n_countries']} | "
            f"{r['spearman_ci_vs_cultural_distance']:.4f} | {r['distant_spearman']:.4f} | "
            f"{r['partial_r_controlling_geography_and_sample_size']:.4f} | "
            f"{r['country_label_permutation_p']:.4f} | {r['incremental_r2_culture']:.5f} |"
        )
    lines += [
        "",
        "Partial correlations control log geographic distance, contiguity, city pixel-count ratio, and prototype-count product.",
        "The permutation test shuffles cultural identities at country level and is the primary inference; naive pair-level p-values are retained only for diagnostics.",
        "The analysis establishes association/predictive validity, not a causal direction from culture to morphology.",
    ]
    (DOC_OUTPUT / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    mapping = city_centres_and_countries()
    ci = calculate_ci(mapping)
    merged = merge_external(ci)
    results = analyse(merged)
    write_summary(mapping, merged, results)
    print((DOC_OUTPUT / "RESULTS.md").read_text())


if __name__ == "__main__":
    main()
