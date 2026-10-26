"""Honesty heads step 2, P5 (2026-10-24): our labeled pairs -> items in Sauers' format (family "ry"), merged
with his items file so one file holds rp and ry.
  python build_items.py --tok TOKDIR --his items_roleplay_insider.json --out-ry data/items-ry.json --out-merged MERGED.json
      [--per-cell 11] BATCH ... (default batches: pilot batch2 batch3, read as data/pairs-B.json + data/labels-B.json)
TOKDIR holds the model's tokenizer.json, tokenizer_config.json and chat_template.jinja; the prompt is rebuilt the way
engine.prompt_ids builds it (checked against every stored prompt_len and against his rp items' tails before writing).
A kept pair (labels: opp not "none") becomes one item: lie = resist's opposite token, both at reply token 0 (dpos 0),
pair_sample = the opposite sample's index 0-7 (our sample1-8), m_dec = log2 p(lie token) - log2 p(truth token) from the
box run, usable as in his file (m_dec's sign agrees with the label; a bfloat16 tie, m_dec 0, is not usable).
Split: per cell (label x the greedy reply's first word, Yes or No), the first --per-cell usable items in his seeded order
(corefind.seeded: numpy default_rng(crc32(key)) permutation) are "select", the rest "test"."""
from __future__ import annotations

import argparse
import json
import zlib
from pathlib import Path

import jinja2
import jinja2.ext
import numpy as np
from jinja2.sandbox import ImmutableSandboxedEnvironment
from tokenizers import Tokenizer

HERE = Path(__file__).resolve().parent.parent
SOURCE = "step2: scenarios written by Claude (Opus 5.5) at Ryan Jelinek's request, 2026-10-24"
LABEL_SOURCE = ("greedy and sample read by hand by Claude (Opus 5.5); no LLM judge; unclear ones "
                "ruled by Ryan")


class Prompt:
    """engine.prompt_ids and engine.template_tail without transformers: the chat template rendered as transformers
    renders it (sandboxed jinja, trim and lstrip blocks), tokenized whole."""

    def __init__(self, d: Path):
        self.tok = Tokenizer.from_file(str(d / "tokenizer.json"))
        env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, extensions=[jinja2.ext.loopcontrols])
        env.filters["tojson"] = lambda x, indent=None, ensure_ascii=False, **k: json.dumps(x, indent=indent,
                                                                                          ensure_ascii=ensure_ascii)
        env.globals["raise_exception"] = lambda m: (_ for _ in ()).throw(jinja2.exceptions.TemplateError(m))
        self.tpl = env.from_string((d / "chat_template.jinja").read_text(encoding="utf-8"))
        self.cfg = json.loads((d / "tokenizer_config.json").read_text(encoding="utf-8"))
        self.end = self.tok.token_to_id("<|im_end|>")

    def ids(self, msgs: list, prefill: str = "") -> list[int]:
        s = self.tpl.render(messages=msgs, add_generation_prompt=True, enable_thinking=False,
                            bos_token=self.cfg.get("bos_token"), eos_token=self.cfg.get("eos_token")) + prefill
        return self.tok.encode(s, add_special_tokens=False).ids

    def tail(self, ids: list) -> int:
        return len(ids) - max(i for i, t in enumerate(ids) if t == self.end)


def seeded(xs: list, key: str) -> list:
    rng = np.random.default_rng(zlib.crc32(key.encode()))
    return [xs[i] for i in rng.permutation(len(xs))]


def item(x: dict, lab: dict, batch: str, pr: Prompt) -> dict:
    R = {r["kind"]: r for r in x["replies"]}
    g, o = R["top"], R[lab["opp"]]
    assert g["ids"][0] != o["ids"][0] and {g["toks"][0], o["toks"][0]} == {" Yes", " No"}, x["id"]
    lie_r, tru_r = (g, o) if lab["top"] == "lie" else (o, g)
    lp = dict(zip((" Yes", " No"), x["p_yes_no"]))
    m = round(lp[lie_r["toks"][0]] - lp[tru_r["toks"][0]], 4)
    ids = pr.ids(x["dec"], x["prefill"])
    assert len(ids) == x["prompt_len"], (x["id"], len(ids), x["prompt_len"])
    label = "lie" if lab["top"] == "lie" else "resist"
    return {
        "id": f"ry-{x['id']}", "source": SOURCE, "split": None, "dec": x["dec"], "prefill": x["prefill"],
        "lie_completion": None, "truth_completion": None, "turn": None, "max_new": 128, "polarity": None,
        "dec_reply": g["text"], "family": "ry", "grade": "pair", "hon": None, "hon_reply": None, "knows": None,
        "lies": label == "lie", "label": label, "label_source": LABEL_SOURCE, "pressure_free": "none",
        "dpos": 0, "parted": True, "prefix_ids": [], "prefix": "",
        "lie_ids": [lie_r["ids"][0]], "truth_ids": [tru_r["ids"][0]], "lie": [lie_r["toks"][0]],
        "truth": [tru_r["toks"][0]], "pair_sample": int(lab["opp"][len("sample"):]) - 1, "pair_reply": o["text"],
        "first": "lie" if label == "lie" else "truth", "tail": pr.tail(ids), "m_dec": m,
        "top_dec": x["first_top"][:5], "m_hon": None, "decides": m > 0, "greedy": x["first_top"][0][0] == lie_r["toks"][0],
        "knowledge_margin": None, "usable": m != 0 and (m > 0) == (label == "lie"), "dpos_kind": "first reply token",
        "n_dec": None, "n_hon": None, "top_hon": None,
        # ours, beyond his fields
        "scenario_id": x["id"], "honest": x["honest"], "author": x["author"], "batch": batch,
        "answer": g["toks"][0].strip(), "pair_kind": lab["opp"], "label_note": lab.get("note"),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("batches", nargs="*", default=["pilot", "batch2", "batch3"])
    p.add_argument("--tok", required=True)
    p.add_argument("--his", required=True)
    p.add_argument("--out-ry", default=str(HERE / "data" / "items-ry.json"))
    p.add_argument("--out-merged", required=True)
    p.add_argument("--per-cell", type=int, default=11)
    a = p.parse_args()
    pr = Prompt(Path(a.tok))
    his = json.load(open(a.his, encoding="utf-8"))
    for it in his:  # the rebuilt prompt must agree with his stored tails before any of ours is trusted
        if it["family"] == "rp":
            assert pr.tail(pr.ids(it["dec"], it["prefill"]) + list(it["prefix_ids"])) == it["tail"], it["id"]
    items = []
    for b in a.batches:
        P = json.load(open(HERE / "data" / f"pairs-{b}.json", encoding="utf-8"))
        L = json.load(open(HERE / "data" / f"labels-{b}.json", encoding="utf-8"))["labels"]
        for x in P["items"]:
            lab = L[x["id"]]
            if lab["top"] != "unclear" and lab.get("opp", "none") != "none":
                items.append(item(x, lab, b, pr))
    cells = {}
    for it in items:
        if it["usable"]:
            cells.setdefault((it["label"], it["answer"]), []).append(it)
    for (label, word), xs in sorted(cells.items()):
        for k, it in enumerate(seeded(sorted(xs, key=lambda i: int(i["scenario_id"][1:])), f"ry/select/{label}/{word}")):
            it["split"] = "select" if k < a.per_cell else "test"
        print(f"{label:6s} says {word:3s}: usable {len(xs):2d}, select {min(len(xs), a.per_cell):2d}, "
              f"test {max(0, len(xs) - a.per_cell):2d}")
    for it in items:
        if not it["usable"]:
            it["split"] = "test"
            print(f"not usable (m_dec {it['m_dec']}): {it['id']} {it['label']} says {it['answer']}")
    assert not {i["id"] for i in items} & {i["id"] for i in his}
    Path(a.out_ry).write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    Path(a.out_merged).write_text(json.dumps(his + items, ensure_ascii=False), encoding="utf-8")
    print(f"{len(items)} ry items -> {a.out_ry}; {len(his)} + {len(items)} -> {a.out_merged}")


if __name__ == "__main__":
    main()
