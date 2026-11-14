"""Run monitor. usage: python3 runner/status.py [--watch 60]
Per run: conversations done per condition, failures, speed, last activity, decision-format compliance,
and a quick DO-IT rate on WEAK items (sanity only, not a result). Also checks the Claude recorder log
for anything that should not reach the model (injected reminders, tool lists, emails)."""
import json, os, glob, re, sys, time, datetime, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABEL = re.compile(r"^\W*(DO IT|DON'T|DON’T|IT DEPENDS)", re.I)

def runs():
    out = []
    for f in sorted(glob.glob(f"{ROOT}/results/*.jsonl")):
        if f.endswith(".fails.jsonl") or "/test_" in f: continue
        rows = [json.loads(l) for l in open(f)]
        if not rows: continue
        fails = sum(1 for _ in open(f.replace(".jsonl", ".fails.jsonl"))) if os.path.exists(f.replace(".jsonl", ".fails.jsonl")) else 0
        by = collections.Counter(r["cond"] for r in rows)
        forced = [r for r in rows if not r.get("free_decision")]
        ok = sum(bool(LABEL.match(r["replies"][-1] or "")) for r in forced)
        weak = [r for r in forced if r["key_class"] == "WEAK" and r["cond"] in ("A", "B")]
        do = sum(r["replies"][-1].strip().upper().startswith("DO IT") for r in weak)
        ts = [datetime.datetime.fromisoformat(r["ts"]) for r in rows]
        last = max(ts); span = (last - min(ts)).total_seconds() / 3600 or 1e-9
        out.append(dict(tag=os.path.basename(f)[:-6], n=len(rows), fails=fails, conds=dict(sorted(by.items())),
                        per_hour=round(len(rows) / span), idle_min=round((datetime.datetime.now() - last).total_seconds() / 60),
                        label_ok=f"{ok}/{len(forced)}", weak_do=f"{do}/{len(weak)}"))
    return out

def recorder_check(n=200):
    p = f"{ROOT}/traces/recorder/claude_requests.jsonl"
    if not os.path.exists(p): return "no recorder log"
    lines = open(p).read().splitlines()[-n:]; bad = collections.Counter()
    for l in lines:
        s = l
        if "<system-reminder>" in s: bad["system-reminder"] += 1
        if '"tools": [{' in s or '"tools":[{' in s: bad["tool list"] += 1
        if "Agent SDK" in s: bad["SDK line"] += 1
        if re.search(r"[\w.+-]+@[\w-]+\.(com|org|net|io)", s): bad["email"] += 1
    return f"last {len(lines)} requests: " + ("clean" if not bad else "PROBLEM " + json.dumps(bad))

def show():
    print(datetime.datetime.now().strftime("%a %d %b %H:%M"))
    for r in runs():
        flag = "  <-- stalled?" if r["idle_min"] > 20 else ""
        print(f"{r['tag']:42s} done {r['n']:5d}  fails {r['fails']:3d}  {r['per_hour']:4d}/h  idle {r['idle_min']}m{flag}")
        print(f"   {r['conds']}  label ok {r['label_ok']}  DO on WEAK(A,B) {r['weak_do']}")
    print("recorder:", recorder_check())
    sp = os.path.expanduser("~/.mottebench_spend.json")
    if os.path.exists(sp): print("api spend ledger:", json.load(open(sp)))

if __name__ == "__main__":
    if "--watch" in sys.argv:
        while True: os.system("clear"); show(); time.sleep(int(sys.argv[sys.argv.index("--watch") + 1]))
    show()
