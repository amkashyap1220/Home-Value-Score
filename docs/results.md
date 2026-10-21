# Results (step 3)

Run on 2026-10-21 with the method in [decisions.md](decisions.md). The numbers come from `src/prices.py` and `src/model.py`, and the full tables are in `output/`.

## Data

- **Prices:** Redfin zip code market tracker, All Residential. The latest period in the file ends 2026-05-31, so the 12-month window is **2025-06-01 to 2026-05-31**. It is made of the four non-overlapping 90-day periods ending in Aug 2025, Nov 2025, Feb 2026 and May 2026. Redfin hadn't refreshed the zip file since 2026-06-02 when it was pulled.
- **Sample:** 339 of the 380 in-scope zips (301 IL, 38 IN). 41 were dropped, almost all for having fewer than 20 sales. They're listed in `output/excluded_zips.csv`. 20 zips in the sample are missing one quality indicator (usually safety) and are flagged.

## Value model

`price_per_sqft = b0 + b1 * quality + b2 * tax_rate`, OLS, n = 339.

| Term | Coefficient | Std. error | p |
|---|---|---|---|
| Intercept | 88.8 | 16.2 | < 0.001 |
| Quality score (per point) | 2.62 | 0.25 | < 0.001 |
| Tax rate (per 1.0 = 100%) | −200 | 668 | 0.77 |

R² = 0.25. The residual standard deviation is $63.5 per sq ft, so "significantly underpriced" means at least $63.5/sq ft below the prediction. The quality score explains about a quarter of the variation in price. The tax rate adds nothing measurable.

## Pre-registered decision

| | Result | Rule |
|---|---|---|
| Value picks (quality above the median of 51.0 and residual below −1 SD) | **16** | at least 3 |
| Picks not on the reputation list | **11 of 16 (69%)** | more than half |
| **H1** | **Supported** | |

The 16 value picks, most underpriced first: Robbins 60472, Kentland 47951, Rensselaer 47978, Joliet 60433, Mazon 60444, North Chicago 60064, Valparaiso 46383\*, Munster 46321\*, Chesterton 46304\*, Woodstock 60098, Dyer 46311\*, Coal City 60416, Highland 46322, Grayslake 60030, Griffith 46319, Valparaiso 46385\* (\* = on the reputation list).

## Robustness checks

1. **Illinois only** (percentiles, model and thresholds rerun on 301 IL zips): 11 value picks, none on the reputation list, so the rule also says supported. R² rises to 0.33. Picks: Robbins, North Chicago, Mazon, Coal City, Joliet 60433, Willow Springs, Itasca, Schiller Park, Morris, Woodstock, Hinckley.
2. **Drop one indicator at a time:** 19 picks without schools, 20 without safety, 17 without commute, 8 without walkability. Only **4 of the 16 picks hold in at least 3 of the 4 runs**: Kentland, Rensselaer, Joliet 60433 and North Chicago. The rest depend on which indicators are included.
3. **Hand check**, below.

## Hand check: 10 most underpriced zips

| Zip | Place | Makes sense? |
|---|---|---|
| 60472 | Robbins | No. It's one of the region's most economically distressed suburbs. Its police department reported no 2025 or 2024 crime data, so its score leans on walkability (a dense street grid) and commute. Missing data flatters it. |
| 47951 | Kentland | Partly. It's a small rural county seat. Short commutes reflect local jobs, not access to a job market, and rural land is cheap everywhere. Only 30 sales. |
| 46407 | Gary | Yes, in that it's cheap, but it isn't high quality (score 31). Long-term population loss and vacancy push prices far below anything the model knows about. |
| 46402 | Gary | Same as 46407. |
| 47948 | Goodland | Same as Kentland: rural, short commutes, no crime data, 23 sales. |
| 46312 | East Chicago | Cheap and low quality. Industrial land and known soil contamination (the USS Lead Superfund site) aren't in the model. |
| 47978 | Rensselaer | Rural county seat. Good schools for Indiana, short commutes and Indiana's tax cap; no usable crime data. Plausibly cheap for what it is, but it's far from the Chicago job market. |
| 60426 | Harvey | Low quality, and the town is in fiscal distress. Not a value pick. |
| 60433 | Joliet (east) | Partly. Joliet has one police department, so the east side gets the citywide crime rate, which is likely better than its own. Older housing stock. |
| 60444 | Mazon | Small rural village with 25 sales. Its 0 reported crimes is a tiny-agency effect. |

## Hand check: 10 most overpriced zips

Kenilworth 60043, Chicago 60614 (Lincoln Park), 60601 (Loop), Glencoe 60022, Chicago 60657 (Lakeview), 60647 (Logan Square), 60602 (Loop), 60607 (West Loop), 60622 (Wicker Park) and 60618 (Avondale/North Center).

These all make sense as places the model can't price. Eight are in Chicago, where every zip gets the same school and crime value (one district, one police agency). That makes the expensive north side look like an average Chicago zip with a high price. Kenilworth and Glencoe are lakefront suburbs with top schools, where large lots and the lake drive prices well beyond what a 0–100 score can capture, and their long commutes pull their score down.

## What this means

By the rule set before the data was seen, **H1 is supported**: there are high-quality zips selling well below what the model predicts, and most of them aren't on the reputation list. But the hand check and the drop-one test show the result is fragile, and it should be described that way:

- **Indiana drives much of it.** Indiana zips sit $61/sq ft below the line on average, and 9 of the 16 picks are in Indiana. The tax-rate term was supposed to absorb Indiana's tax cap, but it doesn't (the coefficient isn't distinguishable from zero), so part of the "underpricing" is just "Indiana". The Illinois-only rerun still finds picks, which is the strongest evidence for H1.
- **Short commutes reward rural towns** where people work locally. The commute indicator measures how long people actually commute, not how close a place is to jobs.
- **Missing safety data helps some zips**, such as Robbins and Kentland, because their score is the average of the other three indicators.
- **Only 4 picks are robust** to dropping an indicator, and two of those (North Chicago, which has a short commute because it includes Naval Station Great Lakes, and Kentland) look like measurement artifacts on the hand check.

The most defensible picks for a buyer are the suburban ones that hold up in the Illinois-only run and have full data: Woodstock, Coal City, Itasca, Willow Springs and Joliet 60433. These are good leads for a closer look, not proof that these places are undervalued.
