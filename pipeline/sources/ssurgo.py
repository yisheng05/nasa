"""USDA NRCS SSURGO via Soil Data Access: area-weighted soil properties for a polygon."""

from __future__ import annotations

import pandas as pd
import requests

SDA = "https://sdmdataaccess.sc.egov.usda.gov/tabular/post.rest"
NUMERIC = ("aws0100wta", "slopegradwta", "om_r", "kwfact")
CATEGORICAL = ("muname", "drclassdcd", "hydgrpdcd")


def _query(sql: str) -> pd.DataFrame:
    r = requests.post(SDA, json={"query": sql, "format": "JSON+COLUMNNAME"}, timeout=120)
    r.raise_for_status()
    rows = r.json().get("Table", [])
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows[1:], columns=rows[0])


def field_soils(geom_wgs84) -> tuple[pd.DataFrame, dict]:
    """Map units intersecting the field with area shares, and an area-weighted summary."""
    areas = _query(
        f"""~DeclareGeometry(@aoi)~
SELECT @aoi = geometry::STGeomFromText('{geom_wgs84.wkt}', 4326);
SELECT P.mukey, SUM(P.mupolygongeo.STIntersection(@aoi).STArea()) AS area
FROM mupolygon P WHERE P.mupolygongeo.STIntersects(@aoi) = 1 GROUP BY P.mukey"""
    )
    if areas.empty:
        return areas, {}
    keys = ",".join(f"'{k}'" for k in areas["mukey"])
    attrs = _query(
        f"""SELECT M.mukey, M.muname, A.drclassdcd, A.hydgrpdcd, A.aws0100wta, A.slopegradwta, H.om_r, H.kwfact
FROM mapunit M
JOIN muaggatt A ON A.mukey = M.mukey
LEFT JOIN component C ON C.mukey = M.mukey AND C.cokey = (
    SELECT TOP 1 C2.cokey FROM component C2 WHERE C2.mukey = M.mukey ORDER BY C2.comppct_r DESC)
LEFT JOIN chorizon H ON H.cokey = C.cokey AND H.chkey = (
    SELECT TOP 1 H2.chkey FROM chorizon H2 WHERE H2.cokey = C.cokey ORDER BY H2.hzdept_r)
WHERE M.mukey IN ({keys})"""
    )
    df = areas.merge(attrs, on="mukey", how="left")
    for c in ("area", *NUMERIC):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["share"] = df["area"] / df["area"].sum()
    df = df.sort_values("share", ascending=False).drop(columns="area").reset_index(drop=True)
    summary: dict = {}
    for c in NUMERIC:
        ok = df[c].notna()
        summary[c] = (
            round(float((df.loc[ok, c] * df.loc[ok, "share"]).sum() / df.loc[ok, "share"].sum()), 3) if ok.any() else None
        )
    for c in CATEGORICAL:
        summary[c] = df.groupby(c)["share"].sum().idxmax() if df[c].notna().any() else None
    summary["dominant_share"] = round(float(df["share"].iloc[0]), 3)
    summary["n_map_units"] = len(df)
    return df, summary
