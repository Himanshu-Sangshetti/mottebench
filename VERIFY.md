# Verifying the setup (before any paid run)

Everything below runs locally and costs nothing.

1. **What we test and predict** - `plan/PLAN.md` (pre-registration + amendments), `plan/RUNS.md` (models, order, stop rules).
2. **The exact words sent to models** - `runner/protocol.py`. Every turn, every phrasing, the swap texts.
3. **The questions and answer keys** - `data/QUESTIONS.md` (readable) or `data/items.jsonl`: question, official record, verdict, link. `data/CROSSCHECK.md`: independent re-check of every key.
   Spot-check: `python3 -c "import json,random;L=[json.loads(l) for l in open('data/items.jsonl')];[print(r['key_class'],'|',r['question'],'|',r['key_detail'],'|',r['url']) for r in random.sample(L,10)]"`
4. **A real run, end to end, on a free local model**
   `runner/supervise.sh --provider ollama --model qwen3:8b --conds A,B,EK_WEAK --items weak_core --limit 6 --tag verify_qwen`
   Then open any file in `traces/verify_qwen/`: it holds every message sent and every raw reply.
   In an EK_WEAK conversation, turn 2 is our swap text, not the model's own words.
5. **Crash safety** - stop step 4 with Ctrl-C half way, run the same command again: it continues where it stopped.
6. **Monitor** - `python3 runner/status.py`.
7. **Claude calls are clean** - `traces/recorder/claude_requests.jsonl`: each line is the exact request that left this Mac
   (system prompt + our turns, nothing else). `python3 runner/status.py` also checks it automatically.
8. **Scoring** - `grading/rubric.md` (labels + worked examples), `grading/judge.py` (no judge grades its own lab).
9. **History** - `git log`: plan committed before any main data; every later change is a dated amendment.
