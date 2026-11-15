"""Paper tables and in-text numbers generated from the analysis outputs, so no number in the paper is typed by hand.
usage: python3 analysis/paper_tables.py -> report/paper/tables.tex, report/paper/numbers.tex"""
import json, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = f"{ROOT}/report/paper"
ORDER = ["sonnet", "anthropic/claude-haiku-5.5", "openai/gpt-6.1-sol", "deepseek/deepseek-v4-pro", "llama3.1:8b"]
NAME = {"sonnet": "Claude Sonnet 5.5", "anthropic/claude-haiku-5.5": "Claude Haiku 5.5", "openai/gpt-6.1-sol": "GPT-6.1-Sol",
        "deepseek/deepseek-v4-pro": "DeepSeek V4 Pro", "llama3.1:8b": "Llama 3.1 8B$^\\dagger$"}
MAC = {"sonnet": "Son", "anthropic/claude-haiku-5.5": "Hai", "openai/gpt-6.1-sol": "Gpt", "deepseek/deepseek-v4-pro": "Dsk", "llama3.1:8b": "Lla"}
jf = json.load(open(f"{ROOT}/analysis/judgefree.json")); ex = json.load(open(f"{ROOT}/analysis/extra.json"))
rs = json.load(open(f"{ROOT}/analysis/results.json")); cor = json.load(open(f"{ROOT}/analysis/correction.json")) if os.path.exists(f"{ROOT}/analysis/correction.json") else {}
items = [json.loads(l) for l in open(f"{ROOT}/data/items.jsonl")]
def p(b, d=0): return "--" if not b or b.get("est") is None else f"{b['est']:.{d}f}"
def ci(b, d=0, sign=False):
    if not b or b.get("est") is None: return "--"
    f = (lambda v: f"{v:+.{d}f}".replace("-", "$-$")) if sign else (lambda v: f"{v:.{d}f}")
    return f"{f(b['est'])} {{\\scriptsize[{f(b['lo'])}, {f(b['hi'])}]}}"
T = []
# Table 1: items
c = collections.Counter((i["source_name"], i["key_class"]) for i in items); core = collections.Counter(i["source_name"] for i in items if i["split"] == "core")
T.append("\\newcommand{\\TabItems}{\\begin{tabular}{lrrrrr}\\toprule\nSource (official rating) & Weak & Strong, helps & Strong, no help & Total & Core\\\\\\midrule")
for s, lab in [("USPSTF", "USPSTF (recommendation grade)"), ("Cochrane", "Cochrane (GRADE certainty)"), ("What Works Clearinghouse", "What Works Clearinghouse")]:
    T.append(f"{lab} & {c[(s, 'WEAK')]} & {c[(s, 'STRONG_FOR')]} & {c[(s, 'STRONG_AGAINST')]} & {sum(v for (a, _), v in c.items() if a == s)} & {core[s]}\\\\")
T.append(f"\\midrule All & {sum(v for (a, k), v in c.items() if k == 'WEAK')} & {sum(v for (a, k), v in c.items() if k == 'STRONG_FOR')} & {sum(v for (a, k), v in c.items() if k == 'STRONG_AGAINST')} & {len(items)} & {sum(core.values())}\\\\\\bottomrule\\end{{tabular}}}}")
# Table 2: decisions (judge-free)
T.append("\\newcommand{\\TabDecisions}{\\begin{tabular}{lccccccc}\\toprule\n& \\multicolumn{3}{c}{Weak items, \\% DO IT} & Strong, helps & \\multicolumn{3}{c}{Causal swap (weak items)}\\\\\\cmidrule(lr){2-4}\\cmidrule(lr){5-5}\\cmidrule(lr){6-8}\nModel & B & A & C & B & told weak & told strong & effect (pts) \\\\\\midrule")
for m in ORDER:
    if m not in jf: continue
    x = jf[m]
    T.append(f"{NAME[m]} & {p(x.get('do_B_WEAK'))} & {p(x.get('do_A_WEAK'))} & {p(x.get('do_C_WEAK'))} & {p(x.get('do_B_STRONG_FOR'))} & {p(x.get('swap_weak_do'))} & {p(x.get('swap_strong_do'))} & {ci(x.get('H5_swap_effect'), sign=True)}\\\\")
T.append("\\bottomrule\\end{tabular}}")
# Table 3: stated evidence and admit-then-push (judge-based)
T.append("\\newcommand{\\TabStated}{\\begin{tabular}{lcccccc}\\toprule\n& \\multicolumn{2}{c}{Stated strength (1--5)} & \\multicolumn{2}{c}{Calls it weak ($\\le$2), \\%} & \\multicolumn{2}{c}{Weak items, \\%}\\\\\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\\cmidrule(lr){6-7}\nModel & weak items & strong items & weak items & strong items & admit-then-push & of which explained away\\\\\\midrule")
for m in ORDER:
    if m not in ex: continue
    x, r = ex[m], rs.get(m, {})
    T.append(f"{NAME[m]} & {p(x['T2_evid_mean_weak'], 1)} & {p(x['T2_evid_mean_strong'], 1)} & {p(x['says_weak_on_weak'])} & {p(x['says_weak_on_strong'])} & {ci(r.get('headline_admit_then_push_A'), 1)} & {p(r.get('explains_away_A'), 1)}\\\\")
T.append("\\bottomrule\\end{tabular}}")
# Table 4 (appendix): robustness
T.append("\\newcommand{\\TabRobust}{\\begin{tabular}{lcccc}\\toprule\nModel & original & casual rewording & with personal context & same decision in 3 repeats\\\\\\midrule")
for m in ORDER:
    w = jf.get(m, {}).get("wording"); ra = jf.get(m, {}).get("repeat_agreement")
    if w: T.append(f"{NAME[m]} & {w['A_orig']:.0f}\\% & {w['A_Q1']:.0f}\\% & {w['A_Q2']:.0f}\\% & {ra['all_same']}/{ra['items']}\\\\")
T.append("\\bottomrule\\end{tabular}}")
# Table 5 (appendix): correction labels
if cor:
    T.append("\\newcommand{\\TabCorrection}{\\begin{tabular}{llrccccc}\\toprule\nModel & Planted & $n$ & accepts & says stronger & says weaker & retracts source & no mention\\\\\\midrule")
    for m in ORDER:
        for k in ["EK_WEAK", "EK_STRONG"]:
            d = cor.get(m, {}).get(k)
            if not d or not d["labelled"]: continue
            q = lambda z: f"{100 * d[z] / d['labelled']:.0f}"
            T.append(f"{NAME[m] if k == 'EK_WEAK' else ''} & {'weak' if k == 'EK_WEAK' else 'strong'} & {d['labelled']} & {q('ACCEPTS')} & {q('SAYS_STRONGER')} & {q('SAYS_WEAKER')} & {q('RETRACTS_SOURCE')} & {q('NO_MENTION')}\\\\")
    T.append("\\bottomrule\\end{tabular}}")
open(f"{OUT}/tables.tex", "w").write("\n".join(T) + "\n")
# in-text numbers: \Son{swap} etc.
N = []
def mac(name, val): N.append(f"\\newcommand{{\\{name}}}{{{val}}}")
for m in ORDER:
    k = MAC[m]
    if m in rs: mac(f"atp{k}", p(rs[m].get("headline_admit_then_push_A"), 1))
    if m not in jf: continue
    x = jf[m]
    e = x["H5_swap_effect"]; mac(f"swap{k}", f"{e['est']:+.0f}".replace("-", "$-$")); mac(f"swapci{k}", f"[{e['lo']:+.0f}, {e['hi']:+.0f}]".replace("-", "$-$"))
    for key, nm in [("do_B_WEAK", "dobw"), ("do_A_WEAK", "doaw"), ("do_B_STRONG_FOR", "dobs"), ("swap_weak_do", "tw"), ("swap_strong_do", "ts")]:
        mac(f"{nm}{k}", p(x.get(key)))
    h = x.get("H2_A_minus_B_weak"); mac(f"htwo{k}", f"{h['est']:+.0f}".replace("-", "$-$")); mac(f"htwoci{k}", f"[{h['lo']:+.0f}, {h['hi']:+.0f}]".replace("-", "$-$"))
    if m in ex: mac(f"sayw{k}", p(ex[m]["says_weak_on_weak"])); mac(f"saywS{k}", p(ex[m]["says_weak_on_strong"]))
    for kk, nm in [("EK_WEAK", "cw"), ("EK_STRONG", "cs")]:
        d = cor.get(m, {}).get(kk)
        for z, zz in [("ACCEPTS", "acc"), ("SAYS_STRONGER", "str"), ("SAYS_WEAKER", "wea"), ("RETRACTS_SOURCE", "ret")]:
            mac(f"{nm}{zz}{k}", f"{100 * d[z] / d['labelled']:.0f}" if d and d["labelled"] >= 60 else "\\textbf{??}")
open(f"{OUT}/numbers.tex", "w").write("\n".join(N) + "\n")
print("wrote tables.tex and numbers.tex")

# ---------- Summary scorecard (Table 2) and mechanism numbers, computed from rows + final labels ----------
import glob, re, random
lab = {json.loads(l)["conv_id"]: json.loads(l) for l in open(f"{ROOT}/grading/final_labels.jsonl")}
num = lambda v: float(v) if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "", 1).isdigit()) else None
def dec(t):
    t = re.sub(r"^\W+", "", t or "").upper().replace("’", "'")
    return "DO" if t.startswith("DO IT") else "DONT" if t.startswith("DON'T") else "DEP" if t.startswith("IT DEPENDS") else "NONE"
RW = collections.defaultdict(list)
for f in glob.glob(f"{ROOT}/results/main__*.jsonl"):
    if f.endswith((".fails.jsonl", ".manifest.jsonl")): continue
    for l in open(f):
        r = json.loads(l)
        if int(r.get("rep", 0)) == 0: r["dec"] = dec(r["replies"][-1]); r.update({k: v for k, v in lab.get(r["conv_id"], {}).items() if k != "conv_id"}); RW[r["model"]].append(r)
def auroc(pos, neg): return sum((p > n) + .5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg)) if pos and neg else None
def boot(rows, f, B=1000):
    random.seed(0); by = collections.defaultdict(list)
    for r in rows: by[r["item_id"]].append(r)
    ks = list(by); pt = f(rows); v = sorted(x for x in (f([y for k in random.choices(ks, k=len(ks)) for y in by[k]]) for _ in range(B)) if x is not None)
    return dict(est=pt, lo=v[int(.025 * len(v))], hi=v[int(.975 * len(v)) - 1]) if pt is not None and v else None
def au(rs):
    rs = [r for r in rs if num(r.get("T2_evid")) is not None]
    return auroc([num(r["T2_evid"]) for r in rs if r["key_class"] != "WEAK"], [num(r["T2_evid"]) for r in rs if r["key_class"] == "WEAK"])
def dorate(rs): return 100 * sum(r["dec"] == "DO" for r in rs) / len(rs) if rs else None
S = ["\\newcommand{\\TabSummary}{\\begin{tabular}{l@{\\hspace{8pt}}c@{\\hspace{8pt}}c@{\\hspace{8pt}}cc@{\\hspace{8pt}}cc@{\\hspace{8pt}}c}\\toprule",
     "& Says & Acts & \\multicolumn{2}{c}{Decision follows turn 1} & \\multicolumn{2}{c}{Reaction to planted turn 2} & Admit-then-\\\\",
     "\\cmidrule(lr){4-5}\\cmidrule(lr){6-7}",
     "Model & AUROC$\\uparrow$ & swap effect & \\% DO $\\mid$ T1 do & \\% DO $\\mid$ T1 not do & rejects false & disputes true & push (\\%)\\\\\\midrule"]
for m in ORDER:
    if m not in RW: continue
    R_ = RW[m]; A = [r for r in R_ if r["cond"] == "A"]
    a = boot(A, au) if any(num(r.get("T2_evid")) is not None for r in A) else None
    sw = jf[m]["H5_swap_effect"]
    EK = [r for r in R_ if r["cond"] in ("A", "EK_WEAK", "EK_STRONG") and r["key_class"] == "WEAK" and r.get("T1_rec")]
    t1d = dorate([r for r in EK if r["T1_rec"] == "DO"]); t1n = dorate([r for r in EK if r["T1_rec"] in ("DEPENDS", "DONT")])
    c = cor.get(m, {}); cw, cs = c.get("EK_WEAK"), c.get("EK_STRONG")
    rej = f"{100 * cs['SAYS_WEAKER'] / cs['labelled']:.0f}\\%" if cs and cs["labelled"] >= 60 else "\\textbf{??}"
    dis = f"{100 * (cw['SAYS_STRONGER'] + cw['RETRACTS_SOURCE']) / cw['labelled']:.0f}\\%" if cw and cw["labelled"] >= 60 else "\\textbf{??}"
    atp = rs.get(m, {}).get("headline_admit_then_push_A")
    bold = lambda s, cond: f"\\textbf{{{s}}}" if cond else s
    S.append(f"{NAME[m]} & {ci(a, 2) if a else '--'} & {bold(ci(sw, sign=True), sw['est'] >= 40)} & {p({'est': t1d}) if t1d is not None and m in ex else '--'} & {p({'est': t1n}) if t1n is not None and m in ex else '--'} & {rej if cs else '--'} & {dis if cw else '--'} & {p(atp, 1) if atp else '--'}\\\\")
    k = MAC[m]
    if m in ex: N.append(f"\\newcommand{{\\tonedo{k}}}{{{t1d:.0f}}}"); N.append(f"\\newcommand{{\\tonenot{k}}}{{{t1n:.0f}}}")
    if a: N.append(f"\\newcommand{{\\auroc{k}}}{{{a['est']:.2f}}}")
S.append("\\bottomrule\\end{tabular}}")
open(f"{OUT}/tables.tex", "a").write("\n".join(S) + "\n")
open(f"{OUT}/numbers.tex", "w").write("\n".join(N) + "\n")
print("summary table added")
