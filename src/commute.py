"""Drive times between every pair of in-scope zips, for the commute to a reader's
workplace on the value map (added 2026-10-21; see the change log in docs/decisions.md).

Each zip is represented by a point inside its shape (shapely's representative point of
the Census 2020 ZCTA cartographic boundary, the same shapes as map.py). The public OSRM
demo server, which routes on OpenStreetMap, gives the driving time between each pair.
These are free-flow times: no traffic, no transit, no parking, so a rush-hour commute
is longer. The server is asked in blocks of 100 x 100 zips, one block per second.

Outputs:
  data/processed/drive_minutes.csv          zcta x zcta matrix, minutes (rows = from, columns = to)
  output/site/chicago-home-value-drive.json  the same matrix for the site: zip order plus whole
                                             minutes (capped at 255) as base64 bytes, row by row
"""
import base64
import json
import time

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

from fetch import ROOT, fetch
from map import URL

OSRM = "https://router.project-osrm.org/table/v1/driving/"
BLOCK = 100


def points():
    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    shapes = gpd.read_file(fetch(URL), columns=["ZCTA5CE20"])
    shapes = shapes[shapes.ZCTA5CE20.isin(zips.zcta)].to_crs(4326).sort_values("ZCTA5CE20").reset_index(drop=True)
    pts = shapes.geometry.representative_point()
    return shapes.ZCTA5CE20.tolist(), [(round(p.x, 5), round(p.y, 5)) for p in pts]


def table(coords, src, dst):
    """Durations in seconds from coords[src] to coords[dst] (index lists)."""
    use = sorted(set(src) | set(dst))
    pos = {i: k for k, i in enumerate(use)}
    url = OSRM + ";".join(f"{x},{y}" for x, y in (coords[i] for i in use))
    params = {"sources": ";".join(str(pos[i]) for i in src),
              "destinations": ";".join(str(pos[i]) for i in dst), "annotations": "duration"}
    for attempt in range(4):
        r = requests.get(url, params=params, timeout=120)
        if r.ok and r.json().get("code") == "Ok":
            return np.array(r.json()["durations"], dtype=float)
        time.sleep(2 ** (attempt + 1))
    r.raise_for_status()
    raise RuntimeError(r.text[:200])


def main():
    zips, coords = points()
    n = len(zips)
    minutes = np.full((n, n), np.nan)
    blocks = [list(range(i, min(i + BLOCK, n))) for i in range(0, n, BLOCK)]
    for a in blocks:
        for b in blocks:
            minutes[np.ix_(a, b)] = table(coords, a, b) / 60
            time.sleep(1)
    np.fill_diagonal(minutes, 0)
    pd.DataFrame(minutes, index=zips, columns=zips).round(1).rename_axis("from").to_csv(ROOT / "data/processed/drive_minutes.csv")

    whole = np.nan_to_num(np.round(minutes), nan=255).clip(0, 255).astype(np.uint8)
    site = {"zips": zips, "cap": 255, "minutes": base64.b64encode(whole.tobytes()).decode()}
    path = ROOT / "output/site/chicago-home-value-drive.json"
    path.write_text(json.dumps(site, separators=(",", ":")))
    print(f"{n} zips, {int(np.isnan(minutes).sum())} missing pairs; median {np.nanmedian(minutes):.0f} min; "
          f"wrote {path} ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
