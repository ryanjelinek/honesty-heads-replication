"""Honesty heads step 2, P6 (2026-10-24): how much of M2's low cosine is noise? Builds resist-minus-lie
directions (over every head, steer.py's delta_nat without bins) from random halves of one family's usable items and
compares them, within a family (the noise ceiling) and across families at the same sizes.
  python split_half.py ITEMS.json OUT.json [--families ry,rp] [--splits 50] [--model PATH] [--device xpu]
Halves are drawn within each cell (label x first word of the answer: the lie token for lies, the truth token for
resists), so both halves keep the cell mix. Reported per draw: cos(half A, half B) within each family, and cos(a half of
one family, a half of the other); the attenuation-corrected cross cosine is cross / sqrt(within ry * within rp).
The same again "balanced": only the Yes and No cells, direction = the mean over the two words of (resist mean - lie
mean), as persona_rep.py ansdir builds his answer-balanced direction, so neither family's answer-word mix enters."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path.home() / "honesty-heads" / "code"))
import engine as E  # noqa: E402
import steer as S  # noqa: E402


def heads(recs: list) -> torch.Tensor:
    """The span-averaged head outputs of every record, one row each (layers concatenated)."""
    return torch.stack([torch.cat([x.flatten() for x in r["mean"]["h"]]) for r in recs]).double()


def cos(x: torch.Tensor, y: torch.Tensor) -> float:
    return float(x @ y / (x.norm() * y.norm()))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("items")
    p.add_argument("out")
    p.add_argument("--families", default="ry,rp")
    p.add_argument("--splits", type=int, default=50)
    p.add_argument("--span", type=int, default=9)
    p.add_argument("--model", default=str(Path.home() / "models" / "qwen3.5-9b-hf"))
    p.add_argument("--device", default="xpu")
    p.add_argument("--dtype", default="bfloat16")
    a = p.parse_args()
    model, tok = E.load(a.model, a.dtype, a.device)
    eng = E.Engine(model)
    items = json.load(open(a.items, encoding="utf-8"))
    fams = a.families.split(",")
    X = {}  # family -> {(label, word): rows}
    for f in fams:
        X[f] = {}
        for lab in ("lie", "resist"):
            recs = S.nat_recs(eng, tok, items, f, ["select", "test"], lab, 10_000, a.span, True)
            for r, row in zip(recs, heads(recs)):
                w = (r["it"]["lie"] if lab == "lie" else r["it"]["truth"])[0].strip().lower()
                X[f].setdefault((lab, w if w in ("yes", "no") else "other"), []).append(row)
            del recs
    cells = {f: {f"{k[0]} {k[1]}": len(v) for k, v in sorted(X[f].items())} for f in fams}
    E.log(f"cells {cells}")
    BAL = False

    def direction(H: dict) -> torch.Tensor:
        if BAL:
            return sum(torch.stack(H["resist", w]).mean(0) - torch.stack(H["lie", w]).mean(0) for w in ("yes", "no")) / 2
        L = torch.stack([r for (lab, _), v in H.items() if lab == "lie" for r in v])
        R = torch.stack([r for (lab, _), v in H.items() if lab == "resist" for r in v])
        return R.mean(0) - L.mean(0)
    rng = np.random.default_rng(0)

    def halves(f):
        A, B = {}, {}
        for k, v in X[f].items():
            idx = rng.permutation(len(v))
            A[k] = [v[i] for i in idx[: len(v) // 2]]
            B[k] = [v[i] for i in idx[len(v) // 2:]]
        return direction(A), direction(B)
    out = {"cells": cells, "splits": a.splits, "span": a.span, "dtype": a.dtype}
    for BAL in (False, True):
        full = {f: direction(X[f]) for f in fams}
        draws = []
        for _ in range(a.splits):
            h = {f: halves(f) for f in fams}
            row = {f"within {f}": cos(*h[f]) for f in fams}
            if len(fams) == 2:
                f, g = fams
                row["cross"] = float(np.mean([cos(h[f][i], h[g][j]) for i in (0, 1) for j in (0, 1)]))
            draws.append(row)
        q = lambda k, pct: round(float(np.percentile([d[k] for d in draws], pct)), 3)
        rec = {"median_p5_p95": {k: [q(k, 50), q(k, 5), q(k, 95)] for k in draws[0]},
               "full_cos": cos(*[full[f] for f in fams]) if len(fams) == 2 else None}
        w = [rec["median_p5_p95"][f"within {f}"][0] for f in fams]
        if len(fams) == 2 and min(w) > 0:
            rec["cross_corrected"] = round(rec["median_p5_p95"]["cross"][0] / float(np.sqrt(w[0] * w[1])), 3)
        out["balanced" if BAL else "plain"] = rec
    json.dump(out, open(a.out, "w"), indent=1)
    E.log(f"split-half {json.dumps(out)}")


if __name__ == "__main__":
    main()
