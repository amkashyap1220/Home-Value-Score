# Data notes (step 2: quality and tax inputs)

Pulled 2026-10-21. Every download is listed with its URL and time in `data/raw/manifest.csv`.

## Coverage

| Input | Zips with a value (of 380) |
|---|---|
| Schools | 380 |
| Safety (crime) | 342 (8 of them using 2024) |
| Commute | 372 |
| Walkability | 380 |
| Tax rate | 371 |

336 zips have all four quality indicators, 42 are missing one (scored on the other three and flagged), and 2 are missing two (dropped under the pre-registered rule). Most of the incomplete zips are small rural zips, many of which will also fall under the 20-sales minimum.

## Police agencies with incomplete data

Each zip is assigned one police agency (rule in `docs/decisions.md`). These zips have no usable 2025 crime rate. Where the agency's 2024 data covers all 12 months, 2024 is used instead (Alex's choice, 2026-10-21); the year used is in the `crime_year` column of `data/processed/crime.csv`.

| Agency | Zips | What happened |
|---|---|---|
| Libertyville Police Department | 60048 | 2025 offenses under half of 2024; used 2024 |
| Northlake Police Department | 60164 | 2025 offenses under half of 2024; used 2024 |
| Westchester Police Department | 60154 | 2025 offenses under half of 2024; used 2024 |
| Bloomingdale Police Department | 60108 | Reported 1 of 12 months in 2025; used 2024 |
| Wayne Police Department | 60184 | Reported 1 of 12 months in 2025; used 2024 |
| Hometown Police Department | 60456 | Reported 2 of 12 months in 2025; used 2024 |
| Waterman Police Department | 60556 | Reported 5 of 12 months in 2025; used 2024 |
| Roselle Police Department | 60172 | Reported 7 of 12 months in 2025; used 2024 |
| Beach Park (no agency found) | 60083 | No agency in the FBI data |
| Beverly Shores (no agency found) | 46301 | No agency in the FBI data |
| Big Rock (no agency found) | 60511 | No agency in the FBI data |
| Braceville (no agency found) | 60407 | No agency in the FBI data |
| Brook (no agency found) | 47922 | No agency in the FBI data |
| Burlington (no agency found) | 60109 | No agency in the FBI data |
| Gardner (no agency found) | 60424 | No agency in the FBI data |
| Goodland (no agency found) | 47948 | No agency in the FBI data |
| Kaneville (no agency found) | 60144 | No agency in the FBI data |
| Kentland (no agency found) | 47951 | No agency in the FBI data |
| Kinsman (no agency found) | 60437 | No agency in the FBI data |
| Malta (no agency found) | 60150 | No agency in the FBI data |
| Millbrook (no agency found) | 60536 | No agency in the FBI data |
| Morocco (no agency found) | 47963 | No agency in the FBI data |
| Mount Ayr (no agency found) | 47964 | No agency in the FBI data |
| Ringwood (no agency found) | 60072 | No agency in the FBI data |
| Schneider (no agency found) | 46376 | No agency in the FBI data |
| Shabbona (no agency found) | 60550 | No agency in the FBI data |
| South Wilmington (no agency found) | 60474 | No agency in the FBI data |
| Bridgeview Police Department | 60455 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Broadview Police Department | 60155 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Dolton Police Department | 60419 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Genoa Police Department | 60135 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Lake Station Police Department | 46405 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Lyons Police Department | 60534 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Markham Police Department | 60428 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Matteson Police Department | 60443 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Maywood Police Department | 60153 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Remington Police Department | 47977 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Rensselaer Police Department | 47978 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Robbins Police Department | 60472 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Schiller Park Police Department | 60176 | Reported 0 of 12 months in 2025; 2024 also incomplete, so missing |
| Jasper County Sheriff's Office | 46310, 46392, 47943 | Reported 1 of 12 months in 2025; 2024 also incomplete, so missing |
| Newton County Sheriff's Office | 46349, 46379, 46381 | Reported 4 of 12 months in 2025; 2024 also incomplete, so missing |

The places marked "no agency found" have no police department in the FBI Crime Data Explorer agency list for their state. Most are small villages policed by the county sheriff by contract or by default, but the plan assigns incorporated places to their own department, so their safety value is left missing rather than guessed.

## Known quirks

- **Chicago is one school district and one police agency.** Every Chicago zip gets the same school percentile (Chicago Public Schools) and the same crime rate (Chicago Police Department). Within Chicago, only commute and walkability vary. This is a limitation of the district- and agency-level data the plan specifies.
- **Small agencies are noisy.** A village of 500 people with 0 offenses gets a rate of 0. These are reported as published.
- **Tax rate.** Uses ACS aggregates, not medians, because the median taxes table is top-coded at $10,000 (see the change log in `docs/decisions.md`). Indiana's median effective rate is about 0.8%, Illinois' about 2.0%.
- **Walkability** is from EPA's Smart Location Database v3 (2021), built on 2010 block groups and 2019 data. It's the latest national release.
