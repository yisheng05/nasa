"""Crop and cover-crop characteristics used by Engine 3 (handoff §8.3).

Qualitative on purpose: Engine 3 makes ordinal comparisons, so the catalogue records
direction and timing, not yields or rates. Each entry names the kind of source it rests
on; the team should confirm every entry with an agronomist or extension specialist
before the demo (handoff §16.2).

Sources (general guidance, not field-specific forecasts):
- ISU: Iowa State University Extension and Outreach (corn and soybean growth stages,
  cover crop management, cereal rye termination ahead of corn).
- PFI: Practical Farmers of Iowa (small grains in Iowa rotations, oats with red clover).
- SARE: Managing Cover Crops Profitably, 3rd ed. (cover crop functions and trade-offs).
- MCCC: Midwest Cover Crops Council (cover crop selection for the Midwest).
"""

from __future__ import annotations

CATALOGUE: dict[str, dict] = {
    "corn": {
        "group": "warm-season grass",
        "sensitive_stage": "silking to early grain fill (R1-R2), typically mid to late July in central Iowa",
        "sensitive_months": (7, 8),
        "nitrogen": "high requirement; benefits from a preceding legume",
        "residue": "high",
        "winter_cover": "none",
        "sources": ["ISU"],
    },
    "soybeans": {
        "group": "legume",
        "sensitive_stage": "pod set to seed fill (R3-R6), typically late July to August",
        "sensitive_months": (7, 8),
        "nitrogen": "fixes its own nitrogen; leaves a credit for the following corn",
        "residue": "low and fragile",
        "winter_cover": "none",
        "sources": ["ISU"],
    },
    "oats": {
        "group": "cool-season grass (small grain)",
        "sensitive_stage": "heading to grain fill, typically June; harvested in July",
        "sensitive_months": (6, 6),
        "nitrogen": "low requirement",
        "residue": "moderate (straw can be baled)",
        "winter_cover": "nurse crop for red clover, which covers the soil after oat harvest",
        "sources": ["PFI", "ISU"],
    },
    "cereal rye": {
        "group": "cool-season grass (cover)",
        "role": "winter cover crop",
        "living_cover": "establishes after harvest, overwinters, grows again in spring until terminated",
        "nitrogen": "takes up leftover nitrate; can tie up nitrogen ahead of corn if terminated late",
        "water": "uses spring soil water before termination; can matter in a dry spring",
        "management": "seed in autumn after harvest; terminate in spring, well ahead of corn planting (ISU guidance is commonly ~10-14 days)",
        "sources": ["ISU", "SARE", "MCCC"],
    },
    "red clover": {
        "group": "legume (cover)",
        "role": "underseeded or frost-seeded with oats",
        "living_cover": "covers the soil from oat harvest through autumn and into the next spring",
        "nitrogen": "legume; leaves a nitrogen credit for the following corn",
        "management": "establish with the oats; terminate before corn the following spring",
        "sources": ["PFI", "SARE"],
    },
}

SOURCE_NAMES = {
    "ISU": "Iowa State University Extension and Outreach",
    "PFI": "Practical Farmers of Iowa",
    "SARE": "SARE, Managing Cover Crops Profitably (3rd ed.)",
    "MCCC": "Midwest Cover Crops Council",
}
