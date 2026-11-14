#!/bin/bash
# Trial before any bulk run: 5 conversations per OpenRouter model (2 x A, 1 x B, 1 x EK_WEAK, 1 x C on WEAK core items),
# then the judge panel on them. Hard spend cap for the whole trial. Prints cost per conversation and time per call.
cd "$(dirname "$0")/.." || exit 1
CAP=${CAP:-1.50}
for M in anthropic/claude-haiku-5.5 deepseek/deepseek-v4-pro z-ai/glm-5.3 openai/gpt-6.1-sol openai/gpt-6.1-sol:batch; do
  T="trial__$(echo $M | tr '/:' '__')"
  python3 runner/run.py --provider openrouter --model "$M" --conds A,B,EK_WEAK,C --items weak_core --limit 5 --tag "$T" --opts "{\"max_usd\": $CAP}" || true
done
python3 grading/judge.py results/trial__*.jsonl --max-usd $CAP
python3 grading/aggregate.py results/trial__*.jsonl
python3 - <<'PY'
import json, glob
for f in sorted(glob.glob("traces/trial__*/*.json")): pass
by = {}
for f in glob.glob("traces/trial__*/*.json"):
    t = json.load(open(f)); tag = f.split("/")[1]; c = by.setdefault(tag, dict(n=0, usd=0, secs=[], hosts=set(), reasoning_tokens=0))
    c["n"] += 1
    for call in t["trace"]["calls"]:
        u = call["response"].get("usage") or {}; c["usd"] += u.get("cost") or 0; c["secs"].append(round(call["secs"], 1)); c["hosts"].add(call.get("served_by"))
        c["reasoning_tokens"] += (u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
for k, c in sorted(by.items()):
    print(f"{k:45s} convs {c['n']}  cost/conv ${c['usd']/max(c['n'],1):.4f}  max call {max(c['secs'] or [0])}s  served by {c['hosts']}  reasoning tokens {c['reasoning_tokens']}")
print("spend ledger:", json.load(open(__import__('os').path.expanduser('~/.mottebench_spend.json'))))
PY
