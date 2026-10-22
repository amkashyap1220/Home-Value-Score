"""Crime rates within Chicago, by zip (added 2026-10-22).

The pre-registered safety indicator (src/crime.py) gives every zip the rate of one police
agency. Chicago has one agency, so all 56 Chicago zips got the same rate (33.8 crimes per
1,000), from the Loop to Lincoln Park to Englewood. That made safety useless inside the
city, and the value model could not tell Chicago neighborhoods apart.

This script keeps the FBI's citywide total and spreads it over the Chicago zips in
proportion to where the city's own incident data puts the same kinds of offenses:

  1. City of Chicago Data Portal, "Crimes - 2001 to Present", incidents in YEAR (2025)
     whose type matches the FBI's violent and property offenses: homicide, criminal sexual
     assault, robbery, aggravated assault and battery, burglary, theft, motor vehicle theft
     and arson. Simple assault and battery, criminal damage, fraud, drugs and the rest are
     left out, as in the FBI counts.
  2. Each incident with a location is placed in a zip (Census 2020 ZCTA boundaries).
  3. A Chicago zip's offenses = the FBI's Chicago total x its share of the portal incidents.
  4. Rate = offenses / the zip's population living in Chicago (2020 Census, the zip's
     population x the share living in Chicago from src/places.py) x 1,000.

The citywide rate therefore matches the FBI number exactly; only its spread across zips
comes from the portal. Incidents are counted where they happen, not where victims live,
so the Loop and other places with many visitors and few residents get very high rates.

Output: data/processed/chicago_crime.csv (zcta, portal_incidents, chicago_pop, crimes_per_1000_local)
"""
import pandas as pd
import pyogrio
import shapely

from fetch import ROOT, fetch

YEAR = 2025
PORTAL = "https://data.cityofchicago.org/resource/ijzp-q8t2.csv"
ZCTA = "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip"
VIOLENT = ["HOMICIDE", "CRIMINAL SEXUAL ASSAULT", "ROBBERY"]
PROPERTY = ["BURGLARY", "THEFT", "MOTOR VEHICLE THEFT", "ARSON"]
AGGRAVATED = ["ASSAULT", "BATTERY"]   # only the aggravated kinds count, as in the FBI's aggravated assault


def incidents():
    types = ", ".join(f"'{t}'" for t in VIOLENT + PROPERTY + AGGRAVATED)
    query = (f"?$select=primary_type,description,latitude,longitude"
             f"&$where=year={YEAR} AND primary_type in ({types}) AND latitude IS NOT NULL&$limit=1000000")
    df = pd.read_csv(fetch(PORTAL + query, name=f"chicago_crimes_{YEAR}.csv"))
    keep = ~df.primary_type.isin(AGGRAVATED) | df.description.str.startswith("AGG")
    return df[keep]


def main():
    ind = pd.read_csv(ROOT / "data/processed/indicators.csv", dtype={"zcta": str})
    places = pd.read_csv(ROOT / "data/processed/places.csv", dtype={"zcta": str})
    agencies = pd.read_csv(ROOT / "data/processed/crime_agencies.csv")
    cpd = agencies[agencies.agency_name == "Chicago Police Department"].iloc[0]
    fbi_total = cpd.violent + cpd.property

    chicago = ind[ind.place_name == "Chicago"].merge(places[["zcta", "place_share"]], on="zcta")
    shapes = pyogrio.read_dataframe(fetch(ZCTA), columns=["ZCTA5CE20"]).to_crs(4326)
    shapes = shapes[shapes.ZCTA5CE20.isin(chicago.zcta)].reset_index(drop=True)

    inc = incidents()
    pts = shapely.points(inc.longitude.values, inc.latitude.values)
    tree = shapely.STRtree(shapes.geometry.values)
    pt_idx, shape_idx = tree.query(pts, predicate="within")
    counts = pd.Series(shapes.ZCTA5CE20.values[shape_idx]).value_counts()
    placed = len(set(pt_idx))

    out = chicago[["zcta", "pop2020", "place_share"]].copy()
    out["portal_incidents"] = out.zcta.map(counts).fillna(0).astype(int)
    out["chicago_pop"] = (out.pop2020 * out.place_share).round()
    out["offenses"] = fbi_total * out.portal_incidents / counts.reindex(out.zcta).sum()
    out["crimes_per_1000_local"] = out.offenses / out.chicago_pop * 1000
    out[["zcta", "portal_incidents", "chicago_pop", "crimes_per_1000_local"]].to_csv(
        ROOT / "data/processed/chicago_crime.csv", index=False, float_format="%.5g")

    print(f"portal incidents {YEAR}: {len(inc)}, placed in a Chicago zip: {placed}; FBI total {fbi_total}")
    print("citywide check:", round(out.offenses.sum() / out.chicago_pop.sum() * 1000, 2), "vs FBI", cpd.crimes_per_1000)
    print(out.sort_values("crimes_per_1000_local")[["zcta", "chicago_pop", "portal_incidents", "crimes_per_1000_local"]]
          .round(1).to_string(index=False))


if __name__ == "__main__":
    main()
