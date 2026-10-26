# honesty heads step 2, P7 follow-up (2026-10-24): his answer-balanced direction (persona_rep.py ansdir, on
# his own items) and its persona test on his 29 heads (19 random directions) and on the 50 heads his balanced head search
# picked (no random directions, a check). Both steps under guardedpy.sh's host-RAM guards; bfloat16 on card 0.
cd ~/honesty-heads
export DCORE_ROW_TOKENS=512
M="--model $HOME/models/qwen3.5-9b-hf --dtype bfloat16 --device xpu"
bash guardedpy.sh p7-ansdir code/persona_rep.py ansdir --items data/items_roleplay_insider.json --source rp \
  --out out/step2/ansdir $M > out/p7-ansdir.log 2>&1
if [ -s out/step2/ansdir/delta_A_rp_answer.pt ]; then
  bash guardedpy.sh p7-balanced code/persona_rep.py run --items step2/items_rp_ry.json --persona data/items_persona.json \
    --arms step2/arms_balanced.json --families ry,rp --controls data/controls.json --out out/step2/persona_balanced $M \
    > out/p7-balanced.log 2>&1
fi
echo P7-BALANCED-ALL-DONE >> out/p7-ansdir.log
