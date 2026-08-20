# K=1,000 validation figures

This directory provides publication-ready figures restricted to the final prototype resolution, $K=1{,}000$:

- `ci_vs_cultural_distance_nature_k1000`: standalone cultural-distance validation;
- `combined_validation_k1000`: combined panels for direct inter-city ties and internal morphology concordance.
- `combined_cultural_direct_morphology_k1000`: a unified three-panel figure containing cultural proximity, direct inter-city ties and morphology-based concordance.
- `combined_external_validation_k1000`: a unified $2\times2$ figure containing cultural distance, direct historical ties, shared historical regimes and morphology-based concordance.

The plotting script reads the existing analysis and result tables, so all statistics match the previously reported full-resolution analyses. It does not overwrite the original three-resolution figures.

```bash
python3 code/k1000_validation_figures/plot_k1000_validation.py
```

Each figure is exported as PDF, 600 dpi PNG and 600 dpi TIFF using Liberation Sans, an open Arial-compatible typeface.
