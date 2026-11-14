"""Growing degree days, maize 86/50 °F method in °C (handoff §7.4, test V10)."""

from __future__ import annotations

import numpy as np

BASE_C = 10.0
CAP_C = 30.0


def gdd_day(tmax, tmin, base: float = BASE_C, cap: float = CAP_C):
    """Daily GDD with Tmax capped at 30 °C and both temperatures floored at the 10 °C base."""
    tmax_adj = np.clip(np.asarray(tmax, dtype=float), base, cap)
    tmin_adj = np.clip(np.asarray(tmin, dtype=float), base, cap)
    return (tmax_adj + tmin_adj) / 2.0 - base


# Purdue NCH-40: ~1,400 °F-GDD to silking and ~2,700 to black layer; /1.8 for °C units.
SILKING_GDD_C = 1400 / 1.8
BLACK_LAYER_GDD_C = 2700 / 1.8
