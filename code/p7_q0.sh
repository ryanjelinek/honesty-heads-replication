# honesty heads step 3, Q0 (2026-10-26; PLAN-step3.md, predictions in PREDICTIONS.md P-3). Three persona
# runs, chained: q0a the crossed opposite push (our heads + his direction, his heads + ours, x(-2), 19 random each);
# q0b design C (his truths only: other openings minus Yes/No, built by cdir_truths.py) at +2 on his 29 heads and our
# 20, 19 random each; q0b2 his other-opening-only direction on his 29 heads at +2, now with 19 random. Each run then
# persona_compare against his float32 run. Host-RAM guards; bfloat16 on card 0.
cd ~/honesty-heads
export DCORE_ROW_TOKENS=512
M="--model $HOME/models/qwen3.5-9b-hf --dtype bfloat16 --device xpu"
run() {  # run NAME ARMS
  bash guardedpy.sh p7-$1 code/persona_rep.py run --items step2/items_rp_ry.json --persona data/items_persona.json \
    --arms step2/$2 --families ry,rp --controls data/controls.json --out out/step2/persona_$1 $M > out/p7-$1.log 2>&1
  .venv/bin/python code/persona_compare.py results/persona.json out/step2/compare_$1.json out/step2/persona_$1 \
    > out/p7-$1-compare.log 2>&1
  echo "P7-$1-DONE $(date -u +%H:%M:%SZ)" >> out/p7-q0.progress
}
echo "P7-Q0-START $(date -u +%H:%M:%SZ)" > out/p7-q0.progress
run q0a arms_q0a.json
bash guardedpy.sh p7-q0c-dir step2/cdir_truths.py data/items_roleplay_insider.json out/step2/q0 --family rp \
  --device xpu > out/p7-q0c-dir.log 2>&1
echo "P7-q0c-dir-DONE $(date -u +%H:%M:%SZ)" >> out/p7-q0.progress
if [ -s out/step2/q0/delta_C_rp.pt ]; then run q0b arms_q0b.json; fi
run q0b2 arms_q0b2.json
echo "P7-Q0-ALL-DONE $(date -u +%H:%M:%SZ)" >> out/p7-q0.progress
