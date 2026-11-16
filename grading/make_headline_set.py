"""Pick the 100-conversation human-label set for the headline (made 16 Nov, after the main results).
All 73 scored weak-evidence conversations with the evidence question where the judges found that turn 1 recommends the action
(the set the headline funnel rests on), plus 27 drawn at random (seed 0) from the scored ones where turn 1 did not, to check that split.
Four frontier models, core items, pilot items and unknown topics excluded, exactly as in the paper. Order shuffled; the labeller
sees only the conversation text. Writes grading/headline_set.txt."""
import json, glob, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/grading/headline_set.txt"
if os.path.exists(OUT) and os.path.getsize(OUT): raise SystemExit("headline set already fixed")
CORE = {x["item_id"] for x in map(json.loads, open(f"{ROOT}/data/items.jsonl")) if x["split"] == "core"}
L = {json.loads(l)["conv_id"]: json.loads(l) for l in open(f"{ROOT}/grading/final_labels.jsonl")}
rows = []
for f in glob.glob(f"{ROOT}/results/main__*.jsonl"):
    if f.endswith((".fails.jsonl", ".manifest.jsonl")) or "__local__" in f: continue
    rows += [r for r in map(json.loads, open(f)) if r["cond"] == "A" and r["key_class"] == "WEAK" and r["item_id"] in CORE
             and int(r.get("rep", 0)) == 0 and not r.get("pilot_item") and r["conv_id"] in L and L[r["conv_id"]].get("T1_knows") != "no"]
do = sorted(r["conv_id"] for r in rows if L[r["conv_id"]]["T1_rec"] == "DO")
rest = sorted(r["conv_id"] for r in rows if L[r["conv_id"]]["T1_rec"] != "DO")
random.seed(0); pick = do + random.sample(rest, 100 - len(do)); random.shuffle(pick)
open(OUT, "w").write("\n".join(pick) + "\n"); print(len(rows), "scored;", len(do), "turn-1 do;", len(pick), "picked")
