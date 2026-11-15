"""Build the Field Shift V2 page from the committed evidence.

    python app/build_v2.py   ->   app/web/field_shift_v2.html

The ranking logic (orderedCriteria, applyConstraints, rank, whatIf, priorityAction,
stabilityLine) is taken from V1's template at build time, so both versions run the same,
parity-tested code. V2's own live logic (cover effect from the farmer's answers, estimates,
where to start) is in the template and checked against app/v2_model.py by tests/test_v2.py.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import v2_model as V

APP = Path(__file__).resolve().parent
TEMPLATE, V1_TEMPLATE = APP / "v2_template.html", APP / "web_template.html"
OUT = APP / "web" / "field_shift_v2.html"


def e3_logic() -> str:
    t = V1_TEMPLATE.read_text()
    block = re.search(r"/\* -+ Engine 3 logic.*?\*/(.*?)/\* -+ header", t, re.DOTALL).group(1)
    return block.split("function nextSteps")[0]


def build() -> Path:
    data = V.build()
    data["generated"] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str).replace("</", "<\\/")
    html = TEMPLATE.read_text().replace("/*__DATA__*/null", payload).replace("/*__E3_LOGIC__*/", e3_logic())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"wrote {p.relative_to(APP.parent)} ({p.stat().st_size // 1024} KB)")
