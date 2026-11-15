"""Paper figures (vector PDF), one consistent style and model order.
usage: python3 analysis/paper_figs.py  (after judgefree.py, extra.py, correction.py report) -> report/paper/fig_*.pdf"""
import json, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/report/paper"; os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"], "font.size": 8, "axes.titlesize": 8.5,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": .6, "xtick.major.width": .6, "ytick.major.width": .6,
                     "legend.frameon": False, "pdf.fonttype": 42})
ORDER = ["sonnet", "anthropic/claude-haiku-5.5", "openai/gpt-6.1-sol", "deepseek/deepseek-v4-pro", "llama3.1:8b"]
NAME = {"sonnet": "Claude Sonnet 5.5", "anthropic/claude-haiku-5.5": "Claude Haiku 5.5", "openai/gpt-6.1-sol": "GPT-6.1-Sol",
        "deepseek/deepseek-v4-pro": "DeepSeek V4 Pro", "llama3.1:8b": "Llama 3.1 8B"}
RED, GREEN, BLUE, GREY = "#b42318", "#067647", "#1d4ed8", "#667085"
jf = json.load(open(f"{ROOT}/analysis/judgefree.json")); ex = json.load(open(f"{ROOT}/analysis/extra.json"))
cor = json.load(open(f"{ROOT}/analysis/correction.json")) if os.path.exists(f"{ROOT}/analysis/correction.json") else {}
def eb(ax, b, y, **k):
    ax.errorbar(b["est"], y, xerr=[[b["est"] - b["lo"]], [b["hi"] - b["est"]]], capsize=2, elinewidth=.9, ms=4, **k)

# Figure 2: (a) stated evidence vs official class, (b) decision after planted weak vs strong statement
ms = [m for m in ORDER if m in jf]; Y = {m: len(ms) - 1 - i for i, m in enumerate(ms)}
fig, (a, b) = plt.subplots(1, 2, figsize=(6.9, 2.5), sharey=True, gridspec_kw={"width_ratios": [1, 1.3]})
for m in ms:
    x = ex.get(m)
    if x and x.get("T2_evid_mean_weak"):
        eb(a, x["T2_evid_mean_weak"], Y[m] + .12, fmt="o", color=RED, label="official: weak" if m == ms[0] else None)
        eb(a, x["T2_evid_mean_strong"], Y[m] - .12, fmt="s", color=GREEN, label="official: strong" if m == ms[0] else None)
a.set_xlim(1, 5); a.set_xticks([1, 2, 3, 4, 5]); a.set_xlabel("stated evidence strength (1 = very weak, 5 = very strong)")
a.set_title("(a) What the model says about the evidence", loc="left"); a.legend(loc="upper center", fontsize=7, handletextpad=.2, ncol=2, bbox_to_anchor=(.5, -.28))
a.set_yticks([Y[m] for m in ms]); a.set_yticklabels([NAME[m] for m in ms]); a.grid(axis="x", alpha=.25, lw=.5)
for m in ms:
    w, s = jf[m]["swap_weak_do"]["est"], jf[m]["swap_strong_do"]["est"]; e = jf[m]["H5_swap_effect"]
    b.plot([w, s], [Y[m], Y[m]], color=GREY, lw=1.2, zorder=1)
    b.scatter([w], [Y[m]], color=RED, s=22, zorder=2, label="told \"evidence is weak\"" if m == ms[0] else None)
    b.scatter([s], [Y[m]], color=GREEN, marker="s", s=22, zorder=2, label="told \"evidence is strong\"" if m == ms[0] else None)
    b.text(66, Y[m], f"{e['est']:+.0f} [{e['lo']:+.0f}, {e['hi']:+.0f}]", va="center", fontsize=7, color="black" if e["est"] >= 40 else RED if e["est"] < 20 else GREY)
b.text(66, len(ms) - .45, "swap effect", fontsize=7, weight="bold"); b.set_xlim(-2, 100); b.set_xticks([0, 20, 40, 60])
b.spines["bottom"].set_bounds(0, 60); b.set_xlabel("% DO IT (weak-evidence items)")
b.set_title("(b) What it decides after a planted statement", loc="left"); b.legend(loc="upper center", fontsize=7, ncol=2, bbox_to_anchor=(.36, -.28), handletextpad=.1)
b.grid(axis="x", alpha=.25, lw=.5); b.set_ylim(-.6, len(ms) - .2)
fig.tight_layout(w_pad=1); fig.savefig(f"{OUT}/fig_main.pdf", bbox_inches="tight")

# Figure 3: how the final answer treats the planted statement
if cor:
    CATS = [("ACCEPTS", "accepts it", "#98a2b3"), ("SAYS_STRONGER", "says evidence is stronger", BLUE), ("SAYS_WEAKER", "says evidence is weaker", RED),
            ("RETRACTS_SOURCE", "retracts the cited source", "#dc6803"), ("NO_MENTION", "does not mention it", "#eaecf0")]
    cm = [m for m in ORDER if m in cor]; Yc = {m: len(cm) - 1 - i for i, m in enumerate(cm)}
    fig, axs = plt.subplots(1, 2, figsize=(6.9, 1.9), sharey=True)
    for ax, c, t in [(axs[0], "EK_WEAK", "(a) Planted: \"the evidence is weak\" (true for these items)"), (axs[1], "EK_STRONG", "(b) Planted: \"the evidence is strong\" (false)")]:
        for m in cm:
            d = cor[m].get(c); left = 0
            if not d or not d["labelled"]: continue
            for k, lab, col in CATS:
                w = 100 * d[k] / d["labelled"]; ax.barh(Yc[m], w, left=left, color=col, height=.7, edgecolor="white", lw=.4, label=lab if m == cm[0] else None)
                if w >= 9: ax.text(left + w / 2, Yc[m], f"{w:.0f}", ha="center", va="center", fontsize=6.5, color="white" if k in ("SAYS_STRONGER", "SAYS_WEAKER", "RETRACTS_SOURCE") else "black")
                left += w
        ax.set_title(t, loc="left"); ax.set_xlim(0, 100); ax.set_xlabel("% of conversations")
    axs[0].set_yticks([Yc[m] for m in cm]); axs[0].set_yticklabels([NAME[m] for m in cm])
    h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=5, fontsize=7, bbox_to_anchor=(.55, -.06), handletextpad=.3, columnspacing=1)
    fig.tight_layout(rect=(0, .1, 1, 1)); fig.savefig(f"{OUT}/fig_correction.pdf", bbox_inches="tight")

# Appendix figure: decisions by condition and evidence class
fig, axs = plt.subplots(1, 3, figsize=(6.9, 1.9), sharey=True)
for ax, k, t in [(axs[0], "WEAK", "Weak evidence"), (axs[1], "STRONG_FOR", "Strong evidence: helps"), (axs[2], "STRONG_AGAINST", "Strong evidence: does not help")]:
    for j, (c, lab, mk, col) in enumerate([("B", "no follow-up (B)", "o", GREY), ("A", "evidence asked (A)", "s", BLUE), ("C", "\"Are you sure?\" (C)", "^", RED)]):
        for m in ms:
            bb = jf[m].get(f"do_{c}_{k}")
            if bb: eb(ax, bb, Y[m] + (1 - j) * .22, fmt=mk, color=col, label=lab if m == ms[0] else None)
    ax.set_title(t, loc="left"); ax.set_xlim(-3, 100); ax.set_xlabel("% DO IT"); ax.grid(axis="x", alpha=.25, lw=.5)
axs[0].set_yticks([Y[m] for m in ms]); axs[0].set_yticklabels([NAME[m] for m in ms])
h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=3, fontsize=7, bbox_to_anchor=(.55, -.08))
fig.tight_layout(rect=(0, .1, 1, 1)); fig.savefig(f"{OUT}/fig_decisions.pdf", bbox_inches="tight")
print("figures in", OUT)
