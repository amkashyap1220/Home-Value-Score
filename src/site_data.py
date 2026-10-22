"""Step 4: the small JSON files the value map on alexanderk.dev reads.

Reads output/value.csv (made by value.py) and writes:
  output/site/chicago-home-value.json       one record per zip: name, nearest station, and
                                            for buyers and renters the seven raw values, so
                                            the page can score them against the reader's
                                            own targets and weights
  output/site/chicago-home-value-zips.json  zip shapes (made by map.py)
  output/site/chicago-home-value-stations.json  the train stations inside the map (from stations.py),
                                            as [lon, lat, name, agency]

Copy both to research/ in the site repo (not /data/, which the site's worker handles).
"""
import json

import pandas as pd

from fetch import ROOT
from value import COLUMNS, SAMPLE, MIN_RENTERS, MIN_SALES, TOP

OUT = ROOT / "output"


def main():
    value = pd.read_csv(OUT / "value.csv", dtype={"zcta": str})
    station = pd.read_csv(ROOT / "data/processed/station_distance.csv", dtype={"zcta": str}).set_index("zcta").nearest_station
    zips = {}
    for r in value.itertuples():
        z = zips.setdefault(r.zcta, {
            "zip": r.zcta,
            "place": r.place_name if isinstance(r.place_name, str) else "",
            "state": r.state,
            "station": station.get(r.zcta, ""),   # the nearest station to most of its residents
        })
        # [school percentile in state, crimes per 1,000, commute min, walk index, home age, price or rent,
        # miles to the nearest station]; null when missing; the page computes percentiles and closeness from these
        cols = [*COLUMNS[r.mode][:5], "price", *COLUMNS[r.mode][6:]]
        z[r.mode] = [None if pd.isna(getattr(r, c)) else round(float(getattr(r, c)), 2) for c in cols]

    site = {
        "top": TOP, "sample": SAMPLE,
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
