# Home Value Score (Chicago metro)

**Question:** are there high-quality zip codes in the Chicago metro where homes sell for less per square foot than their quality predicts, and are those zips mostly outside the places people usually recommend?

**Status:** method pre-registered in [docs/decisions.md](docs/decisions.md) on 2026-10-21, before any price data was downloaded. Steps 2 and 3 are done: the inputs for 380 zips ([data notes](docs/data_notes.md)), then prices, the model and the robustness checks ([results](docs/results.md)).

## Method in short

The post on the site answers two separate questions (since 2026-10-22; see the change log in [docs/decisions.md](docs/decisions.md)):

- **Fit to you:** how well a zip matches the reader's own targets and weights (below).
- **Price vs expected:** whether a zip's price per sq ft is below or above what zips with the same measured schools, safety, commute, walkability, train access, home age and state sell for. A fixed log-price regression with leave-one-out predictions, validated against simple baselines with spatial cross-validation, with a confidence rating per zip (`src/value_gap.py`, results in [docs/results.md](docs/results.md#price-vs-expected-2026-10-22)). "Below expected" is not "undervalued": the gap includes everything the model can't see.

The fit score:

1. The reader sets a target and a weight for seven things: schools, safety, commute time, distance to the nearest train station, walkability, home age, and median sale price (buyers) or rent per bedroom (renters: median gross rent divided by the average bedrooms of rented homes, so each roommate's share). If they name the town or zip they work in, commute becomes the drive time from each zip to that workplace (OpenStreetMap roads via OSRM, free-flow, so no traffic and no transit) instead of the Census average. Train station distance is the straight-line miles to the nearest Metra, CTA 'L' or South Shore Line station, averaged over where people in the zip live (Census 2020 block-group population centers). Two people can name different workplaces. The page starts filled in with sample values (`SAMPLE` in `src/value.py`) that the reader changes to their own.
2. Each value and each target becomes a percentile among the metro's zips. Closeness = 100 − the gap between the zip's percentile and the target's, so it's 100 exactly on target. For schools, safety, price and train station, beating the target also counts as 100.
3. Score = the weighted average of the closeness values of the factors the zip has data for; coverage = the share of the reader's weight those carry. A missing value is left out, not counted as average, and a zip under 80% coverage is shown but not ranked. The 20 highest ranked scores are the reader's top areas, each linked to listings. With two people, "best for both" ranks by the lower of their two scores.

The original pre-registered study (a regression of price per sq ft on quality, taxes and running costs, with value picks more than one standard deviation below the line) is still computed by `src/model.py`; its result is below. Race and ethnicity, and proxies for them, are not used anywhere.

## Sources

| Data | Source | URL | Pulled | License |
|---|---|---|---|---|
| Zip (ZCTA) boundaries | Census TIGER/Line 2020 ZCTA5 | https://www2.census.gov/geo/tiger/TIGER2020/ZCTA520/ | 2026-10-21 | Public domain (U.S. Government) |
| Block population and land area | Census TIGER/Line 2020 blocks (IL, IN, WI) | https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/ | 2026-10-21 | Public domain |
| Block to zip, place, school district | Census 2020 ZCTA-to-block relationship file; 2020 block assignment files | https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/ , https://www2.census.gov/geo/docs/maps-data/data/baf2020/ | 2026-10-21 | Public domain |
| Places, counties | Census TIGER/Line 2020 PLACE and COUNTY | https://www2.census.gov/geo/tiger/TIGER2020/ | 2026-10-21 | Public domain |
| Commute time, tax rate | ACS 5-year 2020–2024 summary file, tables B08013, B08303, B25090, B25082 (and B25103, B25077 for comparison) | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/ | 2026-10-21 | Public domain |
| Walkability | EPA Smart Location Database v3, National Walkability Index | https://edg.epa.gov/EPADataCommons/public/OA/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv | 2026-10-21 | Public domain |
| 2010 to 2020 blocks (for walkability) | Census 2010–2020 block relationship files (IL, IN) | https://www2.census.gov/geo/docs/maps-data/data/rel2020/t10t20/ | 2026-10-21 | Public domain |
| Illinois schools | ISBE 2025 Report Card Public Data Set | https://www.isbe.net/Documents/2025-Report-Card-Public-Data-Set.xlsx | 2026-10-21 | Illinois public data, no license stated |
| Indiana schools | Indiana DOE, ILEARN 2026 grades 3–8 and SAT 2026 grade 11, by corporation | https://www.in.gov/doe/it/data-center-and-reports/ | 2026-10-21 | Indiana public data, no license stated |
| District ids (state id to NCES id) | NCES Common Core of Data 2024 directory, via the Urban Institute Education Data API | https://educationdata.urban.org/api/v1/school-districts/ccd/directory/2024/ | 2026-10-21 | ODC Attribution License (Urban Institute); CCD is public domain |
| Crime | FBI Crime Data Explorer, agency list and monthly violent and property offenses, 2024–2025 | https://cde.ucr.cjis.gov/LATEST/ | 2026-10-21 | Public domain |
| Prices | Redfin Data Center, zip code market tracker (All Residential, 90-day periods), window 2025-06 to 2026-05 | https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/zip_code_market_tracker.tsv000.gz | 2026-10-21 | Redfin Data Center terms: free to use with attribution to Redfin |
| Home value trend (context only) | Zillow Home Value Index, zip, all homes, smoothed, seasonally adjusted (through 2026-09) | https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv | 2026-10-21 | Zillow Research terms of use, with attribution |
| Home age, energy bills, means of commuting (added after the first run) | ACS 5-year 2020–2024 summary file, tables B25035, B25132, B25133, B08301 | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/ | 2026-10-21 | Public domain |
| Gasoline prices (added after the first run) | EIA weekly retail regular gasoline, Chicago (EMM_EPMR_PTE_YORD_DPG) and Midwest (EMM_EPMR_PTE_R20_DPG) | https://www.eia.gov/dnav/pet/pet_pri_gnd_dcus_nus_w.htm | 2026-10-21 | Public domain |
| Rent (added for the value map) | ACS 5-year 2020–2024 summary file, tables B25064 (median gross rent), B25003 (renter-occupied homes) and B25042 (bedrooms by tenure) | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/ | 2026-10-21 | Public domain |
| Rent, context only | Zillow Observed Rent Index, zip, all homes, smoothed (through 2026-09) | https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv | 2026-10-21 | Zillow Research terms of use, with attribution |
| Zip shapes for the map | Census 2020 ZCTA cartographic boundaries, 1:500,000 | https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip | 2026-10-21 | Public domain |
| Metra stations | Metra GTFS schedule feed (stops.txt) | https://schedules.metrarail.com/gtfs/schedule.zip | 2026-10-22 | Metra GTFS terms of use |
| CTA 'L' stations | City of Chicago Data Portal, CTA System Information – List of 'L' Stops | https://data.cityofchicago.org/d/8pix-ypme | 2026-10-22 | City of Chicago Data Portal terms of use |
| South Shore Line stations | NICTD GTFS feed (stops.txt) | http://www.mysouthshoreline.com/google/google_transit.zip | 2026-10-22 | NICTD GTFS terms of use |
| Where people live (for station distance) | Census 2020 centers of population by block group (IL, IN) | https://www2.census.gov/geo/docs/reference/cenpop2020/blkgrp/ | 2026-10-22 | Public domain |
| Chicago crime by location (added 2026-10-22) | City of Chicago Data Portal, Crimes - 2001 to Present, 2025 incidents | https://data.cityofchicago.org/d/ijzp-q8t2 | 2026-10-22 | City of Chicago Data Portal terms of use |
| Housing stock (sensitivity check, added 2026-10-22) | ACS 5-year 2020–2024, tables B25024 (units in structure) and B25018 (median rooms) | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/ | 2026-10-22 | Public domain |
| Drive times between zips (added for the workplace commute) | OSRM table service on OpenStreetMap roads (public demo server), from each zip's representative point to every other | https://router.project-osrm.org/ | 2026-10-21 | Map data © OpenStreetMap contributors, ODbL; OSRM is BSD-2 |

Each file's exact URL and download time is in `data/raw/manifest.csv`. Missing police agencies and other data gaps are listed in [docs/data_notes.md](docs/data_notes.md).

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

**Price vs expected (2026-10-22).** The log-price model explains about half the variation in price per sq ft for areas it didn't see (spatial cross-validation R² 0.53, against 0.09 for the pre-registered model and −0.15 for the metro average). 86 zips sell at least 10% below expected, 99 at least 10% above; 35 and 42 of them with high confidence. The gaps are stable from year to year (correlation 0.97 with 2025 prices), and the most-below list is led by places with long-running disinvestment (Gary, Harvey), so they describe lasting differences the indicators miss, not bargains.

**Fit map (the post).** There is no single ranking any more: each reader's result depends on their targets. `output/value.json` has the sample values the page starts with (schools and safety at Top, commute and home age at Low, a job in the Loop, 60606): the buyers' top 20 is led by Lisle, Naperville and Dyer. The same targets without a workplace (the Census average commute) are under `no_workplace`.

**Pre-registered test.** H1 is supported: 16 of 338 zips are both above-median quality and more than one standard deviation ($56/sq ft) below the price the model predicts. The model explains 41% of the variation in price. About half the picks depend on which indicators go into the score, and the hand check flags some as measurement artifacts. A first run without the running costs, as pre-registered, also met the rule (16 picks) but leaned heavily on Indiana. Details: [docs/results.md](docs/results.md).

Write-up with the interactive map: [Where is the best value in Chicagoland?](https://alexanderk.dev/writing/chicago-home-value.html)

## How to rerun

```
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cd src
../.venv/bin/python blocks.py        # block table: population, zip, place, school districts
../.venv/bin/python zips.py          # the 380 in-scope zips
../.venv/bin/python acs.py           # commute time and tax rate
../.venv/bin/python walkability.py
../.venv/bin/python schools.py
../.venv/bin/python crime.py
../.venv/bin/python places.py        # name each zip after its largest place
../.venv/bin/python indicators.py    # joins everything into data/processed/indicators.csv
../.venv/bin/python prices.py        # Redfin 12-month price per sq ft and sales (+ Zillow ZHVI context)
../.venv/bin/python extras.py       # running costs and home age: home age, energy bills, commuting fuel
../.venv/bin/python model.py         # quality score, regression, value picks, robustness -> output/
../.venv/bin/python rent.py          # median gross rent, rent per bedroom, renter-occupied homes (+ Zillow ZORI context)
../.venv/bin/python map.py           # simplified zip shapes for the map -> output/site/
../.venv/bin/python commute.py       # drive times between all 380 zips (OSRM) -> data/processed/, output/site/
../.venv/bin/python stations.py      # miles to the nearest Metra, CTA or South Shore Line station -> data/processed/
../.venv/bin/python chicago_crime.py # crime rates by zip inside Chicago (city incident data) -> data/processed/
../.venv/bin/python indicators.py    # again, to add the Chicago rates (crimes_per_1000_local)
../.venv/bin/python structure.py     # housing stock: single-family share, median rooms
../.venv/bin/python price_history.py # earlier price windows and single-family prices (Redfin)
../.venv/bin/python value.py         # fit scores for the sample values, buyers and renters -> output/value.*
../.venv/bin/python value_gap.py     # price vs expected: model, validation, checks -> output/value_gap.*
../.venv/bin/python site_data.py     # small JSON for the map on alexanderk.dev -> output/site/
```

Each script downloads what it needs into `data/raw/` (about 6 GB, not committed) and skips files already there. Copy the files in `output/site/` to `research/` in the site repo.

Tests (scoring, normalization, missing data, the model's building blocks): `../.venv/bin/python -m pytest tests` from the repo root. The site repo's `node --test` checks that the page ranks the sample values exactly as `src/value.py` does.
