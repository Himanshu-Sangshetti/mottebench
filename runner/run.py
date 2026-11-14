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
items = [json.loads(l) for l in open(f"{ROOT}/data/items.jsonl")]
sel = {"core": lambda r: r["split"] == "core", "frontier": lambda r: r["split"] in ("core", "ext"),
       "all": lambda r: True, "weak_core": lambda r: r["split"] == "core" and r["key_class"] == "WEAK",
       "q30": lambda r: True}  # q30: filtered below to the 30 items with rewordings
items = [r for r in items if sel[a.items](r)]
_rw = f"{ROOT}/data/sources/rewordings.json"  # condition _Q (Amendment 1.2)
if os.path.exists(_rw):
    _q = {k: v for k, v in json.load(open(_rw)).items() if not k.startswith("_")}
    for r in items:
        if r["item_id"] in _q: r["q_alt"] = _q[r["item_id"]]
if a.items == "q30": items = [r for r in items if r.get("q_alt")]
os.makedirs(f"{ROOT}/results", exist_ok=True); os.makedirs(f"{ROOT}/traces/{tag}", exist_ok=True)
OUT = f"{ROOT}/results/{tag}.jsonl"
done = set()
def read_rows(path):
    """Read a results file; a line cut short by a crash is skipped (that conversation simply reruns)."""
    out = []
    if os.path.exists(path):
        for l in open(path):
            try: out.append(json.loads(l))
            except json.JSONDecodeError: print("skipping partial line in", path, flush=True)
    return out
for r0 in read_rows(OUT): done.add(r0["conv_id"])
if os.path.exists(OUT) and os.path.getsize(OUT):  # a crash can leave the last line unterminated; close it so new rows start clean
    with open(OUT, "rb") as f: f.seek(-1, 2); tail = f.read(1)
    if tail != b"\n":
        with open(OUT, "a") as f: f.write("\n")
jobs = []
for r in items:
    for c in a.conds.split(","):
        if c.startswith("E") and r["key_class"] != "WEAK": continue
        if "_Q" in c and not r.get("q_alt"): continue
        for rep in range(a.reps):
            cid = hashlib.sha1(f"{tag}|{r['item_id']}|{c}|{rep}|{PROTOCOL_VERSION}".encode()).hexdigest()[:16]
            if cid not in done: jobs.append((cid, r, c, rep))
if a.limit: jobs = jobs[:a.limit]
def _sh(cmd):
    try: return __import__("subprocess").run(cmd, capture_output=True, text=True, timeout=30, cwd=ROOT).stdout.strip()[:200]
    except Exception as e: return f"unavailable ({type(e).__name__})"
GIT = _sh(["git", "rev-parse", "HEAD"]); DIRTY = bool(_sh(["git", "status", "--porcelain", "runner", "data/items.jsonl"]))
ACCESS = {"claude": "Claude Code CLI through the sanitizing recorder", "openrouter": "OpenRouter chat API (no tools, no plugins)",
          "ollama": "local Ollama API", "codex": "Codex CLI agent harness (sensitivity only)", "opencode": "OpenCode CLI harness"}[a.provider]
manifest = dict(tag=tag, provider=a.provider, access=ACCESS, model=a.model, args=vars(a), protocol=PROTOCOL_VERSION, git_commit=GIT,
                git_dirty=DIRTY, python=sys.version.split()[0], started=datetime.datetime.now().isoformat(timespec="seconds"),
                items_sha1=hashlib.sha1(open(f"{ROOT}/data/items.jsonl", "rb").read()).hexdigest(),
                tool_version={"claude": _sh(["claude", "--version"]), "codex": _sh(["codex", "--version"]), "ollama": _sh(["ollama", "--version"])}.get(a.provider, "n/a"))
with open(f"{ROOT}/results/{tag}.manifest.jsonl", "a") as f: f.write(json.dumps(manifest) + "\n")  # one line per (re)start
if DIRTY: print("WARNING: runner or data has uncommitted changes; results will be marked git_dirty", flush=True)
print(datetime.datetime.now(), tag, "jobs", len(jobs), flush=True)
fn = PROVIDERS[a.provider]; opts = json.loads(a.opts); STOP = threading.Event(); lock = threading.Lock()

def go(job):
    try: _go(job)
    except Exception:
        err = traceback.format_exc()
        print("JOB ERROR", job[0], err[-300:], flush=True)
        with lock, open(OUT.replace(".jsonl", ".fails.jsonl"), "a") as f:
            f.write(json.dumps(dict(conv_id=job[0], item_id=job[1]["item_id"], cond=job[2], rep=job[3], error=err[-500:], ts=time.time())) + "\n")

def _go(job):
    cid, r, c, rep = job
    if STOP.is_set() or datetime.datetime.now() >= deadline: STOP.set(); return
    import re
    free = "_F" in c; qv = re.search(r"_Q(\d)", c); base = re.sub(r"_(F|Q\d)", "", c)
    k = phrase_index(r["item_id"], base)
    system, turns, swapkey = plan(base, k, free=free)
    q = r["question"] if not qv else r.get("q_alt", [])[int(qv.group(1)) - 1] if len(r.get("q_alt", [])) >= int(qv.group(1)) else None
    if q is None: return  # item has no reworded version for this slot
    turns = [q if t is None else t for t in turns]
    swaptext = None
    if swapkey: swaptext = swap_key_text(swapkey, r["source_name"]) if base.startswith("EK") else SWAP[swapkey]
    swap = (1, swaptext) if swapkey else None
    t0 = time.time()
    for attempt in range(3):
        try:
            o = dict(opts, seed=rep) if a.provider == "ollama" else opts  # local models: seed = repeat index, so repeats differ
            replies, trace = fn(a.model, system, turns, swap=swap, opts=o); break
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
    row = dict(conv_id=cid, tag=tag, provider=a.provider, model=a.model, item_id=r["item_id"], domain=r["domain"], published=r.get("published"),
               key_class=r["key_class"], key_detail=r.get("key_detail"), source_name=r["source_name"], source_url=r["url"], official=r["official"], question_original=r["question"], cond=c, rep=rep, phrase_idx=k, free_decision=free, question_variant=int(qv.group(1)) if qv else 0, pilot_item=r.get("pilot", False),
               system=system, user_turns=turns, replies=replies, swap=swapkey, swap_text=swaptext, protocol=PROTOCOL_VERSION, access=ACCESS, git_commit=GIT, git_dirty=DIRTY, secs=round(time.time() - t0, 1),
               ts=datetime.datetime.now().isoformat(timespec="seconds"))
    with lock:
        tp = f"{ROOT}/traces/{tag}/{cid}.json"
        with open(tp + ".tmp", "w") as f: json.dump(dict(row=row, trace=trace), f); f.flush(); os.fsync(f.fileno())
        os.replace(tp + ".tmp", tp)
        with open(OUT, "a") as f: f.write(json.dumps(row) + "\n"); f.flush(); os.fsync(f.fileno())

with cf.ThreadPoolExecutor(a.workers) as ex: list(ex.map(go, jobs))
left = len([j for j in jobs if j[0] not in {x["conv_id"] for x in read_rows(OUT)}])
print(datetime.datetime.now(), tag, "stopped" if STOP.is_set() else "finished", "left", left, flush=True)
sys.exit(3 if STOP.is_set() else (4 if left else 0))  # 4 = some conversations failed; supervisor retries them
