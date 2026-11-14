# notebooks/

- `01_precompute.ipynb`: builds per-field inputs and writes them to `data/processed/<field_id>/` (`field_static.json`, `power_daily.parquet`, `hls_obs.parquet` once AppEEARS HLS tasks finish). Safe to re-run: downloads and AppEEARS tasks are cached or found by name.

Run from the repo root:

```bash
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/01_precompute.ipynb
```

Earthdata login (for AppEEARS) is read from `~/.netrc` or `EARTHDATA_USERNAME`/`EARTHDATA_PASSWORD`.
