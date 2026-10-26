"""Honesty heads step 3, Q0b (2026-10-26): design C, a direction from his truthful replies only (PLAN-step3.md).
Per unit, the span-averaged value of his resist items whose truth token is another word ("other": mostly owning up in a
sentence, 21) minus the equal-weight mean of those whose truth token is Yes and those whose is No (19 together). No lie
item enters, so the direction holds the reply's style and not honesty. Same records and span as ansdir_words.py (every
usable item of the family, select + test; classes by persona_rep.said):
  python cdir_truths.py ITEMS.json OUT_DIR [--family rp] [--model PATH] [--device xpu]
-> OUT_DIR/delta_C_<family>.pt (steer.py natural's format: "h", "n" per layer), and its cosine with his original,
answer-balanced and other-openings directions over every head."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path.home() / "honesty-heads" / "code"))
import engine as E  # noqa: E402
import persona_rep as PR  # noqa: E402
import steer as S  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("items")
    p.add_argument("out")
    p.add_argument("--family", default="rp")
    p.add_argument("--span", type=int, default=9)
    p.add_argument("--model", default=str(Path.home() / "models" / "qwen3.5-9b-hf"))
    p.add_argument("--device", default="xpu")
    p.add_argument("--dtype", default="bfloat16")
    p.add_argument("--compare", default="results/delta_A_rp.pt,out/step2/ansdir/delta_A_rp_answer.pt,"
                                        "out/step2/words/delta_A_rp_other.pt")
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    model, tok = E.load(a.model, a.dtype, a.device)
    eng = E.Engine(model)
    items = json.load(open(a.items, encoding="utf-8"))
    cells = {}
    for r in S.nat_recs(eng, tok, items, a.family, ["select", "test"], "resist", 10_000, a.span, True):
        cells.setdefault(PR.said(r["it"], "resist"), []).append(r["mean"])
    counts = {k: len(v) for k, v in sorted(cells.items())}
    E.log(f"resist classes {counts}")
    assert all(k in cells for k in ("other", "yes", "no")), counts
    flat = lambda d: torch.cat([x.flatten().double() for x in d["h"]])
    refs = {Path(c).name: flat(torch.load(c, weights_only=False)) for c in a.compare.split(",") if c}
    mean = lambda c, kind, l: sum(x[kind][l] for x in c) / len(c)
    n_layers = len(cells["other"][0]["h"])
    d = {kind: [(mean(cells["other"], kind, l) - (mean(cells["yes"], kind, l) + mean(cells["no"], kind, l)) / 2).float()
                for l in range(n_layers)] for kind in ("h", "n")}
    h = flat(d)
    info = {"design": "C: resist other minus the equal-weight mean of resist yes and resist no", "items": counts,
            "splits": "select+test", "norm_heads": float(h.norm()),
            "cos": {n: round(float(h @ r / (h.norm() * r.norm())), 4) for n, r in refs.items()},
            "norm_refs": {n: round(float(r.norm()), 4) for n, r in refs.items()}}
    f = out / f"delta_C_{a.family}.pt"
    torch.save({**d, "info": info, "P": a.span, "source": [a.family]}, f)
    E.log(f"{f.name}: {json.dumps(info)}")


if __name__ == "__main__":
    main()
