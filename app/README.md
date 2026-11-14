# app/

Streamlit shell for the user flow in handoff §13.1. It reads only `data/processed/<field_id>/` (written by `notebooks/01_precompute.ipynb`), so the demo never depends on a live API.

```bash
streamlit run app/streamlit_app.py
```

| Tab | Shows now | Waiting on |
|---|---|---|
| Field history | Ten-season crop strip (CDL, or farmer edits) | HLS greenness (AppEEARS), Engine 1 cover days, Engine 2 stress flags |
| Changing conditions | 1981–2025 window rainfall, root-zone wetness, Tmax, hot days vs the 1991–2020 band; this field's corn seasons as percentiles | Engine 2 (estimated silking dates instead of the calendar window) |
| Rotation options | Three candidates, hard constraints applied, rows ordered by priorities | Engine 3 ratings and confidence |
| Your inputs | Editable crop history (farmer entries marked), SSURGO soil, map | Saving soil-test overrides |
| Summary | One-page markdown, downloadable | Engine outputs |

Files: `data.py` (pure loaders and derived tables), `charts.py` (Altair; palette validated for colour-vision deficiency, light theme pinned in `.streamlit/config.toml`), `streamlit_app.py` (layout). Tests: `tests/test_app_smoke.py` (renders, constraint filter, V9 ordering).
