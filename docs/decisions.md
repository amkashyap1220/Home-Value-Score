# Pre-registration: hypotheses, definitions and thresholds

This file was committed **before any price data was downloaded**. Its commit date shows the method was set before the results were seen. Later changes are added to the change log at the bottom with the date and a reason. One exception: on 2026-10-21, at Alex's request, the comparison with an outside "best places" ranking was removed from this file, the code and the outputs (see the change log); the original text is in the git history.

Locked on: 2026-10-21

## Research question

Are there high-quality zip codes in the Chicago metro where homes sell for less per square foot than their quality predicts?

## Hypotheses

- **H1:** Among zip codes in the Chicago metro (13 counties in Illinois and Indiana), some zips with above-median quality scores sell for significantly less per square foot than their quality and property taxes predict.
- **H0:** Price per square foot is explained by quality and taxes, with no meaningful set of high-quality, underpriced zips.

## Decision rule (set before analysis)

Call a zip a **value pick** if it is both high quality and significantly underpriced (definitions below).

- **H1 supported:** at least 3 value picks.
- **H1 rejected:** fewer than 3 value picks.

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
Everything else is unchanged: the sample filter (plus one zip dropped for missing home age or cost data, 338 zips), the quality score, the thresholds, the decision rule and the robustness checks, which are rerun on this model.

**This breaks the pre-registration**, and the write-up says so. The controls were chosen after the first run's results were seen. The first run (quality and tax rate only) is still computed by `src/model.py` and saved in `output/first_run.json`. It also met the decision rule: 16 value picks.

**Change (2026-10-21, after all results were seen): the post uses a weighted value score with reader weights, not the regression.** Alex asked for the post to be an interactive tool: sliders set the weights in the value equation and a map shows the value areas, for buyers and for renters, with optional targets and a second person. The property tax rate, energy bills and commuting fuel are dropped; home age becomes a weighted factor. Reason: the point of the project is that "value" depends on what the buyer cares about, and a weighted score lets each reader set that, while the regression residual can't take a price weight. The new method (`src/value.py`, `js/chicago-home-value-model.js` on the site):

- Six percentile ranks within the sample, higher is better: schools, safety, commute, walkability, newer homes (median year built, B25035), and low price (median price per sq ft for buyers; median gross rent, ACS B25064, for renters).
- `quality = weighted mean of the first five` (default weight 1 each). A missing indicator now counts as 50 instead of being skipped, so a zip with no crime data isn't scored on its other indicators alone (the hand check flagged Robbins for this).
- `value = (1 - price share) * quality + price share * low price`, default price share 50%.
- Value areas: the 20 highest value scores among zips with above-median quality (the pre-registered "high quality" rule).
- Targets: a zip that meets a reader's target scores 100 on that factor; one that misses scores `100 * percentile / target percentile`. A buyer's budget is compared with the median sale price.
- Two people: "best for both" ranks by the lower of the two value scores, among zips above both quality medians.
- Samples: buyers as before (at least 20 sales, a price per sq ft, at most one missing quality indicator, a home age: 338 zips). Renters: a median gross rent and at least 100 renter-occupied homes (B25003), same other rules (347 zips). ACS rent is used rather than Zillow's ZORI because ZORI covers only 229 of the 380 zips; the two correlate at 0.75.

These choices (the 50% default, the top 20, the 100-renter minimum, missing = 50) were made after the regression results were seen, so this is not a pre-registered test. The pre-registered test and its result (H1 supported, `output/first_run.json`, `docs/results.md`) stay as they are.

**Change (2026-10-21): the map scores closeness to the reader's targets, replacing the weighted value score above.** Alex's reason: a target isn't a pass/fail limit, it's the value the reader wants, and the weight says how much it matters. So a zip should score by how close it is to each target, with the weight as a multiplier; with price weighted highest and everything else low, a zip whose median price equals the target should score near 100. The method (`src/value.py`, `js/chicago-home-value-model.js` on the site):

- Six factors, each with a target and a weight: schools (state percentile), crimes per 1,000, commute minutes, walk index, home age in years, and price (median sale price for buyers, which replaces price per sq ft, since a reader's target is a price; median gross rent for renters).
- `pct(x)` = share of the sample's zips below x, ties counting half. `closeness = 100 - |pct(zip) - pct(target)|`. For schools, safety and price, beating the target (better schools, less crime, a lower price) also counts as 100, which Alex approved on 2026-10-21: nobody minds a safer or cheaper place than they asked for. For commute, walkability and home age, being off in either direction lowers the score. A missing value counts as 50.
- `score = sum(weight * closeness) / sum(weight)`; weights 0, 0.5, 1, 2, 3 (Ignore to Top). The top areas are the 20 highest scores; the above-median-quality rule is gone, because there's no separate quality score any more.
- Two people: each gets a score; "best for both" ranks by the lower of the two.
- The page scores nothing until every factor with a weight above zero has a target. Its "Fill in typical values" button uses round numbers near the sample medians (`EXAMPLE` in `src/value.py`), which is what `output/value.json` reports, so the two can be checked against each other.
- Samples unchanged (338 buyer zips, 347 renter zips).

**Change (2026-10-21): the reader can name where they work, and the commute becomes the drive time there.** Alex's reason: the Census commute is how long the people who already live in a zip travel, to wherever they work, which says little about the reader's own trip. A reader who works in Naperville and one who works in the Loop want different zips. The method (`src/commute.py`, `drive_to` in `src/value.py`, and the page):

- Each zip is a point: the representative point (always inside the shape) of its Census 2020 ZCTA cartographic boundary.
- Drive times between all 380 × 380 pairs come from the OSRM table service on OpenStreetMap roads (the public demo server, queried in 100 × 100 blocks on 2026-10-21; no pair is missing). They're free-flow times: no traffic, no tolls avoided, no transit, walking or biking. Rush-hour drives will be longer, often much longer into the Loop, and the gap is bigger for longer drives. The site gets whole minutes, capped at 255.
- When a person names a workplace (a zip, or a town that picks its zip), their commute factor is the drive time from each zip to it, scored like any other factor: its percentile among the sample's drive times to that workplace against the target's percentile, both directions counting as off target. Without a workplace, the Census average (B08013 / B08303) is used as before. Each person has their own workplace.
- The workplace has to be one of the 380 zips in scope. A town picks the first zip whose place name starts with what was typed, so a town with several zips gets one of them.
- The page now starts filled in with sample values (`SAMPLE` in `src/value.py`: the earlier typical targets, every weight Normal, a job in 60606) and scores right away, at Alex's request on 2026-10-21; the reader changes or clears them field by field, and a note says they're samples until every field is changed. A cleared field still stops the scoring until it's filled or its weight set to Ignore. `output/value.json` reports the sample (buyers: Justice, Prospect Heights, Willow Springs, Palos Heights, Palos Hills) and the same targets without a workplace.

**Change (2026-10-21): renters are scored on rent per person.** Alex asked whether rent was per person; it was the median gross rent per home (B25064). At Alex's request it's now divided by the zip's average renter household size (ACS B25010_E003, renter-occupied homes), so a zip of shared apartments and one of single renters compare on what each person pays. The renters' price factor, the reader's target and the labels all use rent per person. Limits: it's a ratio of two zip-level numbers (the median rent and the mean household size), not the median of each household's per-person rent, and household size counts children, so a family zip looks cheaper per person than its rents alone. The sample target for renters changes from $1,400 to $650 a month (the sample median is $633). One zip without a household size drops out of the renters' sample (346 zips). With the sample values, the renters' top three are Justice, Willow Springs and Clarendon Hills.

**Change (2026-10-21, same day): rent per person is rent per bedroom, not per household member.** Alex's correction: the point is roommates splitting an apartment, so a $2,500 two-bedroom is $1,250 each; household size counts children, which isn't what he meant. Rent per person is now the median gross rent divided by the average bedrooms of the zip's renter-occupied homes (ACS B25042_E009 to E015), counting a studio as 1 bedroom and "5 or more" as 5. Limits: still a ratio of two zip-level numbers, and it assumes one person per bedroom. The renters' sample target becomes $700 a month (the sample median is $687). The renters' sample is back to 347 zips. With the sample values, the renters' top five are Justice, Willow Springs, Hinsdale, Clarendon Hills and Addison.

**Change (2026-10-21): new sample values.** Alex asked for better starting values. Round targets and weights were searched on a small grid, and the chosen sample is: schools 90th percentile and safety 11 crimes per 1,000 at Top, commute 30 minutes and home age 30 years at Low, walkability 10 and price $600,000 (or $1,200 a month per person) at Normal, with a job in 60606. This is a starting point the reader replaces, not a finding.

Fix in the same change: in `src/value.py`, a missing value on a one-sided factor (schools, safety, price) was scored 100 instead of 50, because the "better than the target" rule also caught missing gaps. The page always used 50. Python now matches the page.

**Change (2026-10-21): the outside "best places" comparison is removed.** At Alex's request the comparison with an outside ranking of places to live is gone from the plan, code, outputs and site. H1 is now judged on value picks alone (at least 3): the main model has 16, so it is still supported. Zips are named by `src/places.py` (the largest place in each zip). The original wording is in git history.

**Change (2026-10-22): distance to the nearest train station is a seventh factor.** Alex asked for it. It's the straight-line miles from where people live to the nearest Metra, CTA 'L' or South Shore Line station (406 stations, from Metra's and NICTD's GTFS feeds and the City of Chicago's 'L' stop list). "Where people live" is the Census 2020 population center of each block group whose center falls in the zip; the zip's value is their population-weighted average distance, so a big zip with a station at one edge isn't scored as if everyone lived next to it. 20 zips with no block-group center inside use their representative point. The median zip is 1.6 miles away; the farthest rural Indiana zips are over 40. Like schools, safety and price it's one-sided: a closer station than the target counts as on target. Limits: straight-line, not walking distance, and it ignores how often trains run. The sample adds a 2-mile target at Low weight. Same change: `value.py` now reads drive times from the file the page uses, because re-rounding the one-decimal CSV put a few zips a minute off and swapped near-tied ranks.

Clarifications. These fill in details the plan didn't specify; none changes a definition above.

- **Vintages.** ACS 5-year 2020–2024 (latest on the pull date). Crime: 2025, the latest full year in the FBI Crime Data Explorer. Schools: Illinois 2025 Report Card (2024–25 tests, the latest published); Indiana spring 2026 ILEARN and SAT.
- **Zip population shares** (scope, police agency, place names) are computed from 2020 Census block populations, using the Census ZCTA-to-block relationship file and the 2020 block assignment files. The Census ZCTA-to-place relationship file only has land area, not population.
- **Schools.** For each district, proficiency is the mean of % proficient in ELA and in math, in two bands: grades 3–8 (IL IAR, IN ILEARN) and high school (IL grade 11 ACT, IN grade 11 SAT). Each band is ranked within its own state, among the state's geographic districts with results. A block takes its grades 3–8 percentile from its unified or elementary district and its high school percentile from its unified or secondary district, and its school value is the mean of the two. The zip value is the land-area-weighted mean of its blocks. Chicago Public Schools is one district, so every Chicago zip gets the same school value; this is a limitation of district-level data.
- **Safety.** "The place holding most of its population" is the largest single population group among the incorporated places in the zip and the unincorporated land of each county. Places with no agency in the FBI data leave the indicator missing. The list is in `docs/data_notes.md`.
- **Walkability.** The EPA index is published for 2010 block groups. Each 2020 block is linked to the 2010 block it overlaps most (Census 2010–2020 block relationship files), and the zip value is weighted by 2020 block population.
- **Place names.** Each zip is named after the place (including Census-designated places) with the largest population in it, even if most of the zip is outside any place.
