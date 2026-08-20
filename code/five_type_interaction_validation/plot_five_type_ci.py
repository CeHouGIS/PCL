#!/usr/bin/env python3
"""Plot one-panel CI distributions for the five interaction types."""

from pathlib import Path
import re
import unicodedata

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
WORKBOOK = ROOT / "data" / "raw" / "historical_city_connection_layers_138x138.xlsx"
CI_FILE = ROOT / "data" / "results" / "cultural_validation" / "city_pair_ci.csv"
DATA_OUTPUT = ROOT / "data" / "results" / "five_type_interaction_validation"
IMAGE_OUTPUT = ROOT / "images" / "five_type_interaction_validation"
K = 1000

ALIASES = {
    "Beira": "Beria", "Brasília": "Brazilia", "City of Tshwane": "Tshwane",
    "Havana": "Habana", "Lisbon": "Lisboa", "Malacca": "Melaka",
    "Mexico City": "Mexico", "Milan": "Milano", "NCT of Delhi": "Delhi",
    "Nairobi": "Narobi", "New York City": "Newyork", "Quebec City": "Quebec",
    "Quezon City": "LungsodQuezon", "Saint Petersburg": "St.Petersburg",
    "Setúbal": "Setobal", "Seville": "Sevilla", "São Paulo": "SanPaulo",
    "The Hague": "Denhaag", "Turin": "Torino",
}

CATEGORY_ORDER = ["C1", "C2", "C3", "C4", "C5"]
LABELS = {
    "C1": "Colonial and\nimperial",
    "C2": "Religious and\ncivilizational",
    "C3": "Planning and\narchitectural",
    "C4": "Shared official\nlanguage",
    "C5": "Trade-mediated\nexchange",
}
COLORS = ["#4C78A8", "#8C6BB1", "#E28E2C", "#59A14F", "#B95F72"]


def normalize(name):
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", text)


def configure_fonts():
    font_dir = Path("/usr/share/fonts/truetype/liberation2")
    for path in sorted(font_dir.glob("LiberationSans-*.ttf")):
        font_manager.fontManager.addfont(path)
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
        "font.size": 7.5,
        "font.weight": "bold",
        "axes.labelsize": 9,
        "axes.labelweight": "bold",
        "axes.linewidth": 0.75,
        "xtick.labelsize": 7.1,
        "ytick.labelsize": 7.5,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def main():
    configure_fonts()
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
    IMAGE_OUTPUT.mkdir(parents=True, exist_ok=True)
    city_list = pd.read_excel(WORKBOOK, sheet_name="City List")
    pair_types = pd.read_excel(WORKBOOK, sheet_name="Interaction Pairs")
    ci = pd.read_csv(CI_FILE)
    frame = ci[ci.k == K].copy()

    ci_cities = sorted(set(frame.city_1) | set(frame.city_2))
    normalized_ci = {normalize(city): city for city in ci_cities}
    mapping = {}
    for row in city_list.itertuples(index=False):
        ci_city = ALIASES.get(row.city, normalized_ci.get(normalize(row.city)))
        if ci_city is not None:
            mapping[row.city] = ci_city
    if len(mapping) != 130:
        raise RuntimeError(f"Expected 130 matched cities, got {len(mapping)}")

    ci_lookup = {}
    for row in frame.itertuples(index=False):
        ci_lookup[tuple(sorted((row.city_1, row.city_2)))] = float(row.ci_symmetric)

    values = {code: [] for code in CATEGORY_ORDER}
    for row in pair_types.itertuples(index=False):
        city_a = mapping.get(row.city_a)
        city_b = mapping.get(row.city_b)
        if city_a is None or city_b is None:
            continue
        value = ci_lookup.get(tuple(sorted((city_a, city_b))))
        if value is not None:
            values[row.category_code].append(value)

    results = []
    for code in CATEGORY_ORDER:
        array = np.asarray(values[code], dtype=float)
        results.append({
            "category_code": code,
            "interaction_type": LABELS[code].replace("\n", " "),
            "n_city_pairs": len(array),
            "mean_ci": array.mean(),
            "median_ci": np.median(array),
            "q25_ci": np.quantile(array, 0.25),
            "q75_ci": np.quantile(array, 0.75),
        })
    pd.DataFrame(results).to_csv(DATA_OUTPUT / "five_type_ci_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(7.09, 3.25))
    positions = np.arange(1, 6)
    boxes = ax.boxplot(
        [values[code] for code in CATEGORY_ORDER],
        positions=positions,
        widths=0.54,
        patch_artist=True,
        showfliers=False,
        whis=(5, 95),
        medianprops={"color": "white", "linewidth": 1.45},
        boxprops={"edgecolor": "#343A40", "linewidth": 0.85},
        whiskerprops={"color": "#343A40", "linewidth": 0.80},
        capprops={"color": "#343A40", "linewidth": 0.80},
    )
    for box, color in zip(boxes["boxes"], COLORS):
        box.set_facecolor(color)
        box.set_alpha(0.82)

    ax.set_xticks(positions, [LABELS[code] for code in CATEGORY_ORDER])
    ax.set_ylabel("Covered Index")
    ax.set_xlabel("Type of historical cultural interaction", labelpad=8)
    ax.set_ylim(0.60, 0.95)
    ax.set_yticks([0.60, 0.70, 0.80, 0.90])
    ax.set_xlim(0.45, 5.55)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color="#E3E7EA", linewidth=0.55)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#30343A")
        ax.spines[side].set_linewidth(0.75)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")

    fig.subplots_adjust(left=0.10, right=0.99, bottom=0.24, top=0.96)
    for suffix, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(IMAGE_OUTPUT / f"five_interaction_types_vs_ci.{suffix}", dpi=dpi, facecolor="white")
    plt.close(fig)
    print(pd.DataFrame(results).to_string(index=False))


if __name__ == "__main__":
    main()
