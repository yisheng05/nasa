# app/

Streamlit shell for the user flow in handoff §13.1. It reads only `data/processed/<field_id>/` (written by `notebooks/01_precompute.ipynb`), so the demo never depends on a live API.

```bash
streamlit run app/streamlit_app.py
```

| Tab | Shows now | Waiting on |
|---|---|---|
| Field history | Ten-season strip: crop, no-living-cover months (Engine 1), stress at the sensitive stage (Engine 2); HLS greenness with the smoothed curve | — |
| Changing conditions | 1981–2025 regional trends vs the 1991–2020 band; Engine 2 stress recurrence vs its 1991–2020 base rate | SMAP L4 confirmation (V11) |
| Rotation options | Engine 3 trade-off table, ranking by priorities, what-if stability, evidence and verify notes per cell | Agronomist review of the crop catalogue |
| Your inputs | Editable crop history (farmer entries marked), SSURGO soil, map | Saving soil-test overrides |
| Summary | One-page markdown with soil cover, stress, ranked options and verify list; downloadable | — |

Files: `data.py` (pure loaders and derived tables), `charts.py` (Altair; palette validated for colour-vision deficiency, light theme pinned in `.streamlit/config.toml`), `streamlit_app.py` (layout). Tests: `tests/test_app_smoke.py` (renders, constraint filter, V9 ordering).

## Standalone page

`python app/build_web.py` builds `app/web/field_shift.html`: one self-contained page with the same precomputed results, which runs in a browser or as a Claude artifact without a server. Engine 3's constraint filter and priority ranking run in the page; `tests/test_web_parity.py` checks they match `pipeline/engine3.py` exactly. Rebuild it after rerunning the notebook.
