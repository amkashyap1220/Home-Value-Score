# Home Value Score (Chicago metro)

**Question:** are there high-quality zip codes in the Chicago metro where homes sell for less per square foot than their quality predicts, and are those zips mostly outside the places people usually recommend?

**Status:** method pre-registered in [docs/decisions.md](docs/decisions.md) on 2026-10-21, before any price data was downloaded. Steps 2 and 3 are done: the inputs for 380 zips ([data notes](docs/data_notes.md)), then prices, the model and the robustness checks ([results](docs/results.md)).

## Method in short

The post on the site is an interactive value map (since 2026-10-21; see the change log in [docs/decisions.md](docs/decisions.md)):

1. Rank each zip from 0 to 100 on six things: schools, safety, commute time, walkability, home age, and price per square foot (buyers) or median rent (renters).
2. Quality = weighted average of the first five. Value = (1 − price share) × quality + price share × the price rank. Readers set the weights, the price share and optional targets, alone or with a second person.
3. The 20 highest value scores among zips with above-median quality are the value areas. Compare them with a "word of mouth" list built from Niche's 2026 Best Places to Live rankings.

The original pre-registered study (a regression of price per sq ft on quality, taxes and running costs, with value picks more than one standard deviation below the line) is still computed by `src/model.py`; its result is below. Race and ethnicity, and proxies for them, are not used anywhere.

## Sources

| Data | Source | URL | Pulled | License |
|---|---|---|---|---|
| Reputation list | Niche, 2026 Best Places to Live (IL, IN) | https://www.niche.com/places-to-live/search/best-places-to-live/s/illinois/ | 2026-10-21 | Niche terms of use; place names only |
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
| Rent (added for the value map) | ACS 5-year 2020–2024 summary file, tables B25064 (median gross rent) and B25003 (renter-occupied homes) | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/ | 2026-10-21 | Public domain |
| Rent, context only | Zillow Observed Rent Index, zip, all homes, smoothed (through 2026-09) | https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv | 2026-10-21 | Zillow Research terms of use, with attribution |
| Zip shapes for the map | Census 2020 ZCTA cartographic boundaries, 1:500,000 | https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip | 2026-10-21 | Public domain |
| Chicago neighborhoods | City of Chicago, Boundaries – Neighborhoods | https://data.cityofchicago.org/d/9wp7-iasj | 2026-10-21 | City of Chicago Data Portal terms of use |

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

**Value map (the post).** With my default weights (everything equal, price half the score), none of Niche's Illinois top 20 is among my 20 value areas for buying. 7 of the 20 are on the list, all from Niche's Indiana ranking (Valparaiso, Chesterton, Munster, Dyer, Schererville, St. John). The Illinois value areas include Woodstock, Sycamore, Grayslake, Gilberts, Coal City and Joliet 60433. For renting, 5 of 20 are on the list. Numbers: `output/value.json`.

**Pre-registered test.** H1 is supported: 16 of 338 zips are both above-median quality and more than one standard deviation ($56/sq ft) below the price the model predicts, and 15 of them are not on the reputation list. The model explains 41% of the variation in price. About half the picks depend on which indicators go into the score, and the hand check flags some as measurement artifacts. A first run without the running costs, as pre-registered, also met the rule (16 picks, 11 off the list) but leaned heavily on Indiana. Details: [docs/results.md](docs/results.md).

Write-up with the interactive map: [Where's the best home value in Chicagoland?](https://alexanderk.dev/writing/chicago-home-value.html)

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
../.venv/bin/python reputation.py
../.venv/bin/python indicators.py    # joins everything into data/processed/indicators.csv
../.venv/bin/python prices.py        # Redfin 12-month price per sq ft and sales (+ Zillow ZHVI context)
../.venv/bin/python extras.py       # running costs and home age: home age, energy bills, commuting fuel
../.venv/bin/python model.py         # quality score, regression, value picks, robustness -> output/
../.venv/bin/python rent.py          # median gross rent and renter-occupied homes (+ Zillow ZORI context)
../.venv/bin/python value.py         # value score with the default weights, buyers and renters -> output/value.*
../.venv/bin/python map.py           # simplified zip shapes for the map -> output/site/
../.venv/bin/python site_data.py     # small JSON for the map on alexanderk.dev -> output/site/
```

Each script downloads what it needs into `data/raw/` (about 4.6 GB, not committed) and skips files already there. Copy the two files in `output/site/` to `writing/` in the site repo.
