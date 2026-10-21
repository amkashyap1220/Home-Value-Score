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

All entries below were made on 2026-10-21, during step 2 (quality and tax data), **before any price data was downloaded**.

**Change: property tax rate uses aggregates instead of medians.** The pre-registered measure was median taxes paid (B25103) ÷ median home value (B25077). In the 2020–2024 ACS, B25103 is top-coded at "$10,000 or more", and 42 of the 380 in-scope zips hit that cap, which would understate the tax rate exactly in the high-tax suburbs. The tax rate is now aggregate real estate taxes paid (B25090) ÷ aggregate value of owner-occupied homes (B25082), same vintage. Where the median isn't top-coded the two measures correlate at 0.93. The median version is kept in `data/processed/acs.csv` as `tax_rate_median`.

**Change: crime data-quality rule, chosen by Alex.** A police agency's 2025 data is treated as unusable if it covers fewer than 12 months, or if its 2025 offense total is under half of its 2024 total with at least 50 offenses in 2024 (Westchester, Libertyville and Northlake: their 2025 reports cover all 12 months but are far below 2024, which points to incomplete NIBRS submissions rather than a real drop; the median agency fell 14%). For those agencies the 2024 rate is used when 2024 covers all 12 months; otherwise the safety indicator is missing. This uses 2024 for 8 zips. Reason: keep as many zips as possible with a real crime value, at the cost of mixing two years in one indicator.

**Post-hoc addition (2026-10-21, after the step 3 results were seen): extended model with running costs and home age.** At Alex's request, a second model adds three controls: median home age (ACS B25035), the estimated monthly home electricity and natural gas bill (ACS B25132, B25133), and the estimated yearly gasoline cost of commuting (drive share × commute time × EIA pump price). It uses the same sample, percentiles and thresholds. Reason: a buyer pays these costs on top of the price, and home age was listed above as an unmeasured confounder. Because this was added after the results were seen, **the pre-registered model stays the primary test and decides H1**. The extended model is reported as a labeled secondary analysis. Details are in `src/extras.py` and `docs/results.md`.

**Change (2026-10-21, after all results were seen): the model with running costs and home age becomes the main model.** Alex asked for the extended model above to be the main ranking instead of a secondary analysis. The reason: a buyer judges value on what a home costs to own and run, not only its sale price, so energy bills, commuting fuel and home age belong in the definition of value from the start. The value model is now
`price_per_sqft = b0 + b1 * quality + b2 * tax_rate + b3 * home_age + b4 * home_energy_month + b5 * commute_fuel_year`.
Everything else is unchanged: the sample filter (plus one zip dropped for missing home age or cost data, 338 zips), the quality score, the thresholds, the reputation list, the decision rule and the robustness checks, which are rerun on this model.

**This breaks the pre-registration**, and the write-up says so. The controls were chosen after the first run's results were seen. The first run (quality and tax rate only) is still computed by `src/model.py` and saved in `output/first_run.json`. It also met the decision rule: 16 value picks, 11 not on the reputation list.

**Change (2026-10-21, after all results were seen): the post uses a weighted value score with reader weights, not the regression.** Alex asked for the post to be an interactive tool: sliders set the weights in the value equation and a map shows the value areas, for buyers and for renters, with optional targets and a second person. The property tax rate, energy bills and commuting fuel are dropped; home age becomes a weighted factor. Reason: the point of the project is that "value" depends on what the buyer cares about, and a weighted score lets each reader set that, while the regression residual can't take a price weight. The new method (`src/value.py`, `js/chicago-home-value-model.js` on the site):

- Six percentile ranks within the sample, higher is better: schools, safety, commute, walkability, newer homes (median year built, B25035), and low price (median price per sq ft for buyers; median gross rent, ACS B25064, for renters).
- `quality = weighted mean of the first five` (default weight 1 each). A missing indicator now counts as 50 instead of being skipped, so a zip with no crime data isn't scored on its other indicators alone (the hand check flagged Robbins for this).
- `value = (1 - price share) * quality + price share * low price`, default price share 50%.
- Value areas: the 20 highest value scores among zips with above-median quality (the pre-registered "high quality" rule).
- Targets: a zip that meets a reader's target scores 100 on that factor; one that misses scores `100 * percentile / target percentile`. A buyer's budget is compared with the median sale price.
- Two people: "best for both" ranks by the lower of the two value scores, among zips above both quality medians.
- Samples: buyers as before (at least 20 sales, a price per sq ft, at most one missing quality indicator, a home age: 338 zips). Renters: a median gross rent and at least 100 renter-occupied homes (B25003), same other rules (347 zips). ACS rent is used rather than Zillow's ZORI because ZORI covers only 229 of the 380 zips; the two correlate at 0.75.
- The reputation comparison is now "how many of the 20 value areas are on the list".

These choices (the 50% default, the top 20, the 100-renter minimum, missing = 50) were made after the regression results were seen, so this is not a pre-registered test. The pre-registered test and its result (H1 supported, `output/first_run.json`, `docs/results.md`) stay as they are. With the defaults, 7 of the 20 buyer value areas are on the reputation list, all of them from the Indiana list; none of the Illinois top 20 is in them. For renters it's 5 of 20.

Clarifications. These fill in details the plan didn't specify; none changes a definition above.

- **Vintages.** ACS 5-year 2020–2024 (latest on the pull date). Crime: 2025, the latest full year in the FBI Crime Data Explorer. Schools: Illinois 2025 Report Card (2024–25 tests, the latest published); Indiana spring 2026 ILEARN and SAT.
- **Zip population shares** (scope, police agency, reputation list) are computed from 2020 Census block populations, using the Census ZCTA-to-block relationship file and the 2020 block assignment files. The Census ZCTA-to-place relationship file only has land area, not population.
- **Schools.** For each district, proficiency is the mean of % proficient in ELA and in math, in two bands: grades 3–8 (IL IAR, IN ILEARN) and high school (IL grade 11 ACT, IN grade 11 SAT). Each band is ranked within its own state, among the state's geographic districts with results. A block takes its grades 3–8 percentile from its unified or elementary district and its high school percentile from its unified or secondary district, and its school value is the mean of the two. The zip value is the land-area-weighted mean of its blocks. Chicago Public Schools is one district, so every Chicago zip gets the same school value; this is a limitation of district-level data.
- **Safety.** "The place holding most of its population" is the largest single population group among the incorporated places in the zip and the unincorporated land of each county. Places with no agency in the FBI data leave the indicator missing. The list is in `docs/data_notes.md`.
- **Walkability.** The EPA index is published for 2010 block groups. Each 2020 block is linked to the 2010 block it overlaps most (Census 2010–2020 block relationship files), and the zip value is weighted by 2020 block population.
- **Reputation list.** "Place" includes Census-designated places (needed for Lakes of the Four Seasons). The place with the largest population in the zip decides, even if most of the zip is outside any place. Chicago neighborhoods use the City's "Boundaries – Neighborhoods" layer.
