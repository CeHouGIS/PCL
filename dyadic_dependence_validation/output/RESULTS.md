# Results

## Dependence diagnostics

| `K` | Geographic Spearman `r_s` | Geographic `P_perm` | Same-country `Delta CI` | Same-country `P_perm` |
|---:|---:|---:|---:|---:|
| 200 | -0.2122 | 0.0001 | 0.1058 | 0.0001 |
| 500 | -0.2079 | 0.0001 | 0.1082 | 0.0001 |
| 1,000 | -0.1793 | 0.0001 | 0.1031 | 0.0001 |

At all prototype resolutions, CI contains strong geographic and same-country structure. These are dependence diagnostics, not evidence that the city pairs satisfy an i.i.d. assumption.

## Shared-city dependence

| `K` | Source-city `R^2` | Target-city `R^2` | Source + target `R^2` | Source + target adjusted `R^2` |
|---:|---:|---:|---:|---:|
| 200 | 0.2041 | 0.2657 | 0.4719 | 0.4636 |
| 500 | 0.1624 | 0.2935 | 0.4581 | 0.4497 |
| 1,000 | 0.1629 | 0.2988 | 0.4636 | 0.4553 |

The substantial explained variance shows that observations sharing the same source or target city are systematically related. The asymmetry between source and target effects is also consistent with CI being directional before symmetrization.

## Controlled historical associations

Each historical layer was tested in a separate double-semi-partialling MRQAP model with log geographic distance and same-country status as covariates.

| Layer | `K` | Standardized `beta` | Adjusted CI difference | One-sided `P_MRQAP` | Model `R^2` |
|:---|---:|---:|---:|---:|---:|
| Direct tie | 200 | 0.0206 | 0.0030 | 0.2902 | 0.1423 |
| Direct tie | 500 | 0.0329 | 0.0046 | 0.1831 | 0.1450 |
| Direct tie | 1,000 | 0.0339 | 0.0046 | 0.1730 | 0.1313 |
| Shared regime | 200 | 0.0596 | 0.0086 | 0.0254 | 0.1452 |
| Shared regime | 500 | 0.0686 | 0.0096 | 0.0121 | 0.1484 |
| Shared regime | 1,000 | 0.0691 | 0.0093 | 0.0122 | 0.1347 |

Shared regime is consistently significant across all three prototype resolutions. Direct tie is consistently positive but does not remain significant after the geographic and national controls.

## Reviewer-ready interpretation

The results support the methodological point that strict i.i.d. inference is unsuitable, rather than showing that independence holds. They also provide a qualified substantive conclusion: broad shared historical regimes retain a robust association with CI beyond geographic proximity and national context, while the more specific direct-tie layer does not provide independent evidence after those controls.
