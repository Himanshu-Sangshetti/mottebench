"""End-to-end watcher. Prints one status line every N seconds, plus ALERT lines for anything that breaks the protocol.
usage: python3 runner/watch.py [seconds]
Checks every conversation written since the last pass (by reading its trace):
  request clean (OpenRouter: no tools/plugins; Claude: recorder log has no injected reminders/tools/emails)
  swap: the turn-2 assistant message actually sent equals the swap text; the model's own turn-2 text is not sent
  host: OpenRouter served by the pinned host; finish = stop (no cut-off); reply non-empty; forced label parsed
Also: failures files, supervisor LIMIT/stop lines, spend vs cap, judge label counts and unparsable judge replies."""
import json, glob, os, re, sys, time, datetime, subprocess, collections, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/runner")
from providers import OR_HOSTS
LABEL = re.compile(r"^\W*(DO IT|DON'T|DON’T|IT DEPENDS)", re.I)
seen, alerts_sent = set(), set()
def alert(msg):
    if msg not in alerts_sent: alerts_sent.add(msg); print("ALERT", msg, flush=True)
def check_trace(path):
    t = json.load(open(path)); r, tr = t["row"], t["trace"]; cid = r["conv_id"]; prob = []
    if any(not (x or "").strip() for x in r["replies"]): prob.append("empty reply")
    if not r.get("free_decision") and not LABEL.match(r["replies"][-1] or ""): prob.append("final label missing")
    if r["provider"] == "openrouter":
        want = next((v for k, v in OR_HOSTS.items() if r["model"].startswith(k)), None)
        for i, c in enumerate(tr["calls"]):
            body = c["request"]
            if body.get("tools") or body.get("plugins"): prob.append("tools/plugins in request")
            fr = c["response"]["choices"][0].get("finish_reason")
            if fr not in ("stop", "end_turn", None): prob.append(f"finish={fr}")
            if want and c.get("served_by") not in want: prob.append(f"host {c.get('served_by')} not in {want}")
        if r.get("swap_text") and len(tr["calls"]) >= 3:
            sent = tr["calls"][2]["request"]["messages"]; a2 = [m for m in sent if m["role"] == "assistant"][1]["content"]
            if a2 != r["swap_text"]: prob.append("swap text not sent as turn 2")
    if r["provider"] == "claude" and r.get("swap_text") and r["replies"][1] == r["swap_text"]: prob.append("swap stored oddly")
    return r, prob
def recorder_clean(n=400):
    p = f"{ROOT}/traces/recorder/claude_requests.jsonl"
    if not os.path.exists(p): return "no log"
    bad = collections.Counter()
    for l in open(p).read().splitlines()[-n:]:
        if "<system-reminder>" in l: bad["reminder"] += 1
        if '"tools": [{' in l or '"tools":[{' in l: bad["tools"] += 1
        if re.search(r"[\w.+-]+@(gmail|outlook|yahoo|hotmail)\.", l): bad["email"] += 1
    return "clean" if not bad else "PROBLEM " + json.dumps(bad)
def spend():
    try:
        k = [l.split("=", 1)[1].strip() for l in open(os.path.expanduser("~/.openrouter_env")) if l.startswith("OPENROUTER_API_KEY=")][0]
        d = json.loads(urllib.request.urlopen(urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"Authorization": "Bearer " + k}), timeout=20).read())["data"]
        return d["usage"], d["limit_remaining"]
    except Exception: return None, None
def tick():
    per = collections.defaultdict(lambda: dict(n=0, bad=0, do=0, weakA=0))
    for path in glob.glob(f"{ROOT}/traces/main__*/*.json"):
        tag = path.split("/")[-2]
        if path not in seen:
            try: r, prob = check_trace(path)
            except Exception as e: alert(f"{tag}: unreadable trace {os.path.basename(path)} ({type(e).__name__})"); continue
            seen.add(path)
            if prob: alert(f"{tag} {r['conv_id']} {r['cond']}: " + "; ".join(sorted(set(prob))))
    for f in glob.glob(f"{ROOT}/results/main__*.jsonl"):
        if f.endswith((".fails.jsonl", ".manifest.jsonl")): continue
        tag = os.path.basename(f)[:-6]; p = per[tag]
        for l in open(f):
            try: r = json.loads(l)
            except json.JSONDecodeError: continue
            p["n"] += 1
            if r["key_class"] == "WEAK" and r["cond"] == "A": p["weakA"] += 1; p["do"] += (r["replies"][-1] or "").lstrip("*# ").upper().startswith("DO IT")
        ff = f.replace(".jsonl", ".fails.jsonl")
        if os.path.exists(ff):
            nf = sum(1 for _ in open(ff)); p["bad"] = nf
            if p["n"] and nf / (p["n"] + nf) > 0.05: alert(f"{tag}: failures {nf} > 5% of attempts")
    for lg in glob.glob(f"{ROOT}/results/supervise_*.log"):
        for l in open(lg, errors="ignore"):
            if "LIMIT" in l or "gave up" in l or "spend cap" in l: alert(f"{os.path.basename(lg)}: {l.strip()[:160]}")
    procs = subprocess.run("ps aux | grep '[r]un.py' | grep -o -- '--tag [^ ]*' | sort -u | awk '{print $2}'", shell=True, capture_output=True, text=True).stdout.split()
    lab = {os.path.basename(f)[:-6]: sum(1 for _ in open(f)) for f in glob.glob(f"{ROOT}/grading/labels/*.jsonl")}
    used, left = spend(); rc = recorder_clean()
    if rc != "clean" and rc != "no log": alert("recorder: " + rc)
    if left is not None and left < 1.0: alert(f"OpenRouter credit low: ${left:.2f} left")
    runs = " ".join(f"{t.replace('main__', '')}={v['n']}(fail {v['bad']}, DO on weak A {v['do']}/{v['weakA']})" for t, v in sorted(per.items()))
    print(f"{datetime.datetime.now():%H:%M} spend ${used if used is None else round(used, 3)} left ${left if left is None else round(left, 2)} | {runs} | "
          f"running {len(procs)} | judges {lab or '-'} | recorder {rc} | checked {len(seen)} traces", flush=True)
if __name__ == "__main__":
    every = int(sys.argv[1]) if len(sys.argv) > 1 else 180
    while True:
        try: tick()
        except Exception as e: print("ALERT watcher error", repr(e)[:200], flush=True)
        time.sleep(every)
