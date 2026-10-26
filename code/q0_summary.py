"""Honesty heads step 3 Q0 (2026-10-26): one-screen summary of a persona_compare file.
Per arm: persona r with his +2 pattern (raw / beyond confidence) against the arm's own random directions, the dark and
deception sets, the four traits from his post, and lies removed on both test sets.
  python q0_summary.py COMPARE.json [COMPARE2.json ...]"""
import json
import sys

POST = ("moral-nihilism", "psychopathy", "believes-it-is-a-moral-patient", "acausal")


def rng(xs):
    return f"{min(xs):+.2f}..{max(xs):+.2f}"


for f in sys.argv[1:]:
    d = json.load(open(f, encoding="utf-8"))
    traits = d["traits"]
    idx = {k: next((i for i, t in enumerate(traits) if k in t), None) for k in POST}
    print(f"== {f}")
    for name, a in d["arms"].items():
        print(f"-- {name}  (alpha {a['alpha']}, random {a['random']})")
        for k in ("raw", "beyond"):
            r, rr = a[k]["r"], a[k].get("r_random") or []
            rank = sum(x >= r for x in rr) + 1 if rr else None
            extra = f"  random {rng(rr)}  rank from top {rank}/{len(rr) + 1}  below all: {all(x > r for x in rr)}" if rr else ""
            print(f"   r {k:6s} {r:+.3f}{extra}   same-sign of his FDR traits {a[k].get('same_sign', float('nan')):.2f}")
        for k in ("dark", "deception"):
            t, rr = a[k]["T"], a[k].get("random") or []
            print(f"   {k:9s} T {t:+.3f}" + (f"  random {rng(rr)}  above all: {all(x < t for x in rr)}  below all: {all(x > t for x in rr)}" if rr else ""))
        T = a["T"]
        print("   post traits: " + "; ".join(f"{k} {T[i]:+.2f}" for k, i in idx.items() if i is not None))
        for k, v in a.get("lies", {}).items():
            rr = v.get("random") or []
            print(f"   lies {k:10s} n {v['n']:3d} share {v['share']:.2f}" + (f"  random max {max(rr):.2f}" if rr else ""))
