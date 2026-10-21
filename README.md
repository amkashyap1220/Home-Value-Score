# Home Value Score (Chicago metro)

**Question:** are there high-quality zip codes in the Chicago metro where homes sell for less per square foot than their quality predicts, and are those zips mostly outside the places people usually recommend?

**Status:** method pre-registered in [docs/decisions.md](docs/decisions.md) on 2026-10-21, before any price data was downloaded. Data collection hasn't started yet.

## Method in short

1. Score each zip from 0 to 100 on quality: schools, safety, commute time and walkability, as equal-weighted percentile ranks.
2. Regress median price per square foot on the quality score and the property tax rate.
3. A zip is a **value pick** if its quality is above the metro median and its price is more than one standard deviation below what the model predicts.
4. Compare the value picks with a "word of mouth" list built from Niche's 2026 Best Places to Live rankings.

The full definitions, thresholds and the rule for accepting or rejecting the hypothesis are in [docs/decisions.md](docs/decisions.md). Race and ethnicity, and proxies for them, are not used anywhere.

## Sources

| Data | Source | URL | Pulled | License |
|---|---|---|---|---|
| Reputation list | Niche, 2026 Best Places to Live (IL, IN) | https://www.niche.com/places-to-live/search/best-places-to-live/s/illinois/ | 2026-10-21 | Niche terms of use; place names only |

More rows are added as each source is downloaded.

## Repo layout

```
data/raw/        downloads (not committed; re-fetch with the scripts in src/)
data/processed/  cleaned tables
notebooks/       exploration
src/             scripts for the final steps
output/          final scores (CSV/JSON) and the chart
docs/            pre-registration and notes
```

## Result

Not yet available.

## How to rerun

To be filled in once the scripts exist.
