# Global city-level Covered Index activation

This figure maps a city-level summary of the pairwise Covered Index (CI) for all 130 cities. Because CI is defined between two cities and is asymmetric, the mapped activation for city $i$ is based on the symmetric pair score

$$
CI^{\mathrm{sym}}_{ij,K}=\frac{CI_{i\rightarrow j,K}+CI_{j\rightarrow i,K}}{2},
$$

and is calculated as

$$
A_i=\frac{1}{3}\sum_{K\in\{200,500,1000\}}
\left(\frac{1}{129}\sum_{j\ne i}CI^{\mathrm{sym}}_{ij,K}\right).
$$

Thus, a high activation indicates that a city's morphology has high average affinity with the global sample. It is a descriptive network summary, not a new pairwise CI definition and not evidence that the city influenced all other cities.

## Run

The script reads the existing derived CI and city-coordinate tables. It uses the Natural Earth boundary file already required by `cultural_validation`; external raw boundary data are not committed.

```bash
python3 code/global_ci_activation/plot_global_ci_activation.py
```

Dependencies are Python 3, NumPy, pandas, Matplotlib, pyshp and Liberation Sans. Outputs include publication-ready PDF, 600 dpi PNG and 600 dpi TIFF maps. The generated CSV is a derived city-level audit table rather than raw input data.

## Outputs

- `images/global_ci_activation/global_ci_activation_map.png`
- `images/global_ci_activation/global_ci_activation_map.pdf`
- `images/global_ci_activation/global_ci_activation_map.tif`
- `data/results/global_ci_activation/city_ci_activation_summary.csv`
