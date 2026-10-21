"""Step 4: the small JSON file the chart on alexanderk.dev reads.

Reads output/scores.csv and output/scores.json (made by model.py) and writes
output/site/chicago-home-value.json: one short record per zip, plus the numbers
the chart needs (quality median, residual SD). Each record also carries the four
indicator percentiles and the model's controls, so the page can refit the model
with the reader's own weights. Copy that file to
writing/chicago-home-value.json in the site repo.
"""
import json

import pandas as pd

from fetch import ROOT

OUT = ROOT / "output"


def main():
    scores = pd.read_csv(OUT / "scores.csv", dtype={"zcta": str})
    meta = json.loads((OUT / "scores.json").read_text())["meta"]

    zips = [{
        "zip": r.zcta,
        "place": r.place_name if isinstance(r.place_name, str) else "",
        "state": r.state,
        "quality": round(r.quality, 1),
        "ppsf": round(r.ppsf),
        "predicted": round(r.predicted),
        "residual": round(r.residual, 1),
        "pick": bool(r.value_pick),
        "on_list": bool(r.on_list),
        "list_entry": r.list_entry if isinstance(r.list_entry, str) else None,
        # Inputs for the reader's own weights on the site: the four percentiles (null when missing)
        # and the model's controls, so the page can rebuild the score and refit the regression
        "p": [None if pd.isna(v) else round(v, 3) for v in (r.p_schools, r.p_safety, r.p_commute, r.p_walkability)],
        "price": round(r.ppsf, 2),
        "tax": float(f"{r.tax_rate:.5g}"),
        "age": round(r.home_age, 1),
        "energy": round(r.home_energy_month, 2),
        "fuel": round(r.commute_fuel_year, 1),
    } for r in scores.itertuples()]

    site = {
        "n": meta["n"], "r2": round(meta["r2"], 3), "residual_sd": round(meta["residual_sd"], 2),
        "quality_median": round(meta["quality_median"], 2),
        "picks": meta["value_picks"], "not_on_list": meta["not_on_list"],
        "zips": zips,
    }
    (OUT / "site").mkdir(exist_ok=True)
    path = OUT / "site/chicago-home-value.json"
    path.write_text(json.dumps(site, separators=(",", ":")))
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB, {len(zips)} zips)")


if __name__ == "__main__":
    main()
