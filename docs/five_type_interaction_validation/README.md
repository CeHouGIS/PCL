# Five cultural-homology interaction types

This analysis reorganizes the historical city-connection workbook into five
non-exclusive interaction layers:

1. colonial and imperial cultural transmission;
2. religious and civilizational diffusion;
3. planning and architectural diffusion;
4. shared official language; and
5. trade-mediated cultural exchange.

The workbook retains the source evidence and classification rules. A city pair
may belong to multiple types. A value of zero means that no qualifying record
is present in the current evidence base; it does not establish historical
absence.

The accompanying figure contains one panel and one CI distribution for each
interaction type. It is descriptive: categories overlap and should not be
treated as independent samples.

## Reproduce

```bash
python3 code/five_type_interaction_validation/build_five_type_layers.py
python3 code/five_type_interaction_validation/plot_five_type_ci.py
```

The raw supplementary workbook remains excluded from Git. Aggregate summaries
are stored in `data/results/five_type_interaction_validation/`, and publication
figures are stored in `images/five_type_interaction_validation/`.
