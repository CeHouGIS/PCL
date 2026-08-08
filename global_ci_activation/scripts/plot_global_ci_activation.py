#!/usr/bin/env python3
"""Plot the city-level global activation of the Covered Index."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapefile
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, Normalize


ROOT = Path(__file__).resolve().parents[2]
CI_FILE = ROOT / "cultural_validation" / "output" / "city_pair_ci.csv"
CITY_FILE = ROOT / "cultural_validation" / "output" / "city_country_mapping.csv"
WORLD_FILE = (
    ROOT
    / "cultural_validation"
    / "external"
    / "natural_earth"
    / "ne_10m_admin_0_countries.shp"
)
OUTPUT = ROOT / "global_ci_activation" / "output"

FONT_DIR = Path("/usr/share/fonts/truetype/liberation2")
font_files = sorted(FONT_DIR.glob("LiberationSans-*.ttf"))
if not font_files:
    raise RuntimeError("Install Liberation Sans: apt install fonts-liberation2")
for path in font_files:
    font_manager.fontManager.addfont(path)

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Liberation Sans"],
    "font.size": 7,
    "font.weight": "bold",
    "axes.linewidth": 0.65,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def city_activation(ci):
    """Mean symmetric CI with all other cities, averaged across K values."""
    long = pd.concat(
        [
            ci[["k", "city_1", "ci_symmetric"]].rename(
                columns={"city_1": "city"}
            ),
            ci[["k", "city_2", "ci_symmetric"]].rename(
                columns={"city_2": "city"}
            ),
        ],
        ignore_index=True,
    )
    by_k = (
        long.groupby(["k", "city"], as_index=False)
        .agg(activation=("ci_symmetric", "mean"), n_partners=("ci_symmetric", "size"))
    )
    if not (by_k["n_partners"] == 129).all():
        raise ValueError("Every city must have CI values for exactly 129 partners per K")
    activation = (
        by_k.groupby("city", as_index=False)
        .agg(
            mean_ci_activation=("activation", "mean"),
            min_ci_activation=("activation", "min"),
            max_ci_activation=("activation", "max"),
        )
    )
    return activation


def split_at_dateline(points):
    """Split polygon rings where consecutive longitudes cross the map seam."""
    points = np.asarray(points, dtype=float)
    if len(points) < 3:
        return []
    breaks = np.where(np.abs(np.diff(points[:, 0])) > 180)[0] + 1
    return [part for part in np.split(points, breaks) if len(part) >= 3]


def simplify_ring(points, tolerance=0.12):
    """Radially simplify a ring at a tolerance suited to a global map."""
    points = np.asarray(points, dtype=float)
    if len(points) < 3 or np.ptp(points, axis=0).max() < 0.06:
        return None
    keep = [0]
    last = points[0]
    for index in range(1, len(points) - 1):
        latitude_scale = np.cos(np.radians((points[index, 1] + last[1]) / 2))
        squared_distance = (
            ((points[index, 0] - last[0]) * latitude_scale) ** 2
            + (points[index, 1] - last[1]) ** 2
        )
        if squared_distance >= tolerance ** 2:
            keep.append(index)
            last = points[index]
    keep.append(len(points) - 1)
    simplified = points[keep]
    return simplified if len(simplified) >= 3 else None


def draw_world(ax, shapefile_path):
    reader = shapefile.Reader(str(shapefile_path))
    for shape in reader.shapes():
        bounds = list(shape.parts) + [len(shape.points)]
        for start, stop in zip(bounds[:-1], bounds[1:]):
            for ring in split_at_dateline(shape.points[start:stop]):
                ring = simplify_ring(ring)
                if ring is None:
                    continue
                ax.fill(
                    np.radians(ring[:, 0]),
                    np.radians(ring[:, 1]),
                    facecolor="#ECECEA",
                    edgecolor="#B8BAB8",
                    linewidth=0.24,
                    zorder=1,
                )


def main():
    if not WORLD_FILE.exists():
        raise FileNotFoundError(
            f"Natural Earth boundary file not found: {WORLD_FILE}. "
            "See cultural_validation/README.md for the external-data setup."
        )

    ci = pd.read_csv(CI_FILE)
    cities = pd.read_csv(CITY_FILE)
    activation = city_activation(ci)
    mapped = cities.merge(activation, on="city", how="left", validate="one_to_one")
    if len(mapped) != 130:
        raise ValueError(f"Expected 130 mapped cities, found {len(mapped)}")

    cmap = LinearSegmentedColormap.from_list(
        "ci_activation",
        ["#DDE9EE", "#A9C9D2", "#62A6B1", "#177C83", "#083E4B"],
    )
    norm = Normalize(vmin=0.66, vmax=0.82, clip=True)

    fig = plt.figure(figsize=(7.09, 3.72), facecolor="white")
    ax = fig.add_subplot(111, projection="mollweide")
    ax.set_position([0.035, 0.18, 0.93, 0.69])
    ax.set_facecolor("#FAFAF8")
    ax.set_rasterization_zorder(2)
    draw_world(ax, WORLD_FILE)

    longitude = np.radians(mapped["longitude"].to_numpy())
    latitude = np.radians(mapped["latitude"].to_numpy())
    values = mapped["mean_ci_activation"].to_numpy()
    ax.scatter(
        longitude,
        latitude,
        s=29,
        c="white",
        linewidths=0,
        alpha=0.95,
        zorder=3,
    )
    points = ax.scatter(
        longitude,
        latitude,
        s=20,
        c=values,
        cmap=cmap,
        norm=norm,
        edgecolors="#26343A",
        linewidths=0.28,
        alpha=0.96,
        zorder=4,
    )

    ax.set_longitude_grid(30)
    ax.set_latitude_grid(30)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.grid(True, color="#D9DCDA", linewidth=0.32, alpha=0.75, zorder=0)
    ax.spines["geo"].set_edgecolor("#858A89")
    ax.spines["geo"].set_linewidth(0.60)

    fig.text(
        0.044,
        0.955,
        "Global city-level Covered Index activation",
        fontsize=10.2,
        fontweight="bold",
        ha="left",
        va="top",
        color="#202629",
    )
    fig.text(
        0.044,
        0.918,
        "Mean symmetric CI across 129 partner cities and K = 200, 500 and 1,000",
        fontsize=7.0,
        fontweight="bold",
        ha="left",
        va="top",
        color="#596166",
    )
    fig.text(
        0.955,
        0.918,
        "130 cities",
        fontsize=7.0,
        fontweight="bold",
        ha="right",
        va="top",
        color="#596166",
    )

    color_ax = fig.add_axes([0.315, 0.085, 0.37, 0.026])
    colorbar = fig.colorbar(points, cax=color_ax, orientation="horizontal")
    colorbar.set_label("Mean Covered Index", fontsize=7.5, fontweight="bold", labelpad=3)
    colorbar.set_ticks([0.66, 0.70, 0.74, 0.78, 0.82])
    colorbar.ax.tick_params(labelsize=6.8, width=0.55, length=2.3, pad=2)
    for label in colorbar.ax.get_xticklabels():
        label.set_fontweight("bold")
    colorbar.outline.set_edgecolor("#5F6668")
    colorbar.outline.set_linewidth(0.55)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for suffix, dpi in (("pdf", None), ("png", 600), ("tif", 600)):
        fig.savefig(
            OUTPUT / f"global_ci_activation_map.{suffix}",
            dpi=dpi,
            facecolor="white",
        )
    plt.close(fig)

    summary = mapped[
        [
            "city",
            "iso3",
            "country",
            "longitude",
            "latitude",
            "mean_ci_activation",
            "min_ci_activation",
            "max_ci_activation",
        ]
    ].sort_values("mean_ci_activation", ascending=False)
    summary.to_csv(OUTPUT / "city_ci_activation_summary.csv", index=False)


if __name__ == "__main__":
    main()
