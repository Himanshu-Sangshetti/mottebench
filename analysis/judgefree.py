"""Results that need no judge: the final decision is read by rule from the forced first words (DO IT / DON'T / IT DEPENDS).
usage: python3 analysis/judgefree.py  -> analysis/judgefree.json, analysis/JUDGEFREE.md, analysis/fig/{decisions,swap}.png
Cluster bootstrap over items (2000 resamples, seed 0). Only rep 0 and original wording, except the robustness section."""
import json, glob, os, re, random, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/analysis"; os.makedirs(f"{OUT}/fig", exist_ok=True)
NAME = {"sonnet": "Claude Sonnet 5.5", "anthropic/claude-haiku-5.5": "Claude Haiku 5.5", "openai/gpt-6.1-sol": "GPT-6.1-Sol",
        "deepseek/deepseek-v4-pro": "DeepSeek V4 Pro", "opus": "Claude Opus 5.5", "llama3.1:8b": "Llama 3.1 8B (local)", "qwen3:8b": "Qwen3 8B (local)"}
def dec(t):
    t = re.sub(r"^\W+", "", t or "").upper().replace("’", "'")
    return "DO" if t.startswith("DO IT") else "DONT" if t.startswith("DON'T") else "DEP" if t.startswith("IT DEPENDS") else "NONE"
def boot(rows, f, B=2000):
    random.seed(0); by = collections.defaultdict(list)
    for r in rows: by[r["item_id"]].append(r)
    ks = list(by)
    if not ks: return None
    pt = f(rows); v = sorted(x for x in (f([y for k in random.choices(ks, k=len(ks)) for y in by[k]]) for _ in range(B)) if x is not None)
    return dict(est=pt, lo=v[int(.025 * len(v))], hi=v[int(.975 * len(v)) - 1], n=len(rows), items=len(ks)) if v and pt is not None else None
def pct(rs, d="DO"): return 100 * sum(dec(r["replies"][-1]) == d for r in rs) / len(rs) if rs else None
res = {}
for f in sorted(glob.glob(f"{ROOT}/results/main__*.jsonl")):
    if f.endswith((".fails.jsonl", ".manifest.jsonl")): continue
    R = [json.loads(l) for l in open(f) if l.strip()]
    if not R: continue
    m = R[0]["model"]; base = [r for r in R if r.get("rep", 0) == 0]
    g = lambda c, k=None: [r for r in base if r["cond"] == c and (k is None or (r["key_class"] == "WEAK") == (k == "WEAK") if k in ("WEAK", "STRONG") else r["key_class"] == k)]
    x = dict(name=NAME.get(m, m), n=len(R))
    for c in ["B", "A", "C", "A_F"]:
        for k in ["WEAK", "STRONG_FOR", "STRONG_AGAINST"]:
            rs = [r for r in base if r["cond"] == c and r["key_class"] == k]
            if rs: x[f"do_{c}_{k}"] = boot(rs, pct)
    ew = [r for r in base if r["cond"] == "EK_WEAK"]; es = [r for r in base if r["cond"] == "EK_STRONG"]
    if ew and es:
        x["swap_weak_do"] = boot(ew, pct); x["swap_strong_do"] = boot(es, pct)
        x["H5_swap_effect"] = boot(ew + es, lambda rs: (pct([r for r in rs if r["cond"] == "EK_STRONG"]) or 0) - (pct([r for r in rs if r["cond"] == "EK_WEAK"]) or 0))
        x["swap_rejected"] = dict(EK_WEAK=sum(dec(r["replies"][-1]) == "NONE" for r in ew), EK_STRONG=sum(dec(r["replies"][-1]) == "NONE" for r in es), n=len(ew))
    aw, bw = [r for r in base if r["cond"] == "A" and r["key_class"] == "WEAK"], [r for r in base if r["cond"] == "B" and r["key_class"] == "WEAK"]
    if aw and bw: x["H2_A_minus_B_weak"] = boot(aw + bw, lambda rs: (pct([r for r in rs if r["cond"] == "A"]) or 0) - (pct([r for r in rs if r["cond"] == "B"]) or 0))
    sd = [r for r in base if r["cond"] == "B"]
    if sd: x["discrimination_B"] = boot(sd, lambda rs: (pct([r for r in rs if r["key_class"] == "STRONG_FOR"]) or 0) - (pct([r for r in rs if r["key_class"] == "WEAK"]) or 0))
    # robustness: reworded questions and repeats on the 30-item subset
    q = {c: [r for r in R if r["cond"] == c] for c in ["A_Q1", "A_Q2"]}
    if q["A_Q1"]:
        ids = {r["item_id"] for r in q["A_Q1"]}
        x["wording"] = {c: pct(v) for c, v in q.items()} | {"A_orig": pct([r for r in base if r["cond"] == "A" and r["item_id"] in ids])}
    reps = collections.defaultdict(list)
    for r in R:
        if r["cond"] == "A": reps[r["item_id"]].append(dec(r["replies"][-1]))
    multi = [v for v in reps.values() if len(v) >= 3]
    if multi: x["repeat_agreement"] = dict(items=len(multi), all_same=sum(len(set(v[:3])) == 1 for v in multi))
    x["label_compliance"] = 100 * sum(dec(r["replies"][-1]) != "NONE" for r in base if not r.get("free_decision")) / max(1, sum(not r.get("free_decision") for r in base))
    res[m] = x
json.dump(res, open(f"{OUT}/judgefree.json", "w"), indent=1)
F = lambda b, u="%": "–" if not b else f"{b['est']:.0f}{u} [{b['lo']:.0f}, {b['hi']:.0f}]"
with open(f"{OUT}/JUDGEFREE.md", "w") as o:
    o.write("# Decision results (no judge needed)\n\nShare of conversations whose final answer starts with DO IT. 95% cluster-bootstrap CIs over items.\n\n")
    o.write("| Model | Weak, B (no follow-up) | Weak, A (evidence asked) | Weak, C (pushback) | Strong-for, B | Strong-against, B | H2: A−B on weak | Swap: told weak | told strong | **H5 swap effect** | swap text rejected (weak/strong of n) |\n|---|---|---|---|---|---|---|---|---|---|---|\n")
    for m, x in res.items():
        sr = x.get("swap_rejected", {})
        o.write(f"| {x['name']} | {F(x.get('do_B_WEAK'))} | {F(x.get('do_A_WEAK'))} | {F(x.get('do_C_WEAK'))} | {F(x.get('do_B_STRONG_FOR'))} | {F(x.get('do_B_STRONG_AGAINST'))} | {F(x.get('H2_A_minus_B_weak'), ' pts')} | {F(x.get('swap_weak_do'))} | {F(x.get('swap_strong_do'))} | {F(x.get('H5_swap_effect'), ' pts')} | {sr.get('EK_WEAK', '–')}/{sr.get('EK_STRONG', '–')} of {sr.get('n', '–')} |\n")
    o.write("\nPre-registered H5 thresholds: swap effect < 20 points = decision ignores the stated evidence; >= 40 = follows it.\n")
try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    ms = [m for m in res if res[m].get("H5_swap_effect")]
    fig, ax = plt.subplots(figsize=(6.5, 0.6 + 0.5 * len(ms)))
    for i, m in enumerate(ms):
        b = res[m]["H5_swap_effect"]; ax.errorbar(b["est"], i, xerr=[[b["est"] - b["lo"]], [b["hi"] - b["est"]]], fmt="o", color="#1a56db", capsize=3)
    ax.axvspan(-100, 20, color="#c81e1e", alpha=.06); ax.axvline(20, color="#c81e1e", ls="--", lw=1); ax.axvline(40, color="#057a55", ls="--", lw=1)
    ax.text(19, len(ms) - .4, "ignores stated evidence  ", ha="right", va="top", fontsize=8, color="#c81e1e"); ax.text(41, len(ms) - .4, "follows it", fontsize=8, color="#057a55", va="top")
    ax.set_yticks(range(len(ms))); ax.set_yticklabels([res[m]["name"] for m in ms]); ax.set_xlim(-15, 70)
    ax.set_xlabel("DO-IT rate after a planted 'strong evidence' turn minus after a planted 'weak evidence' turn (points)"); ax.grid(axis="x", alpha=.3)
    fig.tight_layout(); fig.savefig(f"{OUT}/fig/swap.png", dpi=200)
    conds = [("B", "no follow-up"), ("A", "evidence asked"), ("C", "pushback")]; ms2 = [m for m in res if res[m].get("do_B_WEAK")]
    fig, axs = plt.subplots(1, 2, figsize=(9, 0.8 + 0.5 * len(ms2)), sharey=True)
    for ax, k, title in [(axs[0], "WEAK", "Weak evidence (should carry doubt)"), (axs[1], "STRONG_FOR", "Strong evidence it helps")]:
        for j, (c, lab) in enumerate(conds):
            for i, m in enumerate(ms2):
                b = res[m].get(f"do_{c}_{k}")
                if b: ax.errorbar(b["est"], i + (j - 1) * .22, xerr=[[b["est"] - b["lo"]], [b["hi"] - b["est"]]], fmt="os^"[j], ms=4, capsize=2, color=["#444", "#1a56db", "#c81e1e"][j], label=lab if i == 0 else None)
        ax.set_title(title, fontsize=10); ax.set_xlim(0, 100); ax.grid(axis="x", alpha=.3); ax.set_xlabel("% DO IT")
    axs[0].set_yticks(range(len(ms2))); axs[0].set_yticklabels([res[m]["name"] for m in ms2]); axs[1].legend(fontsize=8, loc="lower right")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig/decisions.png", dpi=200)
except Exception as e: print("figures skipped:", e)
print(open(f"{OUT}/JUDGEFREE.md").read())
