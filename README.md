# Field Shift: rotation options from a field's own history

NASA Space Apps 2026 · Challenge: [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=details) · Hackathon 14–15 November 2026

> **Show what the field has done, what is changing, and what each rotation trades off. Leave the choice with the farmer.**

We reconstruct a field's last 6–10 seasons from 30 m NASA HLS imagery: what it grew, when it grew, how long the soil went without living cover, and where stress recurred at sensitive crop stages. We add local climate trends, soil information and the farmer's own priorities. Then we compare 2–4 candidate rotations as explicit trade-offs, each with its evidence and confidence. The tool does not name a single "optimal" rotation, and it does not claim to measure soil carbon or nutrients from space.

The full design is in [`docs/handoff_v2.md`](docs/handoff_v2.md).

## The six questions the tool answers

| # | Question | Evidence |
|---|---|---|
| 1 | What has this field grown, and when? | Crop sequence (CDL); green-up, peak and harvest per season (HLS) |
| 2 | How long was the soil covered, and by living plants? | Days with and without living cover; winter green cover |
| 3 | Where did stress recur, and at which crop stage? | Expected vs observed development; deficits near sensitive stages |
| 4 | How are conditions changing here? | Trends in heat, rainfall and root-zone moisture (POWER, SMAP L4) |
| 5 | What do the soil and the farmer's priorities rule in or out? | SSURGO soil properties; stated priorities and constraints |
| 6 | How do candidate rotations compare, and how sure are we? | Trade-off table with evidence and confidence |

## Status: pre-event setup only

The 2022 Space Apps FAQ asked teams to start the actual work when the hackathon begins. Until the 2026 Project Submission and Judging & Awards guides come out on **13 November**, this repo holds only learning material, setup and data-access checks. There is no engine, index or analysis code yet. Record the 2026 answers in [`docs/rules_check_2026.md`](docs/rules_check_2026.md).

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

## Repo map

| Path | What goes here | Handoff section |
|---|---|---|
| `docs/` | Handoff v2 and the 2026 rules checklist | — |
| `prep/` | Pre-event data-access checks | §18.2 |
| `notebooks/` | Offline precompute of the demo fields → evidence JSON/Parquet | §14 |
| `pipeline/` | Engine 1 Field History, Engine 2 Stress Recurrence, Engine 3 Rotation Comparison | §8 |
| `app/` | Streamlit UI: season strip, trend panel, trade-off table, one-page summary | §13.1 |
| `tests/` | Acceptance tests V1–V10 | §15 |
| `data/` | Raw extracts and precomputed evidence (git-ignored) | §14 |
| `REFERENCES.md` | Data, papers, code and AI tools used, for the submission form | §1.4 |

## Pre-event checklist (handoff §18.2)

- [ ] Confirm the challenge text and the **Resources** tab on the challenge page. Use or cite every NASA dataset listed there.
- [ ] Read the 2026 Project Submission and Judging & Awards guides (13 Nov) and fill in `docs/rules_check_2026.md`.
- [ ] Earthdata Login and AppEEARS working for every team member who needs them (`prep/check_access.py` shows PASS on the login check).
- [x] HLS VI coverage for 2016–2025 on the central Iowa tile (T15TVG). Checked 9 Nov: VI granules match surface reflectance in every year (L30 515/516, S30 958/962), so the precomputed VI products can be used.
- [x] MSLSP30NA period. Checked 9 Nov: the CMR temporal extent is 2016-01-01 to 2019-12-31, with one granule per year at the point. V3 validation is limited to those four years.
- [ ] Agree the region and the decision. Iowa corn–soybean is recommended (§3.2).
- [ ] Line up an agronomist or extension contact for the weekend.

## Before making this repo public

Space Apps submissions usually link to a public repo. `docs/handoff_v2.md` includes competitive positioning that names other teams (§2). Review `docs/` before you change the repo's visibility.
