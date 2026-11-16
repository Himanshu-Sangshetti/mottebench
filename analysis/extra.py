"""Descriptive judge-based measures for the paper (exploratory, not pre-registered).
usage: python3 analysis/extra.py -> analysis/extra.json, analysis/EXTRA.md, analysis/fig/stated.png
Per model, condition A (neutral evidence question), rep 0, original wording:
 - how the model rates the evidence in turn 2 (T2_evid, 1-5) on weak vs strong items (does the stated evidence track the official key?)
 - share calling the evidence weak (T2_evid <= 2) by official class
 - observational coupling: DO-IT rate when the model itself called the evidence weak vs not (on weak items)
 - how the final answer handles doubt (T3_unc) on weak items
Cluster bootstrap over items (2000 resamples, seed 0)."""
import json, glob, os, random, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/analysis"
CORE = {x["item_id"] for x in map(json.loads, open(f"{ROOT}/data/items.jsonl")) if x["split"] == "core"}  # the paper reports the core item set only
NAME = {"sonnet": "Claude Sonnet 5.5", "anthropic/claude-haiku-5.5": "Claude Haiku 5.5", "openai/gpt-6.1-sol": "GPT-6.1-Sol", "deepseek/deepseek-v4-pro": "DeepSeek V4 Pro"}
lab = {json.loads(l)["conv_id"]: json.loads(l) for l in open(f"{ROOT}/grading/final_labels.jsonl")}
num = lambda v: float(v) if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "", 1).isdigit()) else None
def boot(rs, f, B=2000):
    random.seed(0); by = collections.defaultdict(list)
    for r in rs: by[r["item_id"]].append(r)
    ks = list(by); pt = f(rs)
    if pt is None: return None
    v = sorted(x for x in (f([y for k in random.choices(ks, k=len(ks)) for y in by[k]]) for _ in range(B)) if x is not None)
    return dict(est=pt, lo=v[int(.025 * len(v))], hi=v[int(.975 * len(v)) - 1], n=len(rs))
def rate(p): return lambda rs: 100 * sum(map(p, rs)) / len(rs) if rs else None
def mean_ev(rs):
    v = [num(r["T2_evid"]) for r in rs if num(r.get("T2_evid")) is not None]; return sum(v) / len(v) if v else None
res = {}
for f in sorted(glob.glob(f"{ROOT}/results/main__*.jsonl")):
    if f.endswith((".fails.jsonl", ".manifest.jsonl")) or "local" in f: continue
    R = [dict(r, **{k: v for k, v in lab[r["conv_id"]].items() if k != "conv_id"}) for r in map(json.loads, open(f)) if r["conv_id"] in lab and r["item_id"] in CORE]
    if not R: continue
    m = R[0]["model"]; A = [r for r in R if r["cond"] == "A" and r.get("rep", 0) == 0 and num(r.get("T2_evid")) is not None]
    W = [r for r in A if r["key_class"] == "WEAK"]; S = [r for r in A if r["key_class"] != "WEAK"]
    weak_said = lambda r: num(r["T2_evid"]) <= 2; do = lambda r: r.get("T3_dec") == "DO IT"
    x = dict(name=NAME.get(m, m), n_A=len(A))
    x["T2_evid_mean_weak"] = boot(W, mean_ev); x["T2_evid_mean_strong"] = boot(S, mean_ev)
    x["says_weak_on_weak"] = boot(W, rate(weak_said)); x["says_weak_on_strong"] = boot(S, rate(weak_said))
    ws, wn = [r for r in W if weak_said(r)], [r for r in W if not weak_said(r)]
    x["do_when_model_said_weak"] = dict(pct=rate(do)(ws), n=len(ws)); x["do_when_model_said_not_weak"] = dict(pct=rate(do)(wn), n=len(wn))
    x["T3_unc_weak"] = dict(collections.Counter(str(r.get("T3_unc")) for r in W)); x["T3_dec_weak"] = dict(collections.Counter(str(r.get("T3_dec")) for r in W))
    res[m] = x
json.dump(res, open(f"{OUT}/extra.json", "w"), indent=1)
F = lambda b, u="": "–" if not b else f"{b['est']:.{1 if u == '' else 0}f}{u} [{b['lo']:.{1 if u == '' else 0}f}, {b['hi']:.{1 if u == '' else 0}f}]"
with open(f"{OUT}/EXTRA.md", "w") as o:
    o.write("# Stated evidence (turn 2) vs official key, condition A (exploratory)\n\n| Model | n | Mean stated evidence (1-5), weak items | strong items | Calls evidence weak (<=2): weak items | strong items | DO IT on weak items when model said weak | when it did not | Final answer on weak items: CARRIES / EXPLAINS_AWAY / DROPS |\n|---|---|---|---|---|---|---|---|---|\n")
    for m, x in res.items():
        u = x["T3_unc_weak"]; a, b = x["do_when_model_said_weak"], x["do_when_model_said_not_weak"]
        fp = lambda d: "–" if d["pct"] is None else f"{d['pct']:.0f}% (n={d['n']})"
        o.write(f"| {x['name']} | {x['n_A']} | {F(x['T2_evid_mean_weak'])} | {F(x['T2_evid_mean_strong'])} | {F(x['says_weak_on_weak'], '%')} | {F(x['says_weak_on_strong'], '%')} | {fp(a)} | {fp(b)} | {u.get('CARRIES', 0)} / {u.get('EXPLAINS_AWAY', 0)} / {u.get('DROPS', 0)} |\n")
try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
    ms = list(res)[::-1]; fig, ax = plt.subplots(figsize=(3.4, 0.9 + 0.3 * len(ms)))
    for i, m in enumerate(ms):
        for k, c, lab_ in [("T2_evid_mean_weak", "#c81e1e", "official: weak"), ("T2_evid_mean_strong", "#057a55", "official: strong")]:
            b = res[m][k]
            if b: ax.errorbar(b["est"], i, xerr=[[b["est"] - b["lo"]], [b["hi"] - b["est"]]], fmt="o", color=c, capsize=3, label=lab_ if i == 0 else None)
    ax.set_yticks(range(len(ms))); ax.set_yticklabels([res[m]["name"] for m in ms]); ax.set_xlim(1, 5); ax.grid(axis="x", alpha=.3)
    ax.set_xlabel("Stated evidence strength (judge-rated, 1–5)"); ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig/stated.png", dpi=300)
except Exception as e: print("figure skipped:", e)
print(open(f"{OUT}/EXTRA.md").read())
