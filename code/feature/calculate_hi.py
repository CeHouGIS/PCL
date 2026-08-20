#!/usr/bin/env python3
"""Recalculate raw and min-max-normalized Heterogeneity Index (HI)."""

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
FEATURE_DIR = ROOT / "data" / "features" / "PCL" / "spatiotemporal"
OUTPUT = ROOT / "data" / "features" / "HI_recalculated.csv"


def main():
    rows = []
    for path in sorted(FEATURE_DIR.glob("*.npy")):
        x = np.load(path, mmap_mode="r")
        if x.ndim != 2:
            raise ValueError(f"Expected a 2-D feature matrix, got {x.shape}: {path}")
        # Trace(Cov(X)) equals the sum of feature-wise sample variances.
        hi_raw = float(np.var(x, axis=0, ddof=1).sum())
        rows.append({"city": path.stem, "n_patches": len(x), "hi_raw": hi_raw})

    result = pd.DataFrame(rows)
    lo, hi = result.hi_raw.min(), result.hi_raw.max()
    result["hi_normalized"] = (result.hi_raw - lo) / (hi - lo)
    result = result.sort_values("hi_normalized", ascending=False)
    result.to_csv(OUTPUT, index=False)
    print(result.to_string(index=False))
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    main()
