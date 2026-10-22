"""Distance from each zip to the nearest train station, for the value map (added
2026-10-22 at Alex's request; see the change log in docs/decisions.md).

Stations: every Metra station, every CTA 'L' station and every South Shore Line
station (including the West Lake line), from the agencies' own published data.
Amtrak-only stations are left out.

Distance is measured from where people live, not from the middle of the zip: the
Census 2020 population center of each block group whose center falls inside the zip,
and the zip's value is the population-weighted average of their straight-line
distances to the nearest station. A zip with no block-group center inside it uses its
representative point (the same point as src/commute.py). Straight-line miles, not
walking or driving distance.

Outputs:
  data/processed/stations.csv   one row per station: agency, name, lat, lon
  data/processed/station_distance.csv   zcta, station_mi, nearest_station
"""
import io
import json
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd

from fetch import ROOT, fetch
from map import URL

P = ROOT / "data/processed"
METRA = "https://schedules.metrarail.com/gtfs/schedule.zip"
CTA_L = "https://data.cityofchicago.org/resource/8pix-ypme.json?$limit=1000"
SOUTH_SHORE = "http://www.mysouthshoreline.com/google/google_transit.zip"
CENPOP = "https://www2.census.gov/geo/docs/reference/cenpop2020/blkgrp/CenPop2020_Mean_BG{}.txt"
EARTH_MI = 3958.8


def gtfs_stops(path):
    with zipfile.ZipFile(path) as z:
        s = pd.read_csv(io.BytesIO(z.read("stops.txt")), dtype=str, skipinitialspace=True)
    s.columns = s.columns.str.strip()
    if "location_type" in s:   # keep stations, not platforms or entrances
        s = s[s.location_type.fillna("0").isin(["0", "1"]) & s.parent_station.isna()]
    return s[["stop_name", "stop_lat", "stop_lon"]].astype({"stop_lat": float, "stop_lon": float})


def stations():
    metra = gtfs_stops(fetch(METRA, "metra_gtfs.zip")).assign(agency="Metra")
    nictd = gtfs_stops(fetch(SOUTH_SHORE, "south_shore_gtfs.zip")).assign(agency="South Shore Line")
    cta = pd.DataFrame(json.loads(fetch(CTA_L, "cta_l_stops.json").read_text()))
    # One row per platform direction; the station is map_id
    cta = cta.groupby("map_id").agg(stop_name=("station_name", "first"),
                                    stop_lat=("location", lambda x: float(x.iloc[0]["latitude"])),
                                    stop_lon=("location", lambda x: float(x.iloc[0]["longitude"]))).reset_index(drop=True)
    cta["agency"] = "CTA"
    out = pd.concat([metra, cta, nictd], ignore_index=True)
    out.columns = ["name", "lat", "lon", "agency"]
    return out[["agency", "name", "lat", "lon"]].round(6)


def nearest(lat, lon, st):
    """Distance in miles to, and index of, the nearest station for each point (haversine)."""
    la, lo = np.radians(lat)[:, None], np.radians(lon)[:, None]
    sla, slo = np.radians(st.lat.values)[None, :], np.radians(st.lon.values)[None, :]
    a = np.sin((sla - la) / 2) ** 2 + np.cos(la) * np.cos(sla) * np.sin((slo - lo) / 2) ** 2
    d = 2 * EARTH_MI * np.arcsin(np.sqrt(a))
    return d.min(axis=1), d.argmin(axis=1)


def main():
    st = stations()
    st.to_csv(P / "stations.csv", index=False)
    print(st.agency.value_counts().to_string())

    zips = pd.read_csv(P / "zips.csv", dtype=str)
    shapes = gpd.read_file(fetch(URL), columns=["ZCTA5CE20"])
    shapes = shapes[shapes.ZCTA5CE20.isin(zips.zcta)].to_crs(4326).rename(columns={"ZCTA5CE20": "zcta"})

    bg = pd.concat([pd.read_csv(fetch(CENPOP.format(s), f"cenpop2020_bg{s}.txt"), encoding="utf-8-sig") for s in ("17", "18")])
    bg = bg[bg.POPULATION > 0]
    bg = gpd.GeoDataFrame(bg, geometry=gpd.points_from_xy(bg.LONGITUDE, bg.LATITUDE), crs=4326)
    bg = gpd.sjoin(bg, shapes, predicate="within")
    bg["mi"], bg["near"] = nearest(bg.LATITUDE.values, bg.LONGITUDE.values, st)
    by = bg.groupby("zcta").apply(lambda g: pd.Series({
        "station_mi": np.average(g.mi, weights=g.POPULATION),
        "nearest_station": st.name.iloc[g.near.iloc[g.POPULATION.values.argmax()]],
    }), include_groups=False)

    # Zips with no block-group center inside: their representative point
    rest = shapes[~shapes.zcta.isin(by.index)]
    pts = rest.geometry.representative_point()
    mi, near = nearest(pts.y.values, pts.x.values, st)
    by = pd.concat([by, pd.DataFrame({"station_mi": mi, "nearest_station": st.name.iloc[near].values}, index=rest.zcta.values)])

    out = by.rename_axis("zcta").reset_index().sort_values("zcta")
    out["station_mi"] = out.station_mi.astype(float).round(2)
    out.to_csv(P / "station_distance.csv", index=False)
    print(f"{len(out)} zips ({len(rest)} from a representative point); miles: "
          + out.station_mi.describe()[["min", "25%", "50%", "75%", "max"]].round(1).to_string().replace("\n", ", "))


if __name__ == "__main__":
    main()
