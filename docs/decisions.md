# Pre-registration: hypotheses, definitions and thresholds

This file is committed **before any price data is downloaded**. Its commit date shows the method was set before the results were seen. Any later change is added to the change log at the bottom with the date and a reason. Nothing above the change log is edited after the first commit.

Locked on: 2026-10-21

## Research question

Are there high-quality zip codes in the Chicago metro where homes sell for less per square foot than their quality predicts, and are those zips mostly outside the commonly recommended areas?

## Hypotheses

- **H1:** Among zip codes in the Chicago metro (13 counties in Illinois and Indiana), some zips with above-median quality scores sell for significantly less per square foot than their quality and property taxes predict, and most of these undervalued zips are **not** on the reputation list.
- **H0:** Price per square foot is explained by quality and taxes, with no meaningful set of high-quality, underpriced zips; or the underpriced zips are mostly on the reputation list.

## Decision rule (set before analysis)

Call a zip a **value pick** if it is both high quality and significantly underpriced (definitions below).

- **H1 supported:** at least 3 value picks, and more than half of them are not on the reputation list.
- **H1 rejected:** fewer than 3 value picks, or half or more of them are on the reputation list.

The decision uses the main test only (all 13 counties). The robustness checks are reported next to it but do not change the decision.

## Scope

- **Area:** Chicago–Naperville–Elgin, IL-IN Metropolitan Statistical Area, 2023 OMB definition, 13 counties.
  - Illinois: Cook, DeKalb, DuPage, Grundy, Kane, Kendall, Lake, McHenry, Will
  - Indiana: Jasper, Lake, Newton, Porter
  - Kenosha County, WI is its own metro since 2023 and is out of scope.
- **Unit:** zip code, measured as a Census ZIP Code Tabulation Area (ZCTA). A ZCTA is in scope if more than half of its population (2020 Census) lives in the 13 counties.
- **Buyer:** someone buying a home to live in, not a rental investor.

## Sample filter

- **Minimum sales:** a zip needs **at least 20 sales** in the 12-month price window. Zips below that are dropped.
- A zip is also dropped if it is missing the price, the tax rate, or two or more of the four quality indicators. Every dropped zip is listed with its reason in `output/excluded_zips.csv`.

## Price

- **Source:** Redfin Data Center, zip code market tracker, property type "All Residential".
- **Window:** the 12 most recent months available on the download date.
- **Price per sq ft:** the median sale price per square foot over that window. Redfin publishes zip data as rolling periods, not raw sales, so if a single 12-month median isn't available, the price is the homes-sold-weighted average of the medians of the non-overlapping periods that make up the 12 months. This is an approximation of a true 12-month median, and the post will say so.
- **Sales count:** total homes sold over the same periods.

## Quality score (0 to 100)

The equal-weighted average of four percentile ranks. Each percentile is computed across the zips in the final sample, so 100 is best in the sample and 0 is worst.

| Indicator | Measure | Direction |
|---|---|---|
| Schools | District test proficiency, converted to a percentile **within its own state** first (Illinois and Indiana use different tests). Districts are mapped to a zip with an area-weighted average, using the Census school district boundaries. | higher is better |
| Safety | Violent plus property crimes per 1,000 residents for the police agency covering the zip, latest full year in the FBI Crime Data Explorer. A zip is covered by the municipal police department of the place holding most of its population, or by the county sheriff if that area is unincorporated. | lower is better |
| Commute | Mean travel time to work for workers who don't work from home, ACS 5-year, by ZCTA | shorter is better |
| Walkability | EPA National Walkability Index, population-weighted average of block groups to the ZCTA | higher is better |

- **Missing indicators:** if one indicator is missing for a zip (for example, its police agency doesn't report to the FBI), the score is the average of the other three, and the zip is flagged. Two or more missing means the zip is dropped. Missing agencies are listed in the README.
- **Not used in the score:** anything based on price (price growth, days on market, home values). Those would make the test circular. They may be shown as context only.
- **Not used anywhere:** race, ethnicity, or proxies for them. This follows fair-housing practice and avoids repeating the logic of redlining. The post will say so.
- **"High quality"** means a quality score above the median of the final sample.

## Property tax rate

- **Measure:** effective property tax rate = median real estate taxes paid ÷ median value of owner-occupied homes, by ZCTA, from the ACS 5-year estimates (tables B25103 and B25077), same vintage as the commute data.
- **Why this measure:** it records the taxes owners actually pay, so it already reflects Indiana's 1% homestead cap and Illinois' county equalization, and it is measured the same way in all 13 counties. County assessor/treasurer rates and Indiana DLGF rates are used only to sanity-check it for a sample of zips.

## Value model

- Ordinary least squares on the final sample:
  `price_per_sqft = b0 + b1 * quality_score + b2 * tax_rate + error`
- **Residual** = actual price per sq ft minus predicted.
- **"Significantly underpriced"** means a residual more than 1 standard deviation below zero, using the standard deviation of the residuals in the sample.
- R², the coefficients and their standard errors will be reported.

## Reputation list ("word of mouth")

- **Source:** Niche, "Best Places to Live", **2026 rankings** (the latest year available), pulled on **2026-10-21**.
- **Illinois:** the top 20 of "2026 Best Places to Live in Illinois":
  1. Clarendon Hills, 2. Naperville, 3. Riverside, 4. Buffalo Grove, 5. Kildeer, 6. Lincolnshire, 7. Printers Row (Chicago), 8. Western Springs, 9. Long Grove, 10. La Grange, 11. Hinsdale, 12. Vernon Hills, 13. West Loop (Chicago), 14. River Forest, 15. Evanston, 16. Loop (Chicago), 17. Northbrook, 18. Bannockburn, 19. Wilmette, 20. River North (Chicago)
- **Indiana:** the entries in the top 50 of "2026 Best Places to Live in Indiana" that are in the four Indiana metro counties:
  Munster (#10), Chesterton (#37), Dyer (#40), Valparaiso (#43), Lakes of the Four Seasons (#45), St. John (#47), Schererville (#49).
  The cutoff is 50 because the Indiana top 20 contains only one Chicago-area place (Munster), which would leave Northwest Indiana with almost no reputation list. 50 is a round cutoff chosen from the ranking alone, before any price data was seen.
- **Note:** the project brief quoted the 2025 Illinois list as a reference. The 2026 list above replaces it, since the rule is "latest year available". The two lists share 16 of 20 places.
- **Mapping places to zips:** Census 2020 ZCTA-to-place relationship file. A zip counts as on the list if the place holding the largest share of the zip's population is on the list.
- **Mapping Chicago neighborhoods to zips:** the Census files don't cover neighborhoods, so a zip counts as on the list if the largest share of its area inside Chicago falls in a listed neighborhood, using the City of Chicago's neighborhood boundaries.
- The final place-to-zip mapping is saved in `data/processed/reputation_zips.csv`.

## Robustness checks (reported, do not change the decision)

1. **Illinois only:** rerun the full test (percentiles, model, thresholds) on Illinois zips only, because Indiana's homestead tax cap could make Indiana look artificially cheap.
2. **Drop one indicator at a time:** rebuild the quality score four times, each time without one indicator. A value pick counts as robust if it stays a value pick in at least 3 of the 4 runs.
3. **Hand check:** look at the 10 most underpriced and 10 most overpriced zips and write down whether each one makes sense, and any reason the model might be missing (for example a flood zone, airport noise, or mostly new construction).

## Known confounders and limitations

- Property taxes are in the model; Indiana caps homestead taxes at 1% of assessed value and Illinois doesn't.
- Not measured: flood zones, airport noise, HOA fees, home age and condition, lot size.
- A zip averages over very different streets.
- Some police agencies don't report to the FBI, or report only part of the year.
- School district boundaries don't match zip boundaries, so the area-weighted school score is an approximation.

## Change log

Any change after the first commit goes here: date, what changed, and why.

- _none yet_
