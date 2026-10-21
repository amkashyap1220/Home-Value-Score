"""Zip code shapes for the value map on alexanderk.dev.

Census 2020 ZCTA cartographic boundaries (1:500,000), cut to the 380 in-scope zips and
simplified as one coverage, so neighbouring zips keep sharing their borders. Coordinates
are rounded to 4 decimals (about 10 m), plenty for a map this size.

Output: output/site/chicago-home-value-zips.json (GeoJSON)
"""
import json

import geopandas as gpd
import pandas as pd
import shapely

from fetch import ROOT, fetch

URL = "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip"
TOLERANCE = 0.002   # degrees, about 200 m


def main():
    zips = pd.read_csv(ROOT / "data/processed/zips.csv", dtype=str)
    shapes = gpd.read_file(fetch(URL), columns=["ZCTA5CE20"])
    shapes = shapes[shapes.ZCTA5CE20.isin(zips.zcta)].to_crs(4326).reset_index(drop=True)
    shapes["geometry"] = shapely.coverage_simplify(shapes.geometry.values, TOLERANCE)
    shapes["geometry"] = shapely.set_precision(shapes.geometry.values, 1e-4)
    features = [{"type": "Feature", "id": z, "geometry": json.loads(shapely.to_geojson(g))}
                for z, g in zip(shapes.ZCTA5CE20, shapes.geometry) if not g.is_empty]
    path = ROOT / "output/site/chicago-home-value-zips.json"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")))
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB, {len(features)} of {len(zips)} zips)")


if __name__ == "__main__":
    main()
