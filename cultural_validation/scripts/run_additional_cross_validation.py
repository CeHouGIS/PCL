#!/usr/bin/env python3
"""Cross-validate city morphology with independent cultural datasets.

The analyses use Hofstede's six national-culture dimensions, four independent
psychological domains from the EcoCultural Dataset, and CEPII common-language
relations. Country-label permutation tests account for dyadic dependence.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from osgeo import ogr
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "external" / "additional"
NE = ROOT / "external" / "natural_earth" / "ne_10m_admin_0_countries.shp"
OUT = ROOT / "output"
SEED = 20260805
N_PERM = 999

GROUPS = {
    "Hofstede 6D": ["pdi", "idv", "mas", "uai", "ltowvs", "ivr"],
    "Schwartz values": ["harmony", "embedded", "hierarchy", "mastery", "aff.auton", "intel.auton", "egalitar"],
    "Big Five": ["extraversion", "agreeableness", "conscientiousness", "neuroticism", "openness"],
    "Moral foundations": ["authority", "fairness", "harm", "ingroup", "purity"],
    "Fundamental motives": ["SPO", "DIS", "AFG", "AFI", "AFX", "STA", "MAT", "MRB", "MRT", "KCF", "KCC"],
}

# Hofstede uses historical three-letter abbreviations rather than ISO3.
HOFSTEDE_TO_ISO3 = {
    "ALG":"DZA", "AUL":"AUS", "BAN":"BGD", "BUL":"BGR", "BUF":"BFA",
    "CHI":"CHN", "COS":"CRI", "DEN":"DNK", "ECA":"ECU", "SAL":"SLV",
    "GER":"DEU", "GRE":"GRC", "HOK":"HKG", "ICE":"ISL", "IDO":"IDN",
    "IRE":"IRL", "LAT":"LVA", "LIT":"LTU", "MAC":"MKD", "MAL":"MYS",
    "MOL":"MDA", "MNG":"MNE", "NET":"NLD", "NIG":"NGA", "PHI":"PHL",
    "POR":"PRT", "ROM":"ROU", "SAF":"ZAF", "SIN":"SGP", "SLK":"SVK",
    "SPA":"ESP", "SWI":"CHE", "TAI":"TWN", "TAN":"TZA", "TRI":"TTO",
    "VIE":"VNM", "ZAM":"ZMB", "ZIM":"ZWE",
}


def iso2_to_iso3():
    ds = ogr.Open(str(NE))
    layer = ds.GetLayer()
    mapping = {}
    for feature in layer:
        iso2 = feature.GetField("ISO_A2")
        iso3 = feature.GetField("ISO_A3")
        if iso3 == "-99":
            iso3 = feature.GetField("ADM0_A3")
        if iso2 and iso2 != "-99":
            mapping[iso2] = iso3
    mapping["XK"] = "XKX"
    return mapping


def standard_profiles(frame, id_col, columns):
    d = frame[[id_col] + columns].copy()
    for column in columns:
        d[column] = pd.to_numeric(d[column], errors="coerce")
    d = d.dropna(subset=columns)
    d[columns] = (d[columns] - d[columns].mean()) / d[columns].std(ddof=0)
    return {row[id_col]: row[columns].to_numpy(dtype=float) for _, row in d.iterrows()}


def load_profiles():
    hof = pd.read_csv(EXT / "hofstede_6d.csv", sep=";", na_values="#NULL!")
    hof["iso3"] = hof.ctr.map(HOFSTEDE_TO_ISO3).fillna(hof.ctr)
    profiles = {"Hofstede 6D": standard_profiles(hof, "iso3", GROUPS["Hofstede 6D"])}

    ecd = pd.read_csv(EXT / "ECD_Cultural_Variables.csv")
    ecd["iso3"] = ecd.country.map(iso2_to_iso3())
    for name in ("Schwartz values", "Big Five", "Moral foundations", "Fundamental motives"):
        profiles[name] = standard_profiles(ecd, "iso3", GROUPS[name])
    return profiles


def euclidean_distance(profile_a, profile_b):
    # Root-mean-square standardized distance is comparable across domains with
    # different numbers of variables.
    return float(np.sqrt(np.mean((profile_a - profile_b) ** 2)))


def residualize(values, controls):
    values = np.asarray(values, dtype=float)
    y = (values - values.mean()) / values.std(ddof=0)
    matrix = [np.ones(len(y))]
    for control in controls:
        z = np.asarray(control, dtype=float)
        matrix.append((z - z.mean()) / z.std(ddof=0))
    X = np.column_stack(matrix)
    return y - X @ np.linalg.lstsq(X, y, rcond=None)[0]


def analyse_profile(data, profiles, rng):
    countries = sorted(set(data.iso3_1) & set(profiles) | set(data.iso3_2) & set(profiles))
    d = data[data.iso3_1.isin(countries) & data.iso3_2.isin(countries)].copy()
    d["external_distance"] = [euclidean_distance(profiles[a], profiles[b]) for a, b in zip(d.iso3_1, d.iso3_2)]
    controls = [d.log_distance, d.contig, d.log_pixel_ratio, d.log_proto_product]
    morph_res = residualize(d.ci_symmetric, controls)
    culture_res = residualize(d.external_distance, controls)
    observed = stats.pearsonr(morph_res, culture_res).statistic
    rho = stats.spearmanr(d.ci_symmetric, d.external_distance).statistic
    far = d[d.dist >= 5000]
    far_rho = stats.spearmanr(far.ci_symmetric, far.external_distance).statistic

    null = []
    vectors = [profiles[c] for c in countries]
    for _ in range(N_PERM):
        shuffled = rng.permutation(len(countries))
        perm = {country: vectors[index] for country, index in zip(countries, shuffled)}
        distance = np.asarray([euclidean_distance(perm[a], perm[b]) for a, b in zip(d.iso3_1, d.iso3_2)])
        distance_res = residualize(distance, controls)
        null.append(stats.pearsonr(morph_res, distance_res).statistic)
    null = np.asarray(null)
    p = (1 + np.sum(np.abs(null) >= abs(observed))) / (1 + len(null))
    return d, rho, far_rho, observed, p, null


def analyse_language(data, cepii, rng):
    pair_lookup = {
        tuple(sorted((row.iso_o, row.iso_d))): 1.0 - float(row.comlang_ethno)
        for row in cepii.itertuples(index=False)
    }
    countries = sorted(set(data.iso3_1) | set(data.iso3_2))
    keep = [tuple(sorted((a, b))) in pair_lookup for a, b in zip(data.iso3_1, data.iso3_2)]
    d = data[np.asarray(keep)].copy()
    d["external_distance"] = [pair_lookup[tuple(sorted((a, b)))] for a, b in zip(d.iso3_1, d.iso3_2)]
    controls = [d.log_distance, d.contig, d.log_pixel_ratio, d.log_proto_product]
    morph_res = residualize(d.ci_symmetric, controls)
    culture_res = residualize(d.external_distance, controls)
    observed = stats.pearsonr(morph_res, culture_res).statistic
    rho = stats.spearmanr(d.ci_symmetric, d.external_distance).statistic
    far = d[d.dist >= 5000]
    far_rho = stats.spearmanr(far.ci_symmetric, far.external_distance).statistic
    null = []
    for _ in range(N_PERM):
        shuffled = rng.permutation(countries)
        mapping = dict(zip(countries, shuffled))
        vals = np.asarray([pair_lookup.get(tuple(sorted((mapping[a], mapping[b]))), np.nan) for a, b in zip(d.iso3_1, d.iso3_2)])
        ok = np.isfinite(vals)
        if ok.sum() < 100:
            continue
        partial = residualize(vals[ok], [c[ok] for c in controls])
        null.append(stats.pearsonr(morph_res[ok], partial).statistic)
    null = np.asarray(null)
    p = (1 + np.sum(np.abs(null) >= abs(observed))) / (1 + len(null))
    return d, rho, far_rho, observed, p, null


def holm_adjust(frame):
    adjusted = np.empty(len(frame))
    order = np.argsort(frame.permutation_p.to_numpy())
    running = 0.0
    m = len(frame)
    for rank, index in enumerate(order):
        value = min(1.0, (m - rank) * frame.iloc[index].permutation_p)
        running = max(running, value)
        adjusted[index] = running
    frame["holm_p_across_all_tests"] = adjusted
    return frame


def plot_results(results):
    font_dir = Path("/usr/share/fonts/truetype/liberation2")
    for font in font_dir.glob("LiberationSans-*.ttf"):
        font_manager.fontManager.addfont(font)
    mpl.rcParams.update({
        "font.family":"sans-serif", "font.sans-serif":["Liberation Sans"],
        "font.size":7, "font.weight":"bold", "axes.labelweight":"bold",
        "axes.linewidth":.7, "pdf.fonttype":42, "ps.fonttype":42,
    })
    order = ["Hofstede 6D", "Schwartz values", "Big Five", "Moral foundations", "Fundamental motives", "CEPII common language"]
    colors = {200:"#4477AA", 500:"#EE6677", 1000:"#228833"}
    fig, ax = plt.subplots(figsize=(7.09, 2.8))
    y = np.arange(len(order))
    offsets = {200:-.20, 500:0, 1000:.20}
    for k in (200, 500, 1000):
        d = results[results.k == k].set_index("dataset").loc[order]
        ax.scatter(d.partial_r, y + offsets[k], s=24, color=colors[k], label=f"K = {k}", zorder=3)
        for yi, (_, row) in zip(y + offsets[k], d.iterrows()):
            if row.holm_p_across_all_tests <= .05:
                ax.text(row.partial_r - .012, yi, "*", ha="right", va="center", fontsize=8, color=colors[k])
    ax.axvline(0, color="#555555", lw=.7, ls="--")
    ax.set_yticks(y, order)
    ax.invert_yaxis()
    ax.set_xlabel("Partial correlation with morphological similarity")
    ax.text(.0, 1.04, "Cultural distance → lower morphological similarity", transform=ax.transAxes, ha="left", fontsize=7)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    for tick in ax.get_xticklabels() + ax.get_yticklabels(): tick.set_fontweight("bold")
    ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(.5, -.38))
    fig.subplots_adjust(left=.25, right=.98, top=.89, bottom=.25)
    for ext, dpi in (("pdf",None),("png",600),("tif",600)):
        fig.savefig(OUT / f"additional_cultural_cross_validation.{ext}", dpi=dpi, facecolor="white")
    plt.close(fig)


def main():
    data = pd.read_csv(OUT / "analysis_dataset_all_pairs.csv")
    data = data[data.same_country == 0].copy()
    profiles = load_profiles()
    cepii = pd.read_stata(ROOT / "external" / "dist_cepii.dta")
    rows = []
    nulls = {}
    for k in (200, 500, 1000):
        scale = data[data.k == k].dropna(subset=["ci_symmetric", "log_distance", "contig", "log_pixel_ratio", "log_proto_product"])
        for index, (name, profile) in enumerate(profiles.items()):
            d, rho, far_rho, partial, p, null = analyse_profile(scale, profile, np.random.default_rng(SEED + k + index))
            rows.append({"dataset":name, "k":k, "city_pairs":len(d), "countries":len(set(d.iso3_1)|set(d.iso3_2)), "spearman_r":rho, "far_over_5000km_r":far_rho, "partial_r":partial, "permutation_p":p})
            nulls[f"{name}_k{k}"] = null
        d, rho, far_rho, partial, p, null = analyse_language(scale, cepii, np.random.default_rng(SEED + k + 99))
        rows.append({"dataset":"CEPII common language", "k":k, "city_pairs":len(d), "countries":len(set(d.iso3_1)|set(d.iso3_2)), "spearman_r":rho, "far_over_5000km_r":far_rho, "partial_r":partial, "permutation_p":p})
        nulls[f"CEPII common language_k{k}"] = null
    results = holm_adjust(pd.DataFrame(rows))
    results.to_csv(OUT / "additional_cross_validation_results.csv", index=False)
    np.savez_compressed(OUT / "additional_cross_validation_nulls.npz", **nulls)
    plot_results(results)
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
