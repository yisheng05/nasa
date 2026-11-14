"""SMAP L4 root-zone soil moisture from AppEEARS point-request CSVs (3-hourly -> daily mean)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_points(folders: list[Path]) -> dict[str, pd.Series]:
    """Daily mean root-zone soil moisture (m3/m3) per point ID from AppEEARS SPL4SMGP CSVs."""
    frames = []
    for folder in folders:
        for p in folder.rglob("*.csv"):
            head = pd.read_csv(p, nrows=0).columns
            col = next((c for c in head if "sm_rootzone" in c.lower()), None)
            if col is None or "Date" not in head or "ID" not in head:
                continue
            df = pd.read_csv(p, usecols=["ID", "Date", col]).rename(columns={col: "sm"})
            frames.append(df)
    if not frames:
        return {}
    df = pd.concat(frames)
    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
    df = df[df["sm"] > -1]  # drop fill values
    daily = df.groupby(["ID", "Date"])["sm"].mean()
    return {fid: s.droplevel(0).rename("smap_rootzone") for fid, s in daily.groupby(level=0)}
