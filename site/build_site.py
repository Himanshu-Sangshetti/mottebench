"""Build the static website data in docs/ (served by GitHub Pages). usage: python3 site/build_site.py
Exports the 300 questions, every core-set conversation with its final labels, and the paper figures."""
import json, glob, os, re, shutil, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = f"{ROOT}/docs"
items = [json.loads(l) for l in open(f"{ROOT}/data/items.jsonl")]
CORE = {i["item_id"] for i in items if i["split"] == "core"}
Q = [dict(id=i["item_id"], q=i["question"], src=i["source_name"], domain=i["domain"], key=i["key_class"], detail=i["key_detail"],
          url=i["url"], year=i.get("published"), core=i["split"] == "core") for i in items]
json.dump(Q, open(f"{D}/data/questions.json", "w"), separators=(",", ":"))
L = {json.loads(l)["conv_id"]: json.loads(l) for l in open(f"{ROOT}/grading/final_labels.jsonl")}
NAME = {"sonnet": "Claude Sonnet 5.5", "anthropic/claude-haiku-5.5": "Claude Haiku 5.5", "openai/gpt-6.1-sol": "GPT-6.1-Sol",
        "deepseek/deepseek-v4-pro": "DeepSeek V4 Pro", "llama3.1:8b": "Llama 3.1 8B"}
VER = {"A": "Evidence question", "B": "No follow-up", "C": "Are you sure?", "A_F": "Evidence question, free answer",
       "EK_WEAK": "Planted: evidence weak", "EK_STRONG": "Planted: evidence strong", "A_Q1": "Reworded: casual", "A_Q2": "Reworded: personal context"}
def dec(t):
    m = re.match(r"\W*(DO IT|DON'T|DON’T|IT DEPENDS)", t.strip().upper()); return (m.group(1).replace("’", "'") if m else None)
C, n = [], 0
for f in sorted(glob.glob(f"{ROOT}/results/main__*.jsonl")):
    if f.endswith((".fails.jsonl", ".manifest.jsonl")): continue
    for r in map(json.loads, open(f)):
        if r["item_id"] not in CORE: continue
        rep = int(r.get("rep", 0)); rs = list(r["replies"])
        planted = bool(r.get("swap_text"))
        if planted: rs[1] = r["swap_text"]
        lab = {k: v for k, v in L.get(r["conv_id"], {}).items() if k in ("T1_knows", "T1_rec", "T2_evid", "T3_unc")}
        C.append(dict(id=r["conv_id"], m=NAME.get(r["model"], r["model"]), item=r["item_id"], v=VER.get(r["cond"], r["cond"]) + (f", repeat {rep + 1}" if rep else ""),
                      key=r["key_class"], u=r["user_turns"], r=rs, planted=planted, d=dec(rs[-1]) if not r.get("free_decision") else None, lab=lab))
json.dump(C, open(f"{D}/data/conversations.json", "w"), separators=(",", ":"))
for fig, out in [("fig1_funnel", "funnel"), ("fig3_planted", "planted")]:
    subprocess.run(["pdftoppm", "-png", "-r", "220", "-singlefile", f"{ROOT}/report/paper/{fig}.pdf", f"{D}/img/{out}"], check=True)
shutil.copy(f"{ROOT}/report/MotteBench.pdf", f"{D}/MotteBench.pdf")
print(len(Q), "questions;", len(C), "conversations")
