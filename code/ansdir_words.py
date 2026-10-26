"""Honesty heads step 2, P7 follow-up (2026-10-24): his direction rebuilt from chosen answer-word classes only.
Like persona_rep.py ansdir (per class: resist mean minus lie mean of each unit's span-averaged value; the direction =
the equal-weight mean over the classes), but on every usable item of the family (select + test: the persona test does
not use his held-out lies) and with the classes given:
  python ansdir_words.py ITEMS.json OUT_DIR [--family rp] [--sets yesno=yes,no other=other] [--model PATH] [--device xpu]
-> OUT_DIR/delta_A_<family>_<set>.pt per set (steer.py natural's format: "h", "n" per layer), and the cosine of each with
his original and answer-balanced directions over every head. A class is the polarity of the answer the model gives
(lies: the lie token; resists: the truth token), as persona_rep.said."""
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
    p.add_argument("--sets", default="yesno=yes,no other=other")
    p.add_argument("--span", type=int, default=9)
    p.add_argument("--model", default=str(Path.home() / "models" / "qwen3.5-9b-hf"))
    p.add_argument("--device", default="xpu")
    p.add_argument("--dtype", default="bfloat16")
    p.add_argument("--compare", default="results/delta_A_rp.pt,out/step2/ansdir/delta_A_rp_answer.pt")
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    model, tok = E.load(a.model, a.dtype, a.device)
    eng = E.Engine(model)
    items = json.load(open(a.items, encoding="utf-8"))
    cells = {}
    for lab in ("lie", "resist"):
        for r in S.nat_recs(eng, tok, items, a.family, ["select", "test"], lab, 10_000, a.span, True):
            cells.setdefault((lab, PR.said(r["it"], lab)), []).append(r["mean"])
    counts = {f"{lab} {k}": len(v) for (lab, k), v in sorted(cells.items())}
    E.log(f"classes {counts}")
    flat = lambda d: torch.cat([x.flatten().double() for x in d["h"]])
    refs = {Path(c).name: flat(torch.load(c, weights_only=False)) for c in a.compare.split(",") if c}
    for spec in a.sets.split():
        name, words = spec.split("=")
        ks = [k for k in words.split(",") if ("lie", k) in cells and ("resist", k) in cells]
        mean = lambda c, kind, l: sum(x[kind][l] for x in c) / len(c)
        d = {kind: [(sum(mean(cells["resist", k], kind, l) - mean(cells["lie", k], kind, l) for k in ks) / len(ks)).float()
                    for l in range(len(cells["lie", ks[0]][0][kind]))] for kind in ("h", "n")}
        h = flat(d)
        info = {"classes": ks, "items": {k: v for k, v in counts.items() if k.split()[1] in ks},
                "splits": "select+test", "norm_heads": float(h.norm()),
                "cos": {n: round(float(h @ r / (h.norm() * r.norm())), 4) for n, r in refs.items()}}
        f = out / f"delta_A_{a.family}_{name}.pt"
        torch.save({**d, "info": info, "P": a.span, "source": [a.family]}, f)
        E.log(f"{f.name}: {json.dumps(info)}")


if __name__ == "__main__":
    main()
