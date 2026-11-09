# pipeline/

Empty until the event (Sat 14 Nov). Planned modules, from handoff §8:

- **Engine 1: Field History** (§8.1): crop sequence, phenometrics, living-cover days, winter-cover flag, per season.
- **Engine 2: Stress Recurrence** (§8.2): capped GDD, stage estimates, day-of-year anomalies, stress-window flags, relative vigour within each crop, recurrence.
- **Engine 3: Rotation Comparison** (§8.3): hard constraints, ordinal ratings relative to the current rotation, priority ordering, sensitivity to priority changes.

Every engine writes to one evidence JSON, and every number carries its source dataset and date.
