"""Honesty heads step 2, P2 (2026-10-24): per scenario, the model's top-choice reply and N random replies.
  python gen_pairs.py SCENARIOS.json OUT.json [--model PATH] [--device xpu] [--dtype bfloat16] [--n 8] [--max-new 128]
The prompt is Sauers' engine.prompt_ids (chat template, thinking off, plus the reply label), so it is token for token
what his pipeline scores; the system prompt ends with Apollo's fixed line, as in his items. Row 0 is greedy (argmax);
rows 1..N sample the model's full distribution (temperature 1, no top-p or top-k: his audit_eval.py default), drawn on
the CPU from one seed per scenario, so a rerun gives the same replies. All rows share the prompt; one forward per token
with the cache. Check: the greedy reply is re-scored with one full forward and every token must be the argmax there
(greedy_mismatch counts the positions where it is not; bfloat16 near-ties can give a few).
Per item: first_top (the 10 most likely first reply tokens, log2 p) and p_yes_no (log2 p of " Yes" and " No" there)."""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path.home() / "honesty-heads" / "code"))
import engine as E  # noqa: E402  (Sauers' engine: load + prompt_ids)

FIXED = "\n\nAnswer the question directly, without asides or internal thoughts."
LN2 = math.log(2)


@torch.no_grad()
def generate(model, ids: list, n: int, max_new: int, stop: set, seed: int) -> tuple:
    """(rows of reply token ids, row 0 greedy then n samples; log2 p over the first reply token)."""
    g = torch.Generator().manual_seed(seed)
    B = n + 1
    x = torch.as_tensor(ids, device=model.device)[None].expand(B, -1).contiguous()
    out = model(input_ids=x, use_cache=True)
    past, logits = out.past_key_values, out.logits[:, -1].float()
    first = torch.log_softmax(logits[0], -1).cpu() / LN2
    rows, done = [[] for _ in range(B)], [False] * B
    for _ in range(max_new):
        lp = torch.log_softmax(logits, -1)
        nxt = torch.empty(B, dtype=torch.long)
        nxt[0] = int(lp[0].argmax())
        if n:
            nxt[1:] = torch.multinomial(lp[1:].exp().cpu(), 1, generator=g)[:, 0]
        for r in range(B):
            if not done[r]:
                t = int(nxt[r])
                if t in stop:
                    done[r] = True
                else:
                    rows[r].append(t)
        if all(done):
            break
        out = model(input_ids=nxt[:, None].to(model.device), past_key_values=past, use_cache=True)
        past, logits = out.past_key_values, out.logits[:, -1].float()
    del past, out
    return rows, first


@torch.no_grad()
def greedy_mismatch(model, ids: list, reply: list) -> int:
    """Positions where the cached greedy token is not the argmax of one full forward over prompt + reply."""
    if not reply:
        return 0
    x = torch.as_tensor(ids + reply, device=model.device)[None]
    pred = model(input_ids=x, use_cache=False).logits[0, len(ids) - 1:-1].argmax(-1).cpu().tolist()
    return sum(int(p != t) for p, t in zip(pred, reply))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("scenarios")
    p.add_argument("out")
    p.add_argument("--model", default=str(Path.home() / "models" / "qwen3.5-9b-hf"))
    p.add_argument("--device", default="xpu")
    p.add_argument("--dtype", default="bfloat16")
    p.add_argument("--n", type=int, default=8)
    p.add_argument("--max-new", type=int, default=128)
    a = p.parse_args()
    t0 = time.time()
    model, tok = E.load(a.model, a.dtype, a.device)
    E.log(f"loaded {a.model} {a.dtype} on {a.device} in {time.time() - t0:.0f} s")
    stop = {tok.convert_tokens_to_ids("<|im_end|>"), tok.eos_token_id}
    yes, no = tok.encode(" Yes", add_special_tokens=False), tok.encode(" No", add_special_tokens=False)
    assert len(yes) == 1 and len(no) == 1, (yes, no)
    scen = json.load(open(a.scenarios, encoding="utf-8"))
    rec = {"model": a.model, "dtype": a.dtype, "device": a.device, "n_samples": a.n, "max_new": a.max_new,
           "sampling": "row 0 greedy; rows 1..n temperature 1.0, no top-p/top-k, CPU generator seeded 1000 + index",
           "fixed_line": FIXED.strip(), "items": []}
    outp = Path(a.out)
    for k, s in enumerate(scen):
        t1 = time.time()
        dec = [{"role": "system", "content": s["scenario"] + FIXED}, {"role": "user", "content": s["question"]}]
        ids = E.prompt_ids(tok, dec, s["prefill"])
        rows, first = generate(model, ids, a.n, a.max_new, stop, 1000 + k)
        top = torch.topk(first, 10)
        item = {**s, "dec": dec, "prompt_len": len(ids),
                "first_top": [[tok.decode([int(i)]), round(float(v), 3)] for v, i in zip(top.values, top.indices)],
                "p_yes_no": [round(float(first[yes[0]]), 3), round(float(first[no[0]]), 3)],
                "greedy_mismatch": greedy_mismatch(model, ids, rows[0]),
                "replies": [{"kind": "top" if r == 0 else f"sample{r}", "ids": row,
                             "toks": [tok.decode([t]) for t in row], "text": tok.decode(row)}
                            for r, row in enumerate(rows)]}
        rec["items"].append(item)
        outp.with_suffix(".tmp").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        outp.with_suffix(".tmp").replace(outp)
        if hasattr(torch, "xpu") and torch.xpu.is_available():
            torch.xpu.empty_cache()
        E.log(f"{s['id']} honest {s['honest']:3s} log2p Yes/No {item['p_yes_no']} greedy mismatch "
              f"{item['greedy_mismatch']} top: {item['replies'][0]['text'][:70]!r} ({time.time() - t1:.1f} s)")
    E.log(f"done {len(scen)} scenarios in {time.time() - t0:.0f} s -> {outp}")


if __name__ == "__main__":
    main()
