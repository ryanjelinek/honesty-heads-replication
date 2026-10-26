"""Honesty heads step 2 (2026-10-24): scenarios-pilot.md -> scenarios JSON for gen_pairs.py.
  python scenarios_to_json.py scenarios-pilot.md scenarios-pilot.json
Each "### sNN — honest answer: Yes|No [(edited by Ryan)]" block gives id, honest, scenario, question, prefill (the reply
label) and author (the file's author line; "(edited by Ryan)" in a heading adds Ryan)."""
import json
import re
import sys

src = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"\*\*Author: ([^*]+?),", src)
author = m.group(1).strip() if m else "Ryan"
out = []
for block in re.split(r"^### ", src, flags=re.M)[1:]:
    head = re.match(r"(s\d+)\s+—\s+honest answer:\s+(Yes|No)(.*)", block.splitlines()[0])
    if not head:
        continue
    field = {k: re.search(rf"- \*\*{k}:\*\* (.+)", block) for k in ("Scenario", "Question", "Reply label")}
    if not all(field.values()) or not field["Scenario"].group(1).strip().startswith("You"):
        sys.exit(f"{head.group(1)}: a field is empty or the scenario doesn't start with 'You'")
    out.append({"id": head.group(1), "honest": head.group(2),
                "scenario": field["Scenario"].group(1).strip(), "question": field["Question"].group(1).strip(),
                "prefill": field["Reply label"].group(1).strip(),
                "author": author + (" + Ryan (edited)" if "edited by Ryan" in head.group(3) else "")})
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"{len(out)} scenarios, honest Yes {sum(s['honest'] == 'Yes' for s in out)} / No "
      f"{sum(s['honest'] == 'No' for s in out)} -> {sys.argv[2]}")
