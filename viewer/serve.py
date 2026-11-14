"""Local trace viewer. usage: python3 viewer/serve.py [port]   (default 8800; opens the browser)
Reads results/*.jsonl, traces/<run>/<conv_id>.json, data/items.jsonl and grading/labels/*.jsonl live from disk,
so refreshing the page shows runs as they progress. Nothing leaves this machine."""
import http.server, json, os, glob, sys, urllib.parse, webbrowser, threading
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8800

def jl(p):
    out = []
    for l in open(p):
        try: out.append(json.loads(l))
        except json.JSONDecodeError: pass
    return out

def runs():
    items = {r["item_id"]: r for r in jl(f"{ROOT}/data/items.jsonl")}
    labels = {}
    for f in glob.glob(f"{ROOT}/grading/labels/*.jsonl"):
        for x in jl(f): labels.setdefault(x["conv_id"], []).append(x)
    rows, fails = [], []
    for f in sorted(glob.glob(f"{ROOT}/results/*.jsonl")):
        if f.endswith(".fails.jsonl"):
            fails += [dict(x, tag=os.path.basename(f)[:-12]) for x in jl(f)]; continue
        for r in jl(f):
            it = items.get(r["item_id"], {})
            if "key_detail" not in r:  # older rows: join by id, flag that the key may be from a newer item build
                r["key_detail"] = (it.get("key_detail") or "?") + " [joined from current items; row predates stored keys]"; r["source_url"] = it.get("url")
            r["labels"] = labels.get(r["conv_id"], [])
            rows.append(r)
    return dict(rows=rows, fails=fails)

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def send_json(self, obj):
        b = json.dumps(obj).encode(); self.send_response(200)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if u.path == "/api/runs": return self.send_json(runs())
        if u.path == "/api/trace":
            tag, cid = os.path.basename(q["tag"][0]), os.path.basename(q["cid"][0])
            p = f"{ROOT}/traces/{tag}/{cid}.json"
            return self.send_json(json.load(open(p)) if os.path.exists(p) else {"error": "no trace file"})
        if u.path == "/api/items":
            items = jl(f"{ROOT}/data/items.jsonl"); cc = {}
            if os.path.exists(f"{ROOT}/data/crosscheck.csv"):
                import csv
                cc = {r["item_id"]: r for r in csv.DictReader(open(f"{ROOT}/data/crosscheck.csv"))}
            for it in items:
                c = cc.get(it["item_id"], {}); it["check"] = c.get("status", "not checked"); it["check_why"] = c.get("why", ""); it["official"] = c.get("official", "")

            return self.send_json(items)
        if u.path == "/dataset":
            b = open(f"{ROOT}/viewer/dataset.html", "rb").read(); self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b); return
        if u.path in ("/", "/index.html"):
            b = open(f"{ROOT}/viewer/index.html", "rb").read(); self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b); return
        self.send_error(404)

if __name__ == "__main__":
    s = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"viewer on http://127.0.0.1:{PORT}  (Ctrl-C to stop)", flush=True)
    if "--no-open" not in sys.argv: threading.Timer(0.5, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    s.serve_forever()
