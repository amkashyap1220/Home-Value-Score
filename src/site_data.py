"""Step 4: the small JSON files the value map on alexanderk.dev reads.

Reads output/value.csv (made by value.py) and writes:
  output/site/chicago-home-value.json       one record per zip: name, nearest station, and
                                            for buyers and renters the seven raw values, so
                                            the page can score them against the reader's
                                            own targets and weights; for buyers also the
                                            housing value estimate (value_gap.py) and the
                                            data behind it. Top-level: the value model's
                                            summary and checks, factor correlations, and the
                                            sample's top 20 from value.py, which the site's
                                            tests use to check the page scores the same way
  output/site/chicago-home-value-zips.json  zip shapes (made by map.py)
  output/site/chicago-home-value-stations.json  the train stations inside the map (from stations.py),
                                            as [lon, lat, name, agency]

Copy both to research/ in the site repo (not /data/, which the site's worker handles).
"""
import json

import pandas as pd

from fetch import ROOT
from value import COLUMNS, MIN_COVERAGE, NAMES, SAMPLE, MIN_RENTERS, MIN_SALES, TOP

OUT = ROOT / "output"


def main():
    value = pd.read_csv(OUT / "value.csv", dtype={"zcta": str})
    station = pd.read_csv(ROOT / "data/processed/station_distance.csv", dtype={"zcta": str}).set_index("zcta").nearest_station
    ind = pd.read_csv(ROOT / "data/processed/indicators.csv", dtype={"zcta": str}).set_index("zcta")
    gap = pd.read_csv(OUT / "value_gap.csv", dtype={"zcta": str}).set_index("zcta")
    model = json.loads((OUT / "value_gap.json").read_text())
    checks = json.loads((OUT / "value.json").read_text())
    zips = {}
    for r in value.itertuples():
        z = zips.setdefault(r.zcta, {
            "zip": r.zcta,
            "place": r.place_name if isinstance(r.place_name, str) else "",
            "state": r.state,
            "station": station.get(r.zcta, ""),   # the nearest station to most of its residents
            # Where the safety number comes from: the year, and "city" for Chicago's own zip rates
            "crime": None if pd.isna(ind.crime_year.get(r.zcta)) else
                     [int(ind.crime_year[r.zcta]), "city" if ind.place_name.get(r.zcta) == "Chicago" else "agency"],
        })
        # [school percentile in state, crimes per 1,000, commute min, walk index, home age, price or rent,
        # miles to the nearest station]; null when missing; the page computes percentiles and closeness from these
        cols = [*COLUMNS[r.mode][:5], "price", *COLUMNS[r.mode][6:]]
        z[r.mode] = [None if pd.isna(getattr(r, c)) else round(float(getattr(r, c)), 2) for c in cols]
        if r.mode == "buy" and r.zcta in gap.index:
            g = gap.loc[r.zcta]
            num = lambda x, d=3: None if pd.isna(x) else round(float(x), d)
            z["value"] = {
                "gap": num(g.gap), "lo": num(g.gap_lo), "hi": num(g.gap_hi),
                "ppsf": num(g.ppsf, 1), "expected": num(g.expected_ppsf, 1), "sales": int(g.sales_12m),
                "cls": g.value_class, "conf": g.confidence, "agree": num(g.agreement, 2),
                "prev": [num(g.gap_2025), num(g.gap_2024), num(g.gap_2023)],
                "issues": [] if pd.isna(g.issues) else g.issues.split(";"),
            }

    buy = value[value["mode"] == "buy"]
    cols = [*COLUMNS["buy"][:5], "price", COLUMNS["buy"][6]]
    corr = buy[cols].corr(method="spearman").round(2)
    site = {
        "top": TOP, "min_coverage": MIN_COVERAGE, "sample": SAMPLE,
        "sample_check": {m: {"top": checks[m]["top"], "scores": checks[m]["top_scores"]} for m in ("buy", "rent")},
        "factor_correlation": {"names": NAMES, "spearman": corr.values.tolist()},
        "value_model": {k: model[k] for k in ("n", "n_complete", "r2_in_sample", "loo_residual_sd_log", "in_line_band",
                                               "few_sales", "agreement_threshold", "price_window", "coefficients",
                                               "validation", "spatial_autocorrelation", "persistence", "variants",
                                               "variant_same_class", "classes", "confidence", "sales_noise_b")},
        "samples": {"buy": f"at least {MIN_SALES} sales in the past year",
                    "rent": f"at least {MIN_RENTERS} rented homes"},
        "zips": sorted(zips.values(), key=lambda z: z["zip"]),
    }
    path = OUT / "site/chicago-home-value.json"
    path.write_text(json.dumps(site, separators=(",", ":")))
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB, {len(zips)} zips)")

    # Stations inside the map's bounding box (the shapes' outer coordinates)
    shapes = json.loads((OUT / "site/chicago-home-value-zips.json").read_text())
    pts = [c for f in shapes["features"] for c in coords(f["geometry"]["coordinates"])]
    lons, lats = [c[0] for c in pts], [c[1] for c in pts]
    st = pd.read_csv(ROOT / "data/processed/stations.csv")
    st = st[st.lon.between(min(lons), max(lons)) & st.lat.between(min(lats), max(lats))]
    path = OUT / "site/chicago-home-value-stations.json"
    path.write_text(json.dumps([[round(r.lon, 4), round(r.lat, 4), r.name, r.agency] for r in st.itertuples()], separators=(",", ":")))
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB, {len(st)} stations)")


def coords(c):
    """Every [lon, lat] pair in a GeoJSON coordinate array, however deeply nested."""
    if isinstance(c[0], (int, float)):
        yield c
    else:
        for x in c:
            yield from coords(x)


if __name__ == "__main__":
    main()
