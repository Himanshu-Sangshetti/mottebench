"""Paper figures (vector PDF). Data-only, dense, one style, one model order.
usage: python3 analysis/paper_figs.py   (after grading/aggregate.py, analysis/correction.py report) -> report/paper/fig_*.pdf
Every panel is computed here from results/*.jsonl and grading/*.jsonl (rep 0, original wording unless stated)."""
import json, glob, os, re, random, collections
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/report/paper"; os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"], "mathtext.fontset": "stix",
                     "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5, "xtick.labelsize": 7, "ytick.labelsize": 7,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": .5, "xtick.major.width": .5,
                     "ytick.major.width": .5, "xtick.major.size": 2.5, "ytick.major.size": 2.5, "legend.frameon": False, "pdf.fonttype": 42})
ORDER = ["sonnet", "anthropic/claude-haiku-5.5", "openai/gpt-6.1-sol", "deepseek/deepseek-v4-pro", "llama3.1:8b"]
NAME = {"sonnet": "Claude Sonnet 5.5", "anthropic/claude-haiku-5.5": "Claude Haiku 5.5", "openai/gpt-6.1-sol": "GPT-6.1-Sol",
        "deepseek/deepseek-v4-pro": "DeepSeek V4 Pro", "llama3.1:8b": "Llama 3.1 8B"}
SHORT = {"sonnet": "Sonnet", "anthropic/claude-haiku-5.5": "Haiku", "openai/gpt-6.1-sol": "GPT", "deepseek/deepseek-v4-pro": "DeepSeek", "llama3.1:8b": "Llama"}
MCOL = {"sonnet": "#c2410c", "anthropic/claude-haiku-5.5": "#f59e0b", "openai/gpt-6.1-sol": "#0f766e", "deepseek/deepseek-v4-pro": "#4338ca", "llama3.1:8b": "#7c3aed"}
DO_C, DEP_C, DONT_C, NONE_C = "#1d4ed8", "#d0d5dd", "#b42318", "#ffffff"
SRC = ["USPSTF", "Cochrane", "What Works Clearinghouse"]; SRCS = {"USPSTF": "USPSTF", "Cochrane": "Cochrane", "What Works Clearinghouse": "WWC"}
def dec(t):
    t = re.sub(r"^\W+", "", t or "").upper().replace("’", "'")
    return "DO" if t.startswith("DO IT") else "DONT" if t.startswith("DON'T") else "DEP" if t.startswith("IT DEPENDS") else "NONE"
num = lambda v: float(v) if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "", 1).isdigit()) else None
lab = {json.loads(l)["conv_id"]: json.loads(l) for l in open(f"{ROOT}/grading/final_labels.jsonl")}
R = collections.defaultdict(list)
for f in glob.glob(f"{ROOT}/results/main__*.jsonl"):
    if f.endswith((".fails.jsonl", ".manifest.jsonl")): continue
    for l in open(f):
        r = json.loads(l)
        if int(r.get("rep", 0)) != 0: continue
        r["dec"] = dec(r["replies"][-1]) if not r.get("free_decision") else None
        r.update({k: v for k, v in lab.get(r["conv_id"], {}).items() if k not in ("conv_id",)})
        R[r["model"]].append(r)
ms = [m for m in ORDER if m in R]
def boot_diff(a, b, B=2000):
    """cluster bootstrap CI of mean(a) - mean(b) where a, b: dict item -> list of 0/1"""
    random.seed(0); ks = sorted(set(a) | set(b)); out = []
    f = lambda K: (np.mean([v for k in K for v in a.get(k, [])]) - np.mean([v for k in K for v in b.get(k, [])])) * 100
    pt = f(ks)
    for _ in range(B): out.append(f(random.choices(ks, k=len(ks))))
    out.sort(); return pt, out[int(.025 * B)], out[int(.975 * B) - 1]
def auroc(pos, neg):
    if not pos or not neg: return None
    return sum((p > n) + .5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))

# ---------------- Figure 1: every weak item, every model; swap effect overall and per source ----------------
weak_ids = sorted({r["item_id"] for m in ms for r in R[m] if r["cond"] == "EK_WEAK"})
src_of = {r["item_id"]: r["source_name"] for m in ms for r in R[m]}
D = {m: {(r["item_id"], r["cond"]): r["dec"] for r in R[m]} for m in ms}
do_score = {i: np.mean([D[m].get((i, c)) == "DO" for m in ms for c in ("A", "EK_WEAK", "EK_STRONG")]) for i in weak_ids}
rows = [i for s in SRC for i in sorted([i for i in weak_ids if src_of[i] == s], key=lambda i: -do_score[i])]
CONDS = [("A", "own"), ("EK_WEAK", "weak"), ("EK_STRONG", "strong")]
M = np.zeros((len(rows), len(ms) * 3)); code = {"DO": 3, "DEP": 2, "DONT": 1, "NONE": 0, None: 0}
for j, m in enumerate(ms):
    for k, (c, _) in enumerate(CONDS):
        for i, it in enumerate(rows): M[i, j * 3 + k] = code[D[m].get((it, c))]
fig = plt.figure(figsize=(6.1, 3.7)); gs = fig.add_gridspec(1, 2, width_ratios=[1.25, 1], wspace=.62)
ax = fig.add_subplot(gs[0]); cm = ListedColormap([NONE_C, DONT_C, DEP_C, DO_C])
ax.imshow(M.T, aspect="auto", cmap=cm, vmin=0, vmax=3, interpolation="nearest")
for j in range(1, len(ms)): ax.axhline(j * 3 - .5, color="white", lw=2.2)
cum = 0
for s in SRC:
    n = sum(src_of[i] == s for i in rows); ax.axvline(cum - .5, color="black", lw=.5) if cum else None
    ax.text(cum + n / 2 - .5, -.75, f"{SRCS[s]} (n={n})", ha="center", va="bottom", fontsize=6.3); cum += n
ax.set_yticks(range(len(ms) * 3)); ax.set_yticklabels([f"{lbl}" for m in ms for _, lbl in CONDS], fontsize=5.8)
for j, m in enumerate(ms): ax.text(-7.5, j * 3 + 1, SHORT[m], ha="right", va="center", fontsize=7, weight="bold", color=MCOL[m])
ax.tick_params(axis="y", length=0, pad=1); ax.set_xticks([]); ax.set_xlabel(f"{len(rows)} weak-evidence items (sorted within source by overall DO-IT rate)")
for sp in ax.spines.values(): sp.set_visible(False)
ax.set_title("(a) Final decision for every weak item, by turn-2 content", loc="left", pad=14, x=-.17)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=DO_C, label="DO IT"), Patch(color=DEP_C, label="IT DEPENDS"), Patch(color=DONT_C, label="DON'T")],
          loc="upper center", bbox_to_anchor=(.5, -.07), ncol=3, fontsize=6.5, handlelength=1, columnspacing=1)
ax.text(-.17, -.17, "rows: own = model's own turn-2 answer; weak / strong = planted statement", transform=ax.transAxes, fontsize=5.8, color="#475467")
ax2 = fig.add_subplot(gs[1]); y = 0; yt = []
for m in ms[::-1]:
    get = lambda c, s=None: {i: [D[m].get((i, c)) == "DO"] for i in weak_ids if (s is None or src_of[i] == s) and (i, c) in D[m]}
    pt, lo, hi = boot_diff(get("EK_STRONG"), get("EK_WEAK"))
    ax2.errorbar(pt, y, xerr=[[pt - lo], [hi - pt]], fmt="o", ms=4.5, color=MCOL[m], capsize=2, elinewidth=1.1, zorder=3)
    ax2.text(103, y, f"{pt:+.0f} [{lo:+.0f}, {hi:+.0f}]", va="center", fontsize=6.3)
    for k, (s, mk) in enumerate(zip(SRC, ["^", "s", "D"])):
        p2, _, _ = boot_diff(get("EK_STRONG", s), get("EK_WEAK", s), B=1)
        ax2.scatter(p2, y - .32, marker=mk, s=9, facecolor="white", edgecolor=MCOL[m], lw=.7, zorder=2, label=SRCS[s] if m == ms[0] else None)
    yt.append(y); y += 1
ax2.axvspan(-30, 20, color="#b42318", alpha=.05, lw=0); ax2.axvline(20, color="#b42318", ls="--", lw=.7); ax2.axvline(40, color="#067647", ls="--", lw=.7)
ax2.text(19, len(ms) - .45, "ignores\n(<20)", ha="right", va="top", fontsize=6, color="#b42318"); ax2.text(41, len(ms) - .45, "follows\n(≥40)", va="top", fontsize=6, color="#067647")
ax2.set_yticks(yt); ax2.set_yticklabels([NAME[m] for m in ms[::-1]]); ax2.set_xlim(-30, 100); ax2.set_ylim(-.75, len(ms) - .1)
ax2.set_xlabel("swap effect: % DO IT (told strong) − (told weak), pts"); ax2.grid(axis="x", lw=.3, alpha=.4)
ax2.legend(loc="lower left", fontsize=6, title="per source", title_fontsize=6, handletextpad=.1, borderaxespad=0)
ax2.set_title("(b) Causal swap effect, 95% CI", loc="left", pad=14)
fig.savefig(f"{OUT}/fig1_items.pdf", bbox_inches="tight"); plt.close(fig)

# ---------------- Figure 2: what models say vs what they do (condition A) ----------------
jm = [m for m in ms if any(num(r.get("T2_evid")) is not None for r in R[m])]
fig, axs = plt.subplots(1, 2, figsize=(6.1, 2.0), gridspec_kw={"width_ratios": [1.5, 1]})
ev_cols = ["#7a271a", "#d92d20", "#fda29b", "#a6f4c5", "#039855"]; ax = axs[0]; yl = []
for i, m in enumerate(jm):
    for k, (cls, off) in enumerate([("WEAK", .2), ("STRONG", -.2)]):
        v = [round(num(r["T2_evid"])) for r in R[m] if r["cond"] == "A" and num(r.get("T2_evid")) is not None and (r["key_class"] == "WEAK") == (cls == "WEAK")]
        left = 0
        for s in range(1, 6):
            w = 100 * v.count(s) / len(v); ax.barh(len(jm) - 1 - i + off, w, left=left, height=.36, color=ev_cols[s - 1], lw=0, label=str(s) if i == 0 and k == 0 else None); left += w
        ax.text(101, len(jm) - 1 - i + off, "weak" if cls == "WEAK" else "strong", va="center", fontsize=5.8, color="#475467")
ax.set_yticks(range(len(jm))); ax.set_yticklabels([NAME[m] for m in jm[::-1]]); ax.set_xlim(0, 100); ax.tick_params(axis="y", length=0)
ax.set_xlabel("% of conversations"); ax.set_title("(a) Evidence strength the model states when asked, by official class", loc="left")
ax.legend(title="stated strength: 1 = very weak … 5 = strong", title_fontsize=6, fontsize=6, ncol=5, loc="upper center", bbox_to_anchor=(.5, -.3), handlelength=.9, columnspacing=.7, handletextpad=.3)
ax = axs[1]
for i, m in enumerate(jm):
    A = [r for r in R[m] if r["cond"] == "A" and num(r.get("T2_evid")) is not None]
    a = auroc([num(r["T2_evid"]) for r in A if r["key_class"] != "WEAK"], [num(r["T2_evid"]) for r in A if r["key_class"] == "WEAK"])
    random.seed(0); by = collections.defaultdict(list)
    for r in A: by[r["item_id"]].append(r)
    bs = []
    for _ in range(1000):
        S = [x for k in random.choices(list(by), k=len(by)) for x in by[k]]
        v = auroc([num(r["T2_evid"]) for r in S if r["key_class"] != "WEAK"], [num(r["T2_evid"]) for r in S if r["key_class"] == "WEAK"])
        if v is not None: bs.append(v)
    bs.sort(); ax.errorbar(a, len(jm) - 1 - i, xerr=[[a - bs[25]], [bs[974] - a]], fmt="o", ms=4, color=MCOL[m], capsize=2, elinewidth=1)
    ax.text(bs[974] + .012, len(jm) - 1 - i, f"{a:.2f}", va="center", fontsize=6)
ax.axvline(.5, color="#98a2b3", lw=.6, ls=":"); ax.set_xlim(.45, 1); ax.set_yticks(range(len(jm))); ax.set_yticklabels([])
ax.set_xlabel("AUROC (stated strength → official class)"); ax.set_title("(b) How well stated strength separates the classes", loc="left"); ax.grid(axis="x", lw=.3, alpha=.4)
fig.tight_layout(w_pad=.6); fig.savefig(f"{OUT}/fig2_stated.pdf", bbox_inches="tight"); plt.close(fig)

# ---------------- Figure 3: the decision follows turn 1, not turn 2 (mechanism) ----------------
fig, axs = plt.subplots(1, len(jm), figsize=(6.1, 2.05), sharey=True)
RECS = [("DO", "turn 1: do"), ("DEPENDS", "depends"), ("DONT", "don't")]
for ax, m in zip(axs, jm):
    H = np.full((3, 3), np.nan); N = np.zeros((3, 3), int)
    for a_, (rec, _) in enumerate(RECS):
        for b_, (c, _) in enumerate(CONDS):
            g = [r for r in R[m] if r["cond"] == c and r["key_class"] == "WEAK" and r.get("T1_rec") == rec]
            N[a_, b_] = len(g)
            if len(g) >= 3: H[a_, b_] = 100 * np.mean([r["dec"] == "DO" for r in g])
    ax.imshow(H, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    for a_ in range(3):
        for b_ in range(3):
            if not np.isnan(H[a_, b_]): ax.text(b_, a_, f"{H[a_, b_]:.0f}\n", ha="center", va="center", fontsize=6.5, color="white" if H[a_, b_] > 55 else "black")
            ax.text(b_, a_ + .22, f"n={N[a_, b_]}", ha="center", va="center", fontsize=4.8, color="white" if not np.isnan(H[a_, b_]) and H[a_, b_] > 55 else "#475467")
    ax.set_xticks(range(3)); ax.set_xticklabels(["own", "told\nweak", "told\nstrong"], fontsize=6); ax.set_title(NAME[m], fontsize=7, color=MCOL[m])
    ax.set_yticks(range(3)); ax.set_yticklabels([lbl for _, lbl in RECS], fontsize=6); ax.tick_params(length=0)
    for sp in ax.spines.values(): sp.set_visible(False)
axs[0].set_ylabel("turn-1 recommendation")

fig.tight_layout(w_pad=.4); fig.savefig(f"{OUT}/fig3_mechanism.pdf", bbox_inches="tight"); plt.close(fig)

# ---------------- Figure 4: how the final answer treats the planted statement ----------------
cor = json.load(open(f"{ROOT}/analysis/correction.json")) if os.path.exists(f"{ROOT}/analysis/correction.json") else {}
if cor:
    CATS = [("ACCEPTS", "accepts it", "#98a2b3"), ("SAYS_STRONGER", "says evidence is stronger", "#1d4ed8"), ("SAYS_WEAKER", "says evidence is weaker", "#b42318"),
            ("RETRACTS_SOURCE", "retracts the cited source", "#f79009"), ("NO_MENTION", "does not mention it", "#eaecf0")]
    cm_ = [m for m in ORDER if m in cor]
    fig, axs = plt.subplots(1, 2, figsize=(6.1, 1.85), sharey=True)
    for ax, c, t in [(axs[0], "EK_WEAK", "(a) Planted \"the evidence is weak\" (true for these items)"), (axs[1], "EK_STRONG", "(b) Planted \"the evidence is strong\" (false)")]:
        for i, m in enumerate(cm_):
            d = cor[m].get(c); left = 0; yy = len(cm_) - 1 - i
            if not d or not d["labelled"]: continue
            for k, lbl, col in CATS:
                w = 100 * d[k] / d["labelled"]; ax.barh(yy, w, left=left, color=col, height=.72, edgecolor="white", lw=.4, label=lbl if i == 0 else None)
                if w >= 8: ax.text(left + w / 2, yy, f"{w:.0f}", ha="center", va="center", fontsize=6, color="white" if k in ("SAYS_STRONGER", "SAYS_WEAKER") else "black")
                left += w
            ax.text(101, yy, f"n={d['labelled']}", va="center", fontsize=5.5, color="#475467")
        ax.set_title(t, loc="left"); ax.set_xlim(0, 100); ax.set_xlabel("% of conversations"); ax.tick_params(axis="y", length=0)
    axs[0].set_yticks(range(len(cm_))); axs[0].set_yticklabels([NAME[m] for m in cm_[::-1]])
    h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=5, fontsize=6.5, bbox_to_anchor=(.55, -.1), handlelength=1, columnspacing=1)
    fig.tight_layout(rect=(0, .08, 1, 1)); fig.savefig(f"{OUT}/fig4_correction.pdf", bbox_inches="tight"); plt.close(fig)

# ---------------- Figure 5 (appendix): full decision composition ----------------
fig, axs = plt.subplots(1, 3, figsize=(6.1, 2.3), sharey=True)
CC = [("B", "B"), ("A", "A"), ("C", "C")]
for ax, (k, t) in zip(axs, [("WEAK", "Weak evidence (n=64)"), ("STRONG_FOR", "Strong, helps (n=24)"), ("STRONG_AGAINST", "Strong, does not help (n=12)")]):
    y = 0; yt, yl = [], []
    for m in ms[::-1]:
        for c, cl in CC[::-1]:
            g = [r["dec"] for r in R[m] if r["cond"] == c and r["key_class"] == k]
            left = 0
            for d_, col in [("DO", DO_C), ("DEP", DEP_C), ("DONT", DONT_C)]:
                w = 100 * g.count(d_) / len(g) if g else 0; ax.barh(y, w, left=left, color=col, height=.8, lw=0); left += w
            yt.append(y); yl.append(f"{SHORT[m]} · {cl}"); y += 1
        y += .6
    ax.set_title(t, loc="left"); ax.set_xlim(0, 100); ax.set_xlabel("% of conversations"); ax.tick_params(axis="y", length=0)
axs[0].set_yticks(yt); axs[0].set_yticklabels(yl, fontsize=5.6)
fig.legend(handles=[Patch(color=DO_C, label="DO IT"), Patch(color=DEP_C, label="IT DEPENDS"), Patch(color=DONT_C, label="DON'T")], loc="lower center", ncol=3, fontsize=6.5, bbox_to_anchor=(.55, -.06))
fig.tight_layout(rect=(0, .05, 1, 1)); fig.savefig(f"{OUT}/fig5_decisions.pdf", bbox_inches="tight"); plt.close(fig)

# ---------------- Figure 6 (appendix): judge agreement (primary pair confusion matrices) ----------------
L = collections.defaultdict(dict)
for f in glob.glob(f"{ROOT}/grading/labels/*.jsonl"):
    if "correction" in f or "self_" in f: continue
    for l in open(f):
        x = json.loads(l); L[x["conv_id"]][x["judge"]] = x
import sys; sys.path.insert(0, f"{ROOT}/grading"); from judge import eligible
pairs = collections.defaultdict(list)
for m in ms:
    for r in R[m]:
        el = eligible(m)[:2]; g = L.get(r["conv_id"], {})
        if all(j in g for j in el): pairs[m].append((g[el[0]], g[el[1]]))
fig, axs = plt.subplots(1, 3, figsize=(6.1, 2.05))
allp = [p for m in pairs for p in pairs[m]]
for ax, k, cats, t in [(axs[0], "T2_evid", ["1", "2", "3", "4", "5"], "(a) Stated evidence (1–5)"), (axs[1], "T3_unc", ["CARRIES", "EXPLAINS_AWAY", "DROPS"], "(b) Doubt in final answer"),
                       (axs[2], "T1_rec", ["DO", "DEPENDS", "DONT"], "(c) Turn-1 recommendation")]:
    norm = (lambda v: str(round(num(v))) if num(v) is not None else None) if k == "T2_evid" else (lambda v: v)
    C = np.zeros((len(cats), len(cats)))
    for a, b in allp:
        x, y_ = norm(a.get(k)), norm(b.get(k))
        if x in cats and y_ in cats: C[cats.index(x), cats.index(y_)] += 1
    Cn = C / C.sum(); ax.imshow(Cn, cmap="Greys", vmin=0, vmax=Cn.max())
    for i in range(len(cats)):
        for j in range(len(cats)): ax.text(j, i, f"{int(C[i, j])}", ha="center", va="center", fontsize=5.8, color="white" if Cn[i, j] > Cn.max() * .55 else "black")
    sh = {"EXPLAINS_AWAY": "EXPL.", "CARRIES": "CARR.", "DROPS": "DROPS", "DEPENDS": "DEP."}
    ax.set_xticks(range(len(cats))); ax.set_xticklabels([sh.get(c, c) for c in cats], fontsize=5.8); ax.set_yticks(range(len(cats))); ax.set_yticklabels([sh.get(c, c) for c in cats], fontsize=5.8)
    ag = np.trace(C) / C.sum() if k != "T2_evid" else sum(C[i, j] for i in range(5) for j in range(5) if abs(i - j) <= 1) / C.sum()
    ax.set_title(f"{t}\nagreement {ag:.0%}" + (" (±1)" if k == "T2_evid" else ""), loc="left", fontsize=7); ax.set_xlabel("judge 2"); ax.set_ylabel("judge 1"); ax.tick_params(length=0)
fig.tight_layout(w_pad=1.2); fig.savefig(f"{OUT}/fig6_judges.pdf", bbox_inches="tight"); plt.close(fig)
print("figures in", OUT)
