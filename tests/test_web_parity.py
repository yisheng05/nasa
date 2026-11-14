"""The standalone page (app/web/field_shift.html) ranks options exactly as pipeline/engine3.py does."""

import itertools
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from pipeline import engine3 as E3

PAGE = Path(__file__).resolve().parent.parent / "app" / "web" / "field_shift.html"


@pytest.mark.skipif(shutil.which("node") is None or not PAGE.exists(), reason="needs node and a built page (python app/build_web.py)")
def test_js_ranking_matches_python(tmp_path):
    html = PAGE.read_text()
    data = json.loads(re.search(r"const DATA = (\{.*?\});\nconst E3", html, re.DOTALL).group(1))
    logic = re.search(r"/\* -+ Engine 3 logic.*?\*/(.*?)/\* -+ header", html, re.DOTALL).group(1)
    cases = []
    for f in data["fields"]:
        for perm in itertools.permutations(E3.PRIORITIES):
            for cons in ([], ["small_grain_market"], ["cover_termination"]):
                kept, _ = E3.apply_constraints(set(cons))
                p = list(perm[:3])
                cases.append({"f": f["id"], "p": p, "c": cons, "py": [c["id"] for c in E3.rank(f["e3"]["ratings"], kept, p)],
                              "wi": E3.what_if(f["e3"]["ratings"], kept, p)})
    script = tmp_path / "parity.js"
    script.write_text(
        "const E3=" + json.dumps(data["engine3"]) + ";const F=" + json.dumps({f["id"]: f["e3"]["ratings"] for f in data["fields"]}) + ";\n" + logic
        + "\nconst cases=" + json.dumps(cases) + ";let bad=0;for(const c of cases){const [k]=applyConstraints(new Set(c.c));"
        "if(JSON.stringify(rank(F[c.f],k,c.p).map(x=>x.id))!==JSON.stringify(c.py)||JSON.stringify(whatIf(F[c.f],k,c.p))!==JSON.stringify(c.wi))bad++;}console.log(bad);"
    )
    out = subprocess.run(["node", str(script)], capture_output=True, text=True, check=True).stdout.strip()
    assert out == "0"
