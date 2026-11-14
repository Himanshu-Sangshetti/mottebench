"""Run the benchmark for one model.
usage: python3 run.py --provider ollama --model qwen3:8b --conds A,B,C --items core [--workers 1] [--deadline "2026-11-15 01:29"]
Writes results/<tag>.jsonl (one row per conversation) and traces/<tag>/<conv_id>.json (every call, full payloads).
Resumable: conversations already in results are skipped. Stops cleanly on a usage-limit reply."""
import argparse, json, os, sys, time, datetime, hashlib, threading, traceback, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__))
from protocol import plan, PROTOCOL_VERSION, phrase_index, swap_key_text, SWAP
from providers import PROVIDERS, LimitHit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--provider", required=True); ap.add_argument("--model", required=True)
ap.add_argument("--conds", default="A,B"); ap.add_argument("--items", default="core")
ap.add_argument("--workers", type=int, default=1); ap.add_argument("--deadline", default="2099-01-01 00:00")
ap.add_argument("--tag", default=None); ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--opts", default="{}"); ap.add_argument("--reps", type=int, default=1)
a = ap.parse_args()
tag = a.tag or f"{a.provider}__{a.model.replace('/', '_').replace(':', '_')}"
deadline = datetime.datetime.strptime(a.deadline, "%Y-%m-%d %H:%M")
items = [json.loads(l) for l in open(f"{ROOT}/items/items.jsonl")]
sel = {"core": lambda r: r["split"] == "core", "frontier": lambda r: r["split"] in ("core", "ext"),
       "all": lambda r: True, "weak_core": lambda r: r["split"] == "core" and r["key_class"] == "WEAK"}
items = [r for r in items if sel[a.items](r)]
os.makedirs(f"{ROOT}/results", exist_ok=True); os.makedirs(f"{ROOT}/traces/{tag}", exist_ok=True)
OUT = f"{ROOT}/results/{tag}.jsonl"
done = set()
if os.path.exists(OUT):
    for l in open(OUT): done.add(json.loads(l)["conv_id"])
jobs = []
for r in items:
    for c in a.conds.split(","):
        if c.startswith("E") and r["key_class"] != "WEAK": continue
        for rep in range(a.reps):
            cid = hashlib.sha1(f"{tag}|{r['item_id']}|{c}|{rep}|{PROTOCOL_VERSION}".encode()).hexdigest()[:16]
            if cid not in done: jobs.append((cid, r, c, rep))
if a.limit: jobs = jobs[:a.limit]
print(datetime.datetime.now(), tag, "jobs", len(jobs), flush=True)
fn = PROVIDERS[a.provider]; opts = json.loads(a.opts); STOP = threading.Event(); lock = threading.Lock()

def go(job):
    cid, r, c, rep = job
    if STOP.is_set() or datetime.datetime.now() >= deadline: STOP.set(); return
    base, free = c.split("_F")[0], c.endswith("_F")
    k = phrase_index(r["item_id"], base)
    system, turns, swapkey = plan(base, k, free=free)
    turns = [r["question"] if t is None else t for t in turns]
    swaptext = None
    if swapkey: swaptext = swap_key_text(swapkey, r["source"]["name"]) if base.startswith("EK") else SWAP[swapkey]
    swap = (1, swaptext) if swapkey else None
    t0 = time.time()
    for attempt in range(3):
        try:
            replies, trace = fn(a.model, system, turns, swap=swap, opts=opts); break
        except LimitHit as e:
            print("LIMIT -> stop:", e, flush=True); STOP.set(); return
        except NotImplementedError as e:
            print("skip", c, e, flush=True); return
        except Exception as e:
            err = repr(e); time.sleep(5 * (attempt + 1))
    else:
        print("FAIL", cid, err[:200], flush=True)
        with lock, open(OUT.replace(".jsonl", ".fails.jsonl"), "a") as f:
            f.write(json.dumps(dict(conv_id=cid, item_id=r["item_id"], cond=c, rep=rep, error=err[:500], ts=time.time())) + "\n")
        return
    row = dict(conv_id=cid, tag=tag, provider=a.provider, model=a.model, item_id=r["item_id"], domain=r["domain"],
               key_class=r["key_class"], cond=c, rep=rep, phrase_idx=k, free_decision=free, pilot_item=r.get("pilot", False),
               system=system, user_turns=turns, replies=replies, swap=swapkey, swap_text=swaptext, protocol=PROTOCOL_VERSION, secs=round(time.time() - t0, 1),
               ts=datetime.datetime.now().isoformat(timespec="seconds"))
    with lock:
        json.dump(dict(row=row, trace=trace), open(f"{ROOT}/traces/{tag}/{cid}.json", "w"))
        with open(OUT, "a") as f: f.write(json.dumps(row) + "\n")

with cf.ThreadPoolExecutor(a.workers) as ex: list(ex.map(go, jobs))
print(datetime.datetime.now(), tag, "stopped" if STOP.is_set() else "finished", flush=True)
