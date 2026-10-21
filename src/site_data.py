"""Step 4: the small JSON files the value map on alexanderk.dev reads.

Reads output/value.csv (made by value.py) and writes:
  output/site/chicago-home-value.json       one record per zip: name, Niche list entry, and
                                            for buyers and renters the price and the six
                                            percentiles, so the page can score with the
                                            reader's own weights
  output/site/chicago-home-value-zips.json  zip shapes (made by map.py)

Copy both to writing/ in the site repo (not /data/, which the site's worker handles).
"""
import json

import pandas as pd

from fetch import ROOT
from value import DEFAULT, FACTORS, MIN_RENTERS, MIN_SALES, NAMES, TOP

OUT = ROOT / "output"


def main():
    value = pd.read_csv(OUT / "value.csv", dtype={"zcta": str})
    zips = {}
    for r in value.itertuples():
        z = zips.setdefault(r.zcta, {
            "zip": r.zcta,
            "place": r.place_name if isinstance(r.place_name, str) else "",
            "state": r.state,
            "list": r.list_entry if r.on_list else None,
        })
        # v: the raw values, for readers' targets: [school proficiency percentile in state,
        #    crimes per 1,000, commute minutes, walk index, home age in years, $/sq ft or rent,
        #    median sale price (buyers only)]
        # p: percentiles within the sample: [schools, safety, commute, walkability, newer homes, low price]
        # null when missing
        num = lambda v, d=2: None if pd.isna(v) else round(float(v), d)
        z[r.mode] = {
            "v": [num(getattr(r, c)) for c in [*FACTORS, "price"]] + [num(r.median_price, -3)],
            "p": [num(getattr(r, n)) for n in [*NAMES, "low_price"]],
        }

    site = {
        "top": TOP, "default": DEFAULT,
        "samples": {"buy": f"at least {MIN_SALES} sales in the past year",
                    "rent": f"at least {MIN_RENTERS} rented homes"},
        "zips": sorted(zips.values(), key=lambda z: z["zip"]),
    }
    path = OUT / "site/chicago-home-value.json"
    path.write_text(json.dumps(site, separators=(",", ":")))
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB, {len(zips)} zips)")


if __name__ == "__main__":
    main()
