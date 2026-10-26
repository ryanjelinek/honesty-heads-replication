"""Honesty heads step 2 (2026-10-26): why natneed counts his 29 heads at 16 of his 34 test lies and the
persona run (cross, his heads + his direction) at 18. Both use the same heads, delta (x2 at every position), lies and
metric; the one difference found in the code is how many steering rows share a forward. natneed runs its 3 rows (set,
every head, every head but the set) together; the persona run's 41 rows went in chunks of 512 // prompt length (3 to 5
rows for these 99-149 token prompts), so his arm ran alone or in a pair. This runs his arm on the 34 lies in batches of
1, 2 and 3 rows (3 twice, for run-to-run repeatability) and saves every lie's margin in bits.
  cd ~/honesty-heads && bash guardedpy.sh edge-check step2/edge_check.py out/step2/edge_check.json"""
import json
import os
import sys

os.environ["DCORE_ROW_TOKENS"] = "4096"       # every shape below runs as one forward
sys.path.insert(0, "code")
import torch  # noqa: E402

import engine as E  # noqa: E402
import steer as S  # noqa: E402

hs = json.load(open("results/heads_nat.json"))
model, tok = E.load("$HOME/models/qwen3.5-9b-hf", "bfloat16", "xpu")
eng = E.Engine(model)
dz = torch.load("results/delta_A_rp.pt", weights_only=False)
dl = {k: dz[k] for k in ("h", "n")}
core = {(u["layer"], u["index"]) for u in hs["heads"]}
allh = [(l, i) for l in range(eng.L) for i in range(eng.nheads[l])]
mk_set = S.masks(eng, [("h", *h) for h in core])
mk_all = S.masks(eng, [("h", *h) for h in allh])
mk_but = S.masks(eng, [("h", *h) for h in allh if h not in core])
items = json.load(open("step2/items_rp_ry.json"))
items = items["items"] if isinstance(items, dict) else items
recs = S.nat_recs(eng, tok, items, "rp", ["test"], "lie", 40, hs["P"])
# (rows in the forward, index of his set's row); "natneed" is natneed's own row order
shapes = {"alone": ([mk_set], 0), "pair": ([mk_all, mk_set], 1), "natneed": ([mk_set, mk_all, mk_but], 0),
          "natneed_again": ([mk_set, mk_all, mk_but], 0)}
res = {"ids": [r["it"]["id"] for r in recs], "len": [len(r["ids"]) for r in recs], "m": [r["m"] for r in recs]}
for name, (mks, j) in shapes.items():
    out = []
    for r in recs:
        lp = S.run_rows(eng, r["ids"], S.Shift(eng, dl, [(2.0, m) for m in mks], 0, True))
        out.append(round(eng.metric(lp[j], r["lie"], r["truth"]), 4))
    res[name] = out
    E.log(f"{name:14s} rows {len(mks)}: {sum(v < 0 for v in out)} of {len(out)} lies flipped")
json.dump(res, open(sys.argv[1], "w"), indent=1)
E.log(f"-> {sys.argv[1]}")
