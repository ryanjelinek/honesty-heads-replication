cd ~/honesty-heads
export DCORE_ROW_TOKENS=512
bash guarded.sh p6-need-ours natneed --model $HOME/models/qwen3.5-9b-hf --device xpu --dtype bfloat16 --items step2/items_rp_ry.json --heads out/step2/natsel_ry/heads_nat.json --delta out/step2/natural/delta_A_ry.pt --families rp,ry --labels lie,resist --n-items 40 --out out/step2/need_ours > out/p6-need-ours.log 2>&1
bash guarded.sh p6-need-his natneed --model $HOME/models/qwen3.5-9b-hf --device xpu --dtype bfloat16 --items step2/items_rp_ry.json --heads results/heads_nat.json --delta results/delta_A_rp.pt --families ry,rp --labels lie,resist --n-items 40 --out out/step2/need_his > out/p6-need-his.log 2>&1
echo P6-NEED-ALL-DONE >> out/p6-need-his.log
