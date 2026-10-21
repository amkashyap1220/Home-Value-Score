# Results

Run on 2026-10-21 with the method in [decisions.md](decisions.md), including its change log. The numbers come from `src/prices.py`, `src/extras.py` and `src/model.py`, and the full tables are in `output/`.

**About the model:** the main model controls for running costs and home age as well as the tax rate. Those controls were added after a first run without them, and were made the main model at Alex's request (see the change log). That breaks the pre-registration. The first run is reported at the end of this file and saved in `output/first_run.json`.

## Data

- **Prices:** Redfin zip code market tracker, All Residential. The latest period in the file ends 2026-05-31, so the 12-month window is **2025-06-01 to 2026-05-31**. It is made of the four non-overlapping 90-day periods ending in Aug 2025, Nov 2025, Feb 2026 and May 2026. Redfin hadn't refreshed the zip file since 2026-06-02 when it was pulled.
- **Running costs and home age** (`src/extras.py`):
  - **Home age:** 2026 minus the median year built (ACS B25035). The median zip's homes are about 52 years old.
  - **Home energy bill:** estimated mean monthly electricity plus natural gas bill (ACS B25132 and B25133, from bin midpoints). The median zip pays about $235 a month.
  - **Commuting fuel:** estimated yearly gasoline cost per worker = share who drive × mean commute time, converted to miles at 30 mph, × 2 trips × 250 workdays ÷ 25 mpg × the average pump price over the price window. EIA weekly regular gasoline: Chicago average for Illinois zips ($3.54), Midwest average for Indiana zips ($3.11). EIA publishes no Indiana or NW Indiana series. The median zip is about $930 a year.
- **Sample:** 338 of the 380 in-scope zips (300 IL, 38 IN). 42 were dropped, almost all for having fewer than 20 sales, and one for missing home age and cost data. They're listed in `output/excluded_zips.csv`. Some zips in the sample are missing one quality indicator (usually safety) and are flagged.

## Value model

`price_per_sqft = b0 + b1 * quality + b2 * tax_rate + b3 * home_age + b4 * home_energy_month + b5 * commute_fuel_year`, OLS, n = 338.

| Term | Coefficient | Std. error | p |
|---|---|---|---|
| Intercept | 317.4 | 35.7 | < 0.001 |
| Quality score (per point) | 1.88 | 0.24 | < 0.001 |
| Tax rate (per 1.0 = 100%) | 347 | 777 | 0.66 |
| Home age (per year) | 0.06 | 0.19 | 0.74 |
| Home energy bill (per $/month) | −0.41 | 0.10 | < 0.001 |
| Commuting fuel (per $/year) | −0.12 | 0.02 | < 0.001 |

R² = 0.41. The residual standard deviation is $56.3 per sq ft, so "significantly underpriced" means at least $56.3/sq ft below the prediction.

- **Quality** is the strongest term: each point on the 0–100 score adds about $1.90 per sq ft.
- **Energy bills and commuting fuel** both lower the price, as you'd expect. They're partly proxies, though. Energy bills grow with house size, and commuting fuel is built from commute time, which is also in the quality score (correlation about 0.6). So read their coefficients as associations, not as the value buyers place on gas or electricity.
- **Home age and the tax rate** add nothing measurable once the other terms are in.

## The value picks

Quality above the median (51.0) and price more than one standard deviation below the prediction. Most underpriced first:

| Zip | Place | Quality | $/sq ft | Model | Below by |
|---|---|---|---|---|---|
| 47951 | Kentland, IN | 52 | $92 | $206 | $114 |
| 60472 | Robbins, IL | 52 | $90 | $203 | $113 |
| 60064 | North Chicago, IL | 57 | $146 | $252 | $106 |
| 60433 | Joliet (east), IL | 64 | $158 | $253 | $95 |
| 47978 | Rensselaer, IN | 59 | $138 | $230 | $92 |
| 60444 | Mazon, IL | 58 | $147 | $234 | $86 |
| 60098 | Woodstock, IL | 68 | $184 | $258 | $73 |
| 46383 | Valparaiso, IN | 66 | $172 | $244 | $72 |
| 60030 | Grayslake, IL | 68 | $192 | $260 | $67 |
| 60173 | Schaumburg, IL | 67 | $231 | $296 | $65 |
| 60085 | Waukegan, IL | 52 | $172 | $236 | $64 |
| 60143 | Itasca, IL | 76 | $222 | $283 | $62 |
| 60450 | Morris, IL | 55 | $180 | $241 | $61 |
| 60176 | Schiller Park, IL | 73 | $219 | $278 | $60 |
| 46322 | Highland, IN | 57 | $166 | $224 | $59 |
| 60178 | Sycamore, IL | 57 | $182 | $240 | $58 |

12 are in Illinois and 4 in Indiana.

## Decision

| | Result | Rule |
|---|---|---|
| Value picks | **16** | at least 3 |
| **H1** | **Supported** | |

## Robustness checks

1. **Illinois only** (percentiles, model and thresholds rerun on 300 IL zips): 15 value picks, so the rule also says supported. R² rises to 0.51. Picks: Robbins, North Chicago, Mazon, Joliet 60433, Morris, Coal City, Chicago 60606, Itasca, Woodstock, Willow Springs, Schiller Park, Hinckley, Joliet 60435, Sycamore, Crystal Lake.
2. **Drop one indicator at a time:** 15 picks without schools, 22 without safety, 15 without commute, 13 without walkability. **7 of the 16 picks hold in at least 3 of the 4 runs**: Kentland, North Chicago, Joliet 60433, Rensselaer, Woodstock, Valparaiso 46383 and Schaumburg.
3. **Hand check**, below.

## Hand check: 10 most underpriced zips

| Zip | Place | Makes sense? |
|---|---|---|
| 46407 | Gary | Yes, in that it's cheap, but it isn't high quality (score 31). Long-term population loss and vacancy push prices far below anything the model knows about. |
| 47948 | Goodland | Partly. Rural, short commutes because people work locally, no crime data, 23 sales. Just under the quality median. |
| 46312 | East Chicago | Cheap and low quality. Industrial land and known soil contamination (the USS Lead Superfund site) aren't in the model. |
| 47951 | Kentland | Partly. It's a small rural county seat. Short commutes reflect local jobs, not access to a job market, and rural land is cheap everywhere. No crime data, 30 sales. |
| 60472 | Robbins | No. It's one of the region's most economically distressed suburbs. Its police department reported no 2025 or 2024 crime data, so its score leans on walkability (a dense street grid) and commute. Missing data flatters it. |
| 46402 | Gary | Same as 46407. |
| 60426 | Harvey | Low quality, and the town is in fiscal distress. Not a value pick. |
| 60064 | North Chicago | Partly. Its short commutes come largely from Naval Station Great Lakes, and its schools rank near the bottom. |
| 60433 | Joliet (east) | Partly. Joliet has one police department, so the east side gets the citywide crime rate, which is likely better than its own. Older housing stock. |
| 47978 | Rensselaer | Rural county seat. Good schools for Indiana and short commutes; no usable crime data. Plausibly cheap for what it is, but it's far from the Chicago job market. |

## Hand check: 10 most overpriced zips

Kenilworth 60043, Glencoe 60022, Winnetka 60093, Chicago 60614 (Lincoln Park), Wilmette 60091, Hinsdale 60521, Chicago 60647 (Logan Square), Lake Forest 60045, Chicago 60618 (Avondale/North Center) and Lake Village 46349.

Most make sense as places the model can't price. The North Shore suburbs and Hinsdale have top schools, large lots and (on the North Shore) the lake, which drive prices well beyond a 0–100 score, and their long commutes pull the score down. The Chicago zips get the same school and crime values as every Chicago zip (one district, one police agency), so the expensive north side looks like an average Chicago zip with a high price. Lake Village is the odd one: a low-quality rural zip with high estimated fuel and energy costs, so the model predicts only $57/sq ft. That's an extrapolation at the edge of the data, not a real finding.

## What this means

By the decision rule, **H1 is supported**: there are high-quality zips selling well below what the model predicts. The caveats:

- **The model changed after the first run.** See the change log. The first run also met the rule, so the yes doesn't depend on the change, but the list of picks does.
- **Short commutes reward rural towns** where people work locally. The commute indicator measures how long people actually commute, not how close a place is to jobs.
- **Missing safety data helps some zips**, such as Robbins, Kentland and Rensselaer, because their score is the average of the other three indicators.
- **About half the picks depend on the recipe.** 7 of 16 survive dropping an indicator, and two of those (North Chicago and Kentland) look like measurement artifacts on the hand check.

The most defensible picks for a buyer are suburban, have full data, and hold up under the checks: Woodstock and Joliet 60433 (robust to drop-one and in the Illinois-only run), Schaumburg 60173 (robust to drop-one), and Itasca and Sycamore (Illinois-only). These are good leads for a closer look, not proof that these places are undervalued.

## First run: quality and tax rate only

The model as pre-registered, on the same 338 zips: `price_per_sqft = b0 + b1 * quality + b2 * tax_rate`. R² = 0.25, residual SD = $63.5/sq ft, tax rate not significant (p = 0.77).

- 16 value picks, so it also met the decision rule.
- 9 of its 16 picks were in Indiana. Indiana zips sat about $61/sq ft below the line, and the tax-rate term didn't absorb Indiana's homestead tax cap. Adding running costs (cheaper gas and energy in Indiana) cut Indiana's picks to 4.
- 10 picks are in both runs: Kentland, Robbins, North Chicago, Joliet 60433, Rensselaer, Mazon, Woodstock, Valparaiso 46383, Grayslake and Highland. The first run's other picks were Munster, Chesterton, Dyer, Coal City, Griffith and Valparaiso 46385; the main model adds Schaumburg, Waukegan, Itasca, Morris, Schiller Park and Sycamore.

## Value map (post-hoc, 2026-10-21)

The post now uses a weighted value score that readers can change (method and reasons in the change log of [decisions.md](decisions.md); code in `src/value.py`). With the defaults (every quality factor weighted 1, price 50% of the score), the 20 value areas are:

- **Buying (338 zips):** led by Indiana suburbs such as Valparaiso, Chesterton, Munster, Dyer, Schererville and St. John.
- **Renting (347 zips):** 14 of the 20 are in Illinois.

Full lists: `output/value.json`, per-zip scores: `output/value.csv`.

## Target map (2026-10-21)

The weighted value score above was replaced by a target score (change log in [decisions.md](decisions.md)): each reader's ranking depends on their own targets and weights, so there is no single list to report. With the example targets (schools 50th percentile, 11 crimes per 1,000, 30-minute commute, walk index 11, homes 50 years old, $350,000 or $1,400 a month, all weights equal), the top 20 are middle-of-the-road suburbs such as Palos Heights, Hanover Park, Justice and Carpentersville for buyers, and Clarendon Hills, Woodridge and Justice for renters. The page now starts with different sample values (decisions.md). Full lists: `output/value.json`.
