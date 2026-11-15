# Field Shift: rotation options from a field's own history

NASA Space Apps 2026 · Challenge: [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=details) · Singapore Local Event (virtual), 14 Nov 9:00 am – 15 Nov 11:59 pm SGT

> **Show what the field has done, what is changing, and what each rotation trades off. Leave the choice with the farmer.**

We reconstruct a field's last 6–10 seasons from 30 m NASA HLS imagery: what it grew, when it grew, how long the soil went without living cover, and where stress recurred at sensitive crop stages. We add local climate trends, soil information and the farmer's own priorities. Then we compare 2–4 candidate rotations as explicit trade-offs, each with its evidence and confidence. The tool does not name a single "optimal" rotation, and it does not claim to measure soil carbon or nutrients from space.

The full design is in [`docs/handoff_v2.md`](docs/handoff_v2.md) (v2.3, 14 Nov; changes listed in its §0.1–0.3). Rules: [`docs/rules_check_2026.md`](docs/rules_check_2026.md).

## The six questions the tool answers

| # | Question | Evidence |
|---|---|---|
| 1 | What has this field grown, and when? | Crop sequence (CDL); green-up, peak and harvest per season (HLS) |
| 2 | How long was the soil covered, and by living plants? | Days with and without living cover; spring green cover |
| 3 | Where did stress recur, and at which crop stage? | Expected vs observed development; deficits near sensitive stages |
| 4 | How are conditions changing here? | Trends in heat, rainfall and root-zone moisture (POWER, SMAP L4) |
| 5 | What do the soil and the farmer's priorities rule in or out? | SSURGO soil properties; stated priorities and constraints |
| 6 | How do candidate rotations compare, and how sure are we? | Trade-off table with evidence and confidence |

## Status

The hackathon is live (from Sat 14 Nov 9:00 am SGT). Product code starts now. Everything committed before then is planning, setup and data-access checks only, because the 2026 Participant FAQ states that teams "are not allowed to begin working on the challenges prior to the hackathon".

### Submission (confirmed by the Singapore Local Lead, 13 Nov)

Deadline **Sun 15 Nov 11:59 pm SGT** (internal: 10:00 pm). Submit on the official Space Apps site:

- **Project Summary:** the solution, the problem and its impact.
- **Project Demo:** a 30-second video **or** 7 slides. We plan 7 slides.
- **Final Project Link:** publicly accessible. Make this repo public first (see below).
- **Project Details:** approach, tools, technologies, NASA datasets with source links and how each is used. Include AI tools from `REFERENCES.md`.

At least one NASA dataset is mandatory for Global Awards. A live API is not required, and a well-presented prototype is acceptable.

### Pre-event log (for disclosure in the submission)

| Date | What | Where |
|---|---|---|
| 6 Nov | Design handoff v2 (product concept, method, validation plan) | `docs/handoff_v2.md` |
| 9 Nov | Repo layout, rules checklist, references, data-access smoke test (no analytics) | commit `21ee8a2` |
| 13 Nov | Handoff v2.1 (2026 rule updates, terminology and method fixes), rules checklist filled from the 2026 FAQ | commit `d38301c` |
| 14 Nov, after 9:00 am SGT start | Handoff v2.2 (Local Lead email) and v2.3 (Resources tab) | commits `9f36104` onward |

Kept as a factual record.

## Setup

Requires Python 3.11 or later.

```bash
python -m venv .venv && source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

```bash
cp .env.example .env   # then add your Earthdata login, or use ~/.netrc
```

```bash
python prep/check_access.py --ancillary
```

The last command checks every NASA data path for central Iowa and prints PASS / WARN / FAIL / SKIP. See [`prep/README.md`](prep/README.md).

Precompute the demo fields, then start the app:

```bash
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/01_precompute.ipynb
```

```bash
streamlit run app/streamlit_app.py
```

Run the tests (V10 GDD, app smoke tests incl. V9 ordering):

```bash
python -m pytest -q
```

Re-check every validation test in handoff §15 (V1–V13) from the committed evidence; this writes [`docs/validation_results.md`](docs/validation_results.md):

```bash
python prep/validate_all.py
```

## Repo map

| Path | What goes here | Handoff section |
|---|---|---|
| `docs/` | Handoff v2, the 2026 rules checklist and the validation results | §15 |
| `prep/` | Data-access checks, the V6 visual-check sheets and `validate_all.py` | §15, §18.2 |
| `notebooks/` | Offline precompute of the demo fields → evidence JSON/Parquet | §14 |
| `pipeline/` | Engine 1 Field History, Engine 2 Stress Recurrence, Engine 3 Rotation Comparison | §8 |
| `app/` | Streamlit UI: season strip, trend panel, trade-off table, one-page summary | §13.1 |
| `tests/` | Unit and acceptance tests (V7, V9, V10, engines, readers, web parity) | §15 |
| `data/` | Raw extracts (git-ignored) and `data/processed/` evidence read by the app (committed) | §14 |
| `REFERENCES.md` | Data, papers, code and AI tools used, for the submission form | §1.4 |

## Pre-event checklist (handoff §18.2)

- [x] Resources tab read (14 Nov) and mapped in handoff §10.1. None of its datasets is mandatory.
- [ ] Compare the challenge Details tab with handoff §1.1.
- [ ] Read the 2026 Project Submission and Judging & Awards guides (13 Nov) and finish `docs/rules_check_2026.md`. The pre-work rule is already confirmed from the 2026 FAQ.
- [x] Submission fields, demo format, NASA-data rule, team size and judging criteria. Confirmed by the Local Lead's email (13 Nov).
- [ ] Earthdata Login and AppEEARS working for every team member who needs them (`prep/check_access.py` shows PASS on the login check).
- [x] HLS VI coverage for 2016–2025 on the central Iowa tile (T15TVG). Checked 9 Nov: VI granules match surface reflectance in every year (L30 515/516, S30 958/962), so the precomputed VI products can be used.
- [x] MSLSP30NA period. Checked 9 Nov: the CMR temporal extent is 2016-01-01 to 2019-12-31, with one granule per year at the point. V3 validation is limited to those four years.
- [ ] Agree the region and the decision. Iowa corn–soybean is recommended (§3.2).
- [ ] Line up an agronomist or extension contact for the weekend.

## Before making this repo public

The Final Project Link must be publicly accessible. `docs/handoff_v2.md` includes competitive positioning that names other teams (§2). Review `docs/` before you change the repo's visibility, and keep the pre-event log: it is the disclosure.
