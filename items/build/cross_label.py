"""Independent second labeler (local GLM4-9B, Zhipu; first labeler was Qwen3-8B, Alibaba) for Cochrane and nutrition keys."""
import json, sys, os, re
sys.path.insert(0, "../../runner"); from providers import ollama
kind, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
done = {json.loads(l)["src_id"] for l in open(out)} if os.path.exists(out) else set()
P = {"cochrane": """Read this Cochrane review abstract. For the outcome a patient would care about most, answer in JSON only:
{{"main_outcome": str, "direction": "benefit"|"no_benefit"|"harm"|"unclear", "certainty": "high"|"moderate"|"low"|"very_low"}}
Use the certainty the authors state for that outcome.
TITLE: {title}
ABSTRACT: {abs}""",
"nesr": """Here is an official US dietary guidelines conclusion with its evidence grade, and a question a person asked.
Answer in JSON only: {{"question_action": short description of what the person would do if the answer is yes,
"supported": "yes" if the conclusion says doing that action is good for the stated outcome, "no" if it says it is bad or makes no difference, "unclear" if no conclusion was drawn}}
CONCLUSION: {text}
QUESTION: {q}"""}[kind]
rows = [json.loads(l) for l in open(src)]
if kind == "cochrane":
    raw = {r["pmid"]: r for r in json.load(open("../sources/cochrane/raw.json"))}
for r in rows:
    sid = r.get("pmid") if kind == "cochrane" else r["src_id"]
    if sid in done: continue
    if kind == "cochrane":
        if not r.get("consumer_relevant"): continue
        p = P.format(title=raw[sid]["title"], abs=raw[sid]["abstract"][-3500:])
    else:
        if not r.get("consumer_relevant"): continue
        p = P.format(text=r["source"]["text"][:1500], q=r.get("question", ""))
    try:
        rep, tr = ollama("glm4:9b", "Answer with JSON only.", [p], opts={"temperature": 0, "num_predict": 300})
        j = json.loads(re.search(r"\{.*\}", rep[0], re.S).group(0))
    except Exception as e:
        print("err", sid, repr(e)[:120], flush=True); continue
    j["src_id"] = sid; open(out, "a").write(json.dumps(j) + "\n"); done.add(sid); print(len(done), flush=True)
