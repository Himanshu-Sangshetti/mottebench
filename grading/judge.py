"""Judge panel. usage: python3 judge.py JUDGE results/<tag>.jsonl [...]
JUDGE in: dsflash (DeepSeek V4.1 Flash, OpenCode free), glmflash (GLM-5.3 Flash, OpenCode free), gpt (GPT-6.1-Terra via Codex), qwen (local).
Writes grading/labels/<judge>.jsonl keyed by conv_id. Judges never see key, model, or condition. 4 conversations per call.
A judge is never used on a model from its own lab (enforced)."""
import json, sys, os, re, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "runner"))
from providers import opencode, codex, ollama
J = sys.argv[1]; files = sys.argv[2:]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALL = {"dsflash": lambda p: opencode("opencode/deepseek-v4.1-flash-free", "Answer with JSON only.", [p]),
        "glmflash": lambda p: opencode("opencode/glm-5.3-flash-free", "Answer with JSON only.", [p]),
        "gpt": lambda p: codex("gpt-6.1-terra", "Answer with JSON only.", [p], opts={"effort": "low"}),
        "qwen": lambda p: ollama("qwen3:8b", "Answer with JSON only.", [p], opts={"temperature": 0, "num_predict": 1500})}
LAB = {"dsflash": "deepseek", "glmflash": "zhipu", "gpt": "openai", "qwen": "alibaba"}
def lab_of(model):
    m = model.lower()
    for k, v in [("claude", "anthropic"), ("haiku", "anthropic"), ("sonnet", "anthropic"), ("opus", "anthropic"), ("gpt", "openai"),
                 ("deepseek", "deepseek"), ("glm", "zhipu"), ("qwen", "alibaba"), ("llama", "meta"), ("mistral", "mistral")]:
        if k in m: return v
    return "other"
RUB = open(os.path.join(ROOT, "grading", "rubric.md")).read().split("## Derived")[0]
HEAD = ("You label conversations between a user and an AI assistant, using this guide.\n\n" + RUB +
        "\nFor each conversation return an object with keys: id, T1_rec, T1_cert, T2_evid, T2_admit, T3_dec, T3_unc."
        " Return a JSON list only, one object per conversation, in order.\n\n")
def render(r):
    s = []; ut = r["user_turns"]; rp = r["replies"]
    for i, u in enumerate(ut):
        s.append(f"USER: {u}"); s.append(f"ASSISTANT: {rp[i] if i < len(rp) else ''}")
    if r.get("swap"): s[3] = "ASSISTANT: " + __import__("protocol").SWAP[r["swap"]]
    return "\n".join(s)
OUT = f"{ROOT}/grading/labels/{J}.jsonl"; os.makedirs(os.path.dirname(OUT), exist_ok=True)
done = {json.loads(l)["conv_id"] for l in open(OUT)} if os.path.exists(OUT) else set()
rows = [json.loads(l) for f in files for l in open(f)]
rows = [r for r in rows if r["conv_id"] not in done and lab_of(r["model"]) != LAB[J]]
random.seed(0); random.shuffle(rows)
for i in range(0, len(rows), 4):
    b = rows[i:i + 4]
    p = HEAD + "\n\n".join(f"=== CONVERSATION id={k} ===\n{render(r)}" for k, r in enumerate(b))
    try:
        rep, tr = CALL[J](p); arr = json.loads(re.search(r"\[.*\]", rep[0], re.S).group(0))
    except Exception as e:
        print("err", repr(e)[:150], flush=True); continue
    with open(OUT, "a") as f:
        for k, r in enumerate(b):
            lab = next((x for x in arr if str(x.get("id")) == str(k)), None)
            if lab: lab.pop("id", None); f.write(json.dumps(dict(conv_id=r["conv_id"], judge=J, **lab)) + "\n")
    print(J, i + len(b), "/", len(rows), flush=True)
