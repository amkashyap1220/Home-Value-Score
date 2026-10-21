# Home Value Score (Chicago metro)

**Question:** are there high-quality zip codes in the Chicago metro where homes sell for less per square foot than their quality predicts, and are those zips mostly outside the places people usually recommend?

**Status:** method pre-registered in [docs/decisions.md](docs/decisions.md) on 2026-10-21, before any price data was downloaded. Step 2 is done: the zip list, the four quality indicators, the tax rate and the reputation list are built for 380 zips ([data notes](docs/data_notes.md)). No price data has been downloaded yet.

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

Not yet available.

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
```

Each script downloads what it needs into `data/raw/` (about 3 GB, not committed) and skips files already there. Price data and the model come in step 3.
