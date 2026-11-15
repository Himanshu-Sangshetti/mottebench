"""Final labels from the judge panel. usage: python3 grading/aggregate.py results/<run>.jsonl [...]
Per conversation and label: if the two primary judges agree (1-5 scales: within 1 point) the label is their value
(1-5: rounded mean); otherwise the third eligible judge's label breaks the tie (majority / median of three).
T3_dec for forced-format conversations is taken by rule from the reply's first words, never from a judge.
Writes grading/final_labels.jsonl and prints agreement between the primary judges per label.
Lists conversations still needing a tiebreak in grading/needs_tiebreak.txt (run judge.py --extra on them)."""
import json, sys, os, re, glob, collections, statistics
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/grading")
from judge import PANEL, eligible, FIELDS
NUM = {"T1_cert", "T2_evid"}
L = collections.defaultdict(dict)
for f in glob.glob(f"{ROOT}/grading/labels/*.jsonl"):
    if os.path.basename(f).split(".")[0] not in PANEL: continue  # panel judges only (exploratory labels live elsewhere)
    for l in open(f):
        x = json.loads(l); L[x["conv_id"]][x["judge"]] = x
def rule_dec(reply):
    t = re.sub(r"^\W+", "", reply or "").upper().replace("’", "'")
    return "DO IT" if t.startswith("DO IT") else "DON'T" if t.startswith("DON'T") else "IT DEPENDS" if t.startswith("IT DEPENDS") else None
def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None
rows = [json.loads(l) for f in sys.argv[1:] for l in open(f) if l.strip()]
out, agree, tie = [], collections.defaultdict(lambda: [0, 0]), []
for r in rows:
    el = eligible(r["model"]); got = L.get(r["conv_id"], {}); prim = [got[j] for j in el[:2] if j in got]; third = got.get(el[2]) if len(el) > 2 else None
    if len(prim) < 2: continue
    fin = dict(conv_id=r["conv_id"])
    for k in FIELDS:
        a, b = prim[0].get(k), prim[1].get(k)
        if k in NUM:
            x, y = num(a), num(b)
            if x is None and y is None: fin[k] = None; continue  # label does not apply (e.g. no evidence turn): not a disagreement
            ok = x is not None and y is not None and abs(x - y) <= 1
            agree[k][0] += ok; agree[k][1] += 1
            if ok: fin[k] = round((x + y) / 2)
            elif third and num(third.get(k)) is not None: fin[k] = statistics.median([v for v in (x, y, num(third.get(k))) if v is not None])
            else: fin[k] = None; tie.append(r["conv_id"])
        else:
            if a is None and b is None: fin[k] = None; continue
            ok = a == b; agree[k][0] += ok; agree[k][1] += 1
            if ok: fin[k] = a
            elif third: fin[k] = collections.Counter([a, b, third.get(k)]).most_common(1)[0][0]
            else: fin[k] = None; tie.append(r["conv_id"])
    if not r.get("free_decision"): fin["T3_dec"] = rule_dec(r["replies"][-1])  # forced format: by rule
    fin["judges"] = [p["judge"] for p in prim] + ([el[2]] if third else [])
    out.append(fin)
with open(f"{ROOT}/grading/final_labels.jsonl", "w") as f:
    for x in out: f.write(json.dumps(x) + "\n")
open(f"{ROOT}/grading/needs_tiebreak.txt", "w").write("\n".join(sorted(set(tie))))
print(len(out), "conversations with final labels;", len(set(tie)), "need a tiebreak")
for k, (a, n) in agree.items(): print(f"  primary-judge agreement {k}: {a}/{n} = {a / max(n, 1):.0%}")
