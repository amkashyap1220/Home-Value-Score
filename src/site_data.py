"""Step 4: the small JSON file the chart on alexanderk.dev reads.

Reads output/scores.csv, output/scores.json and output/extended.json (made by model.py)
and writes output/site/chicago-home-value.json: one short record per zip, plus the
numbers the chart needs (quality median, residual SDs). Copy that file to
writing/chicago-home-value.json in the site repo.
"""
import json

import pandas as pd

from fetch import ROOT

OUT = ROOT / "output"


def main():
    scores = pd.read_csv(OUT / "scores.csv", dtype={"zcta": str})
    meta = json.loads((OUT / "scores.json").read_text())["meta"]
    extended = json.loads((OUT / "extended.json").read_text())

    zips = []
    for r in scores.itertuples():
        zips.append({
            "zip": r.zcta,
            "place": r.place_name if isinstance(r.place_name, str) else "",
            "state": r.state,
            "quality": round(r.quality, 1),
            "ppsf": round(r.ppsf),
            "predicted": round(r.predicted),
            "residual": round(r.residual, 1),
            "ext_residual": None if pd.isna(r.extended_residual) else round(r.extended_residual, 1),
            "pick": bool(r.value_pick),
            "ext_pick": r.extended_pick is True or r.extended_pick == "True",
            "on_list": bool(r.on_list),
            "list_entry": r.list_entry if isinstance(r.list_entry, str) else None,
        })

    site = {
        "quality_median": round(meta["quality_median"], 2),
        "primary": {"n": meta["n"], "r2": round(meta["r2"], 3), "residual_sd": round(meta["residual_sd"], 2),
                    "picks": meta["value_picks"], "not_on_list": meta["not_on_list"]},
        "extended": {"n": extended["n"], "r2": round(extended["r2"], 3),
                     "residual_sd": round(extended["residual_sd"], 2),
                     "picks": extended["value_picks"], "not_on_list": extended["not_on_list"]},
        "zips": zips,
    }
    (OUT / "site").mkdir(exist_ok=True)
    path = OUT / "site/chicago-home-value.json"
    path.write_text(json.dumps(site, separators=(",", ":")))
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB, {len(zips)} zips)")


if __name__ == "__main__":
    main()
