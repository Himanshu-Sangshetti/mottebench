"""Pick the 60-conversation calibration set for human labelling (Amendment 2.1, item 4).
Stratified: across models, and across conditions A / C / EK_WEAK / B, weak and strong items. Seed 0.
Writes grading/calibration_set.txt (one conv_id per line). Run once; never changes after the human starts labelling."""
import json, glob, os, random, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/grading/calibration_set.txt"
if os.path.exists(OUT) and os.path.getsize(OUT): raise SystemExit("calibration set already fixed")
rows = []
for f in glob.glob(f"{ROOT}/results/main__*.jsonl"):
    if f.endswith((".fails.jsonl", ".manifest.jsonl")) or "__local__" in f: continue
    rows += [json.loads(l) for l in open(f) if l.strip()]
models = sorted({r["model"] for r in rows})
if len(models) < 4 or len(rows) < 1200: raise SystemExit(f"not enough data yet ({len(rows)} rows, {len(models)} models)")
random.seed(0); pick = []
plan = [("A", "WEAK", 6), ("A", "STRONG", 3), ("C", "WEAK", 2), ("EK_WEAK", "WEAK", 2), ("B", "WEAK", 2)]  # per model = 15
for m in models[:4]:
    for cond, k, n in plan:
        pool = [r for r in rows if r["model"] == m and r["cond"] == cond and ((r["key_class"] == "WEAK") == (k == "WEAK"))]
        pick += [r["conv_id"] for r in random.sample(pool, min(n, len(pool)))]
random.shuffle(pick)
open(OUT, "w").write("\n".join(pick[:60]) + "\n"); print("calibration set:", len(pick[:60]), "conversations from", models[:4])
