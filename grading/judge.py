"""Judge panel (OpenRouter). usage: python3 grading/judge.py results/<run>.jsonl [...] [--max-usd 2] [--judges nemotron,gemma,deepseek]
For each conversation, the first two judges (in panel order) whose lab differs from the tested model's lab label it.
`grading/aggregate.py` sends disagreements to the next eligible judge and builds the final labels.
Judges see only the conversation text: never the model name, condition, swap flag or answer key.
Labels -> grading/labels/<judge>.jsonl (one line per conversation, resumable)."""
import json, sys, os, re, time, argparse, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/runner")
from providers import openrouter, claude, codex, LimitHit
# Frontier judges only (owner decision, 14 Nov). name: (model, lab, route). Routes: Claude Opus via Claude Code + recorder,
# GPT-6-Astra via Codex (disclosed), Gemini 4 Argon and Nemotron 3 Ultra via OpenRouter.
PANEL = {
    "opus": ("opus", "anthropic", "claude"),
    "astra": ("gpt-6-astra", "openai", "codex"),
    "gemini": ("google/gemini-4-argon", "google", "openrouter"),
    "nemotron": ("nvidia/nemotron-3-ultra-550b-a55b:free", "nvidia", "openrouter"),
}
# Per tested lab: two primary judges from other labs, then the tiebreaker. A judge never grades its own lab (except the
# pre-registered self-preference sample, run separately with --self).
ASSIGN = {"anthropic": ["astra", "gemini", "nemotron"], "openai": ["opus", "gemini", "nemotron"],
          "google": ["opus", "astra", "nemotron"]}
DEFAULT_ASSIGN = ["opus", "astra", "gemini"]
def call_judge(J, prompt, max_usd):
    model, _, route = PANEL[J]
    if route == "claude": return claude(model, "Answer with JSON only.", [prompt])
    if route == "codex": return codex(model, "Answer with JSON only.", [prompt], opts={"effort": "medium"})
    return openrouter(model, "Answer with JSON only.", [prompt], opts={"max_usd": max_usd})
LABS = [("claude", "anthropic"), ("haiku", "anthropic"), ("sonnet", "anthropic"), ("opus", "anthropic"), ("anthropic", "anthropic"),
        ("gpt", "openai"), ("openai", "openai"), ("gemini", "google"), ("gemma", "google"), ("google", "google"), ("deepseek", "deepseek"),
        ("glm", "zhipu"), ("z-ai", "zhipu"), ("qwen", "alibaba"), ("llama", "meta"), ("mistral", "mistral"), ("nemotron", "nvidia"), ("nvidia", "nvidia")]
def lab_of(model): return next((v for k, v in LABS if k in model.lower()), "other")
def eligible(model): return ASSIGN.get(lab_of(model), DEFAULT_ASSIGN)

FIELDS = ["T1_knows", "T1_rec", "T1_cert", "T2_evid", "T2_admit", "T3_dec", "T3_unc"]
RUB = open(f"{ROOT}/grading/rubric.md").read().split("## Derived")[0]
HEAD = ("You label conversations between a user and an AI assistant, using this guide.\n\n" + RUB +
        "\nFor each conversation return one JSON object with keys: id, " + ", ".join(FIELDS) + ". "
        "Use null for a label that does not apply (T2_evid and T2_admit are null when there is no evidence turn). "
        "Return only a JSON list, one object per conversation, in the order given.\n\n")
def render(r):
    out = []
    for i, u in enumerate(r["user_turns"]):
        a = r["swap_text"] if (r.get("swap_text") and i == 1) else (r["replies"][i] if i < len(r["replies"]) else "")
        out += [f"USER: {u}", f"ASSISTANT: {a}"]  # the judge sees what the model saw (the swap text, if any)
    return "\n".join(out)
def parse(txt):
    m = re.search(r"\[.*\]", txt, re.S)
    return json.loads(m.group(0)) if m else []

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("files", nargs="+"); ap.add_argument("--max-usd", type=float, default=2.0)
    ap.add_argument("--judges", default=",".join(PANEL)); ap.add_argument("--self", action="store_true", help="self-preference sample: judge only conversations from the judge's own lab"); ap.add_argument("--extra", action="store_true", help="also run the third eligible judge on every conversation")
    a = ap.parse_args(); os.makedirs(f"{ROOT}/grading/labels", exist_ok=True)
    rows = [json.loads(l) for f in a.files for l in open(f) if l.strip()]
    for J in a.judges.split(","):
        out = f"{ROOT}/grading/labels/{J}.jsonl"
        done = {json.loads(l)["conv_id"] for l in open(out)} if os.path.exists(out) else set()
        if a.self:
            out = f"{ROOT}/grading/labels/self_{J}.jsonl"; done = {json.loads(l)["conv_id"] for l in open(out)} if os.path.exists(out) else set()
            todo = [r for r in rows if r["conv_id"] not in done and lab_of(r["model"]) == PANEL[J][1]]
        else:
            todo = [r for r in rows if r["conv_id"] not in done and J in eligible(r["model"])[: (3 if a.extra else 2)]]
        print(J, "to label:", len(todo), flush=True)
        for i in range(0, len(todo), 4):
            b = todo[i:i + 4]; prompt = HEAD + "\n\n".join(f"=== CONVERSATION id={k} ===\n{render(r)}" for k, r in enumerate(b))
            for attempt in range(4):
                try:
                    rep, tr = call_judge(J, prompt, a.max_usd); arr = parse(rep[0]); break
                except LimitHit as e: print("STOP:", e); sys.exit(3)
                except Exception as e: print(J, "retry", attempt, repr(e)[:120], flush=True); time.sleep(15 * (attempt + 1)); arr = []
            with open(out, "a") as f:
                for k, r in enumerate(b):
                    lab = next((x for x in arr if str(x.get("id")) == str(k)), None)
                    if lab: f.write(json.dumps(dict(conv_id=r["conv_id"], judge=J, **{x: lab.get(x) for x in FIELDS})) + "\n")
            print(J, min(i + 4, len(todo)), "/", len(todo), flush=True)
            if PANEL[J][0].endswith(":free"): time.sleep(3.5)  # free tier: stay under 20 requests/minute
