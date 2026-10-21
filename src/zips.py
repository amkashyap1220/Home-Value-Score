"""The study's zip list: ZCTAs with more than half of their 2020 population in the
13 counties of the Chicago-Naperville-Elgin MSA (2023 definition).

Output: data/processed/zips.csv (zcta, state, main county, population, share in MSA)
"""
import pandas as pd

from fetch import ROOT

MSA_COUNTIES = {
    # Illinois
    "17031": "Cook", "17037": "DeKalb", "17043": "DuPage", "17063": "Grundy",
    "17089": "Kane", "17093": "Kendall", "17097": "Lake", "17111": "McHenry", "17197": "Will",
    # Indiana
    "18073": "Jasper", "18089": "Lake", "18111": "Newton", "18127": "Porter",
}


def main():
    blocks = pd.read_parquet(ROOT / "data/processed/blocks.parquet", columns=["zcta", "county", "pop"])
    blocks = blocks.dropna(subset=["zcta"])
    blocks["in_msa"] = blocks.county.isin(MSA_COUNTIES)
    candidates = blocks.loc[blocks.in_msa, "zcta"].unique()
    b = blocks[blocks.zcta.isin(candidates)]

    by_county = b.groupby(["zcta", "county"], as_index=False)["pop"].sum()
    total = by_county.groupby("zcta")["pop"].sum().rename("pop2020")
    in_msa = by_county[by_county.county.isin(MSA_COUNTIES)].groupby("zcta")["pop"].sum().rename("pop_in_msa")
    main_county = by_county.sort_values("pop").groupby("zcta").tail(1).set_index("zcta")["county"].rename("county_fips")

    z = pd.concat([total, in_msa, main_county], axis=1).fillna({"pop_in_msa": 0}).reset_index()
    z["share_in_msa"] = z.pop_in_msa / z.pop2020
    z["in_scope"] = z.share_in_msa > 0.5
    z["county"] = z.county_fips.map(MSA_COUNTIES)
    z["state"] = z.county_fips.str[:2].map({"17": "IL", "18": "IN", "55": "WI"})
    z = z.sort_values("zcta")
    z.to_csv(ROOT / "data/processed/zcta_msa_overlap.csv", index=False)

    scope = z[z.in_scope & (z.pop2020 > 0)][["zcta", "state", "county_fips", "county", "pop2020", "share_in_msa"]]
    scope.to_csv(ROOT / "data/processed/zips.csv", index=False)
    print(f"{len(z)} ZCTAs touch the MSA; {len(scope)} in scope "
          f"({(scope.state == 'IL').sum()} IL, {(scope.state == 'IN').sum()} IN); "
          f"{z[z.in_scope & (z.pop2020 == 0)].shape[0]} zero-population ZCTAs dropped")
    border = z[(z.share_in_msa > 0.05) & (z.share_in_msa < 0.95)]
    print("border ZCTAs:\n", border[["zcta", "county_fips", "pop2020", "share_in_msa", "in_scope"]].to_string(index=False))


if __name__ == "__main__":
    main()
