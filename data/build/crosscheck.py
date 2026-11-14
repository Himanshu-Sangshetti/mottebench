"""Independent check of every item against the raw official data (written separately from build_items.py).
Writes data/CROSSCHECK.md and data/crosscheck.csv. usage: python3 crosscheck.py [--no-links]"""
import json, csv, re, os, sys, html, collections, urllib.request, concurrent.futures as cf
H = os.path.dirname(os.path.abspath(__file__)); D = f"{H}/.."; S = f"{D}/sources"
items = [json.loads(l) for l in open(f"{D}/items.jsonl")]
T = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip().lower()
CLS = {"I": "WEAK", "A": "STRONG_FOR", "B": "STRONG_FOR", "D": "STRONG_AGAINST"}

site = {r["slug"]: r for r in json.load(open(f"{S}/uspstf/full_list.json"))}  # the live search table
abstracts = {r["pmid"]: r for r in json.load(open(f"{S}/cochrane/raw.json"))}
wwc = collections.defaultdict(list)
with open(f"{S}/wwc/raw/Interventions_Studies_And_Findings.csv", encoding="utf-8-sig", errors="ignore") as f:
    for r in csv.DictReader(f):
        if r.get("i_Effectiveness_Rating"): wwc[(r["i_InterventionID"], r["i_Protocol"].strip(), r["i_Outcome_Domain"].strip())].append(r)

def check(it):
    o, k = it["official"], it["key_class"]; base = dict(item_id=it["item_id"], source=it["source_name"], key=k, question=it["question"], url=it["url"])
    if it["source_name"] == "USPSTF":
        slug = it["url"].rsplit("/", 1)[1]; page = T(open(f"{S}/uspstf/pages/{slug}.html", encoding="utf-8", errors="ignore").read())
        live = site.get(slug, {})
        if live.get("status") != "Published": return dict(base, status="FAIL", why="recommendation not current on the USPSTF site")
        if o["grade"] not in [g.strip() for g in live.get("grade", "").split(",")]: return dict(base, status="FAIL", why=f"grade {o['grade']} not among the site's grades {live.get('grade')}")
        if CLS[o["grade"]] != k: return dict(base, status="FAIL", why="key does not follow from grade")
        if T(o["population"])[:60] not in page or T(o["recommendation"])[:80] not in page: return dict(base, status="FAIL", why="population/recommendation text not found on the saved official page")
        return dict(base, status="ok", why=f"grade {o['grade']} for '{o['population'][:60]}' found on the official page and in the live table", official=f"{o['grade']} ({o['year']})")
    if it["source_name"] == "Cochrane":
        pm = it["url"].rstrip("/").rsplit("/", 1)[1]; a = abstracts.get(pm)
        if not a: return dict(base, status="FAIL", why="PMID not in downloaded abstracts")
        t = T(a["abstract"]); cert = set(re.findall(r"(very low|low|moderate|high)[- ]certainty evidence", t))
        if k == "WEAK":
            if not cert or not cert <= {"low", "very low"}: return dict(base, status="FAIL", why=f"certainty statements {sorted(cert)} are not all low/very low")
            return dict(base, status="ok", why=f"every certainty statement is {'/'.join(sorted(cert))}", official="/".join(sorted(cert)))
        if T(o["result_sentence"]) not in t: return dict(base, status="FAIL", why="result sentence not found verbatim in the abstract")
        return dict(base, status="ok", why="result sentence found verbatim; direction read by hand", official=o["result_sentence"][:80])
    if it["source_name"] == "What Works Clearinghouse":
        iv = it["url"].rsplit("/", 1)[1]; rs = wwc.get((iv, o["protocol"], o["outcome_domain"]))
        if not rs: return dict(base, status="FAIL", why="not found in the raw WWC export")
        rt = {r["i_Effectiveness_Rating"] for r in rs}; n = max(int(float(r["i_Sample_Size_Intervention"] or 0)) for r in rs); s = max(int(float(r["i_NumStudiesMeetingStandards"] or 0)) for r in rs)
        if len(rt) != 1: return dict(base, status="FAIL", why=f"several ratings {sorted(rt)}")
        rt = rt.pop(); big = n >= 350 and s >= 2
        exp = "STRONG_FOR" if rt == "Positive Effects" and big else "STRONG_AGAINST" if rt == "No Discernible Effects" and big else "WEAK" if rt in ("Potentially Positive Effects", "Mixed Effects") and not big else None
        if exp != k: return dict(base, status="FAIL", why=f"export gives {rt}, {s} studies, {n} students -> {exp}")
        name = re.sub(r"\s*\(.*?\)\s*", " ", o["intervention"]).replace("®", "").replace("™", "").strip().lower()
        if name not in it["question"].lower(): return dict(base, status="CHECK", why="question does not contain the programme name")
        return dict(base, status="ok", why=f"{rt}, {s} studies, {n} students in the raw export", official=f"{rt}; {s} studies; {n} students")
    return dict(base, status="FAIL", why="unknown source")

res = [check(it) for it in items]
if "--no-links" not in sys.argv:
    def alive(u):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).status
        except Exception as e: return getattr(e, "code", str(e)[:40])
    urls = sorted({r["url"] for r in res})
    with cf.ThreadPoolExecutor(8) as ex: st = dict(zip(urls, ex.map(alive, urls)))
    for r in res:
        r["link"] = st[r["url"]]
        if r["link"] not in (200, 203) and r["status"] == "ok": r["status"], r["why"] = "CHECK", f"official link returned {r['link']}"
with open(f"{D}/crosscheck.csv", "w", newline="") as f:
    w = csv.DictWriter(f, ["item_id", "source", "key", "status", "why", "official", "link", "url", "question"], extrasaction="ignore"); w.writeheader(); w.writerows(res)
c = collections.Counter((r["source"], r["status"]) for r in res)
with open(f"{D}/CROSSCHECK.md", "w") as f:
    f.write("# Cross-check of every answer key against the raw official data\n\nGenerated by `build/crosscheck.py`, written separately from the build script. "
            "`ok` = the key re-derived from the official record matches. `CHECK` = needs a human look. `FAIL` = wrong.\n\n| Source | ok | CHECK | FAIL |\n|---|---|---|---|\n")
    for s in ["USPSTF", "Cochrane", "What Works Clearinghouse"]: f.write(f"| {s} | {c[(s,'ok')]} | {c[(s,'CHECK')]} | {c[(s,'FAIL')]} |\n")
    for stt in ["FAIL", "CHECK"]:
        L = [r for r in res if r["status"] == stt]
        f.write(f"\n## {stt} ({len(L)})\n\n" + ("| Item | Key | Why | Question |\n|---|---|---|---|\n" + "".join(f"| {r['item_id']} | {r['key']} | {r['why']} | {r['question']} |\n" for r in L) if L else "None.\n"))
print(dict(c))
