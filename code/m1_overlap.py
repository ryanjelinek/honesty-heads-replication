"""Honesty heads step 2, M1 (2026-10-24): how many of our heads are among his 29, against chance.
  python m1_overlap.py OURS_heads_nat.json HIS_heads_nat.json [OTHER_heads.json ...] [--n-heads 896]
Chance: a random set of k heads out of N holds k x 29 / N of his on average; the p-value is the hypergeometric upper
tail P(overlap >= observed). Other head files (his attribution-patching, balanced and sycophancy reruns) are compared
with his 29 the same way, for scale."""
import json
import sys
from math import comb


def heads(path: str) -> list:
    return [(h["layer"], h["index"]) for h in json.load(open(path, encoding="utf-8"))["heads"]]


def tail(N: int, K: int, k: int, x: int) -> float:
    """P(X >= x), X ~ hypergeometric: k draws from N with K successes."""
    return sum(comb(K, i) * comb(N - K, k - i) for i in range(x, min(K, k) + 1)) / comb(N, k)


args = [a for a in sys.argv[1:] if not a.startswith("--")]
N = int(sys.argv[sys.argv.index("--n-heads") + 1]) if "--n-heads" in sys.argv else 896
args = [a for a in args if a != str(N)]
ours, his = heads(args[0]), heads(args[1])
H = set(his)
print(f"his set: {len(his)} heads")
for name, path in [("ours", args[0])] + [(p.replace("\\", "/").split("/")[-2], p) for p in args[2:]]:
    s = heads(path)
    x = len(set(s) & H)
    print(f"{name:12s} {len(s):4d} heads, {x:3d} among his {len(his)} (chance {len(s) * len(his) / N:.1f}; "
          f"P(>= {x}) = {tail(N, len(his), len(s), x):.2g}); shared: {sorted(set(s) & H)}")
layers = lambda s: {l: sum(1 for x, _ in s if x == l) for l in sorted({x for x, _ in s})}
print("layers ours:", layers(ours))
print("layers his: ", layers(his))
