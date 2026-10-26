# honesty heads step 2, P7 follow-up (2026-10-26): the opposite push (D-12). His 29 heads along his
# direction and our 20 heads along ours, each at x(-2), toward the lie side, with 19 random directions each; then
# persona_compare against his float32 run. Ryan's question: does pushing the other way bring out the dark traits?
# Host-RAM guards; bfloat16 on card 0.
cd ~/honesty-heads
export DCORE_ROW_TOKENS=512
M="--model $HOME/models/qwen3.5-9b-hf --dtype bfloat16 --device xpu"
bash guardedpy.sh p7-opposite code/persona_rep.py run --items step2/items_rp_ry.json --persona data/items_persona.json \
  --arms step2/arms_opposite.json --families ry,rp --controls data/controls.json --out out/step2/persona_opposite $M \
  > out/p7-opposite.log 2>&1
.venv/bin/python code/persona_compare.py results/persona.json out/step2/compare_opposite.json \
  out/step2/persona_opposite > out/p7-opposite-compare.log 2>&1
echo P7-OPPOSITE-ALL-DONE >> out/p7-opposite.log
