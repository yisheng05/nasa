# Field Shift V2: what changed and why

V2 is a guided rotation plan for the farmer, built from the same evidence as V1 (`data/processed`). V1 stays as built; V2 is a separate page (`python app/build_v2.py` writes `app/web/field_shift_v2.html`).

| What V1 taught us | What V2 does |
|---|---|
| The satellite cannot tell a planted cover from weeds or volunteers, or why a season ran late | Step 2, "Tell us what the satellite can’t see": the farmer marks each green-after-harvest autumn as a planted cover, weeds or not sure. Weeds are left out of the local cover effect, and every estimate, rating and the starting field recompute live. Late-looking corn years get a planting-date question that shapes the agronomist questions |
| A farmer manages a farm, not one field | Step 1 shows all three fields side by side, with the field that has most to gain marked "Start a rye trial here" |
| "Rotation picks the crop" was a claim, not a picture | Step 3, the season calendar: each option’s crops, planned covers and bare soil by month, each crop’s sensitive stage, and this farm’s share of days above 30 °C by half-month (NASA POWER, 2016–2025) |
| The water rating rested on "at least one flagged season" | The water rating now compares measured exposure: heat and root-zone wetness inside each crop’s sensitive stage. On these fields June (oats) has wetter soil (0.59 vs 0.53) and slightly fewer hot days (31% vs 40%) than the corn and soybean stages, so oats + red clover rates better; the hottest half-month is 16–31 July, on corn silking |
| Erosion importance was shown but unused | The erosion evidence states the size of the benefit on these flat fields (small) |
| The tool stopped at a ranking | Step 5, "Your plan": the farmer chooses; Field Shift suggests where to start small and when (rye after a corn harvest so it precedes soybeans; oats after soybeans), a season-by-season checklist, questions for the agronomist, and what it will check next season |

Unchanged from V1, on purpose: ordinal ratings against the current rotation, priorities that reorder but never re-rate (the same ranking code), no yield or income forecasts, and the validation results (`docs/validation_results.md`).

Limits that still apply: three neighbouring fields and ten seasons; cover-crop and oat timings in the calendar are planned, typical timings, not measured; vigour is greenness, not yield; the crop traits and rules await an agronomist’s review.

Tests: `tests/test_v2.py` checks the model against Engines 1–3 and V1, and runs the page’s live logic in Node against the Python model for every combination of the farmer’s answers.
