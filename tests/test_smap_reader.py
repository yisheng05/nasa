"""SMAP L4 point CSVs from AppEEARS: timezone-aware 3-hourly rows -> naive daily means per point."""

import pandas as pd

from pipeline.sources import smap


def test_reads_appeears_point_csv(tmp_path):
    d = tmp_path / "fieldshift_smap_l4_2015_2020_v2"
    d.mkdir()
    (d / "x-SPL4SMGP-008-results.csv").write_text(
        "Category,ID,Latitude,Longitude,Date,SMAP_Tile,SPL4SMGP_008_Line_Y_9.00805km,SPL4SMGP_008_Sample_X_9.00805km,SPL4SMGP_008_Geophysical_Data_sm_rootzone\n"
        "demo,field_a,42.04,-93.43,2015-04-01 01:30:00 UTC,h00v00,267.0,927.0,0.30\n"
        "demo,field_a,42.04,-93.43,2015-04-01 04:30:00 UTC,h00v00,267.0,927.0,0.32\n"
        "demo,field_a,42.04,-93.43,2015-04-02 01:30:00 UTC,h00v00,267.0,927.0,-9999\n"
        "demo,field_b,42.06,-93.41,2015-04-01 01:30:00 UTC,h00v00,267.0,927.0,0.25\n"
    )
    out = smap.load_points([d])
    assert set(out) == {"field_a", "field_b"}
    a = out["field_a"]
    assert a.index.tz is None
    assert a.loc[pd.Timestamp("2015-04-01")] == 0.31
    assert pd.Timestamp("2015-04-02") not in a.index  # fill value dropped
    assert a["2015-04-01":"2015-04-30"].size == 1  # slicing by naive dates works
