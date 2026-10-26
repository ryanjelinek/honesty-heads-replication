# honesty heads step 2, P7 follow-up (2026-10-24): his direction from his Yes/No-opening items only (and,
# as a contrast, from his other-opening items only), then the persona test of each on his 29 heads (19 random
# directions for the Yes/No one, none for the contrast). Host-RAM guards; bfloat16 on card 0.
cd ~/honesty-heads
export DCORE_ROW_TOKENS=512
M="--model $HOME/models/qwen3.5-9b-hf --dtype bfloat16 --device xpu"
bash guardedpy.sh p7-words-dir step2/ansdir_words.py data/items_roleplay_insider.json out/step2/words --family rp \
  --device xpu > out/p7-words-dir.log 2>&1
if [ -s out/step2/words/delta_A_rp_yesno.pt ] && [ -s out/step2/words/delta_A_rp_other.pt ]; then
  bash guardedpy.sh p7-words code/persona_rep.py run --items step2/items_rp_ry.json --persona data/items_persona.json \
    --arms step2/arms_words.json --families ry,rp --controls data/controls.json --out out/step2/persona_words $M \
    > out/p7-words.log 2>&1
fi
echo P7-WORDS-ALL-DONE >> out/p7-words-dir.log
