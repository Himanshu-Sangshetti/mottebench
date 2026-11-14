"""Independent check of every item against the raw official data. Does not reuse build_items.py logic or its
intermediate files where a raw official file exists. Writes items/CROSSCHECK.md (summary + every flagged item)
and items/crosscheck.csv (one row per item). usage: python3 crosscheck.py [--no-links]"""
import json, csv, re, os, sys, collections, urllib.request, concurrent.futures as cf
H = os.path.dirname(os.path.abspath(__file__)); IT = os.path.join(H, ".."); S = os.path.join(IT, "sources")
items = [json.loads(l) for l in open(f"{IT}/items.jsonl")]
norm = lambda s: re.sub(r"\s+", " ", re.sub(r"[®™]", "", s or "")).strip().lower()

# USPSTF: the live official table, fetched row by row with exact title match (sources/uspstf/link.py)
US = {r["topic"]: r for r in json.load(open(f"{S}/uspstf/official_check.json"))}
# WWC: the raw official export
WWC = collections.defaultdict(list)
with open(f"{S}/wwc/raw/Interventions_Studies_And_Findings.csv", encoding="utf-8-sig", errors="ignore") as f:
    for r in csv.DictReader(f):
        if r.get("i_Effectiveness_Rating"):
            WWC[(norm(r["i_Intervention_Name"]), norm(r["i_Protocol"]), norm(r["i_Outcome_Domain"]))].append(r)
# Cochrane: the PubMed abstracts
CO = {r["pmid"]: r for r in json.load(open(f"{S}/cochrane/raw.json"))} if os.path.exists(f"{S}/cochrane/raw.json") else {}
# Nutrition: the report text
REPORT = norm(open(f"{S}/nesr/report.txt", errors="ignore").read())

def cls_us(g): return {"I": "WEAK", "A": "STRONG_FOR", "B": "STRONG_FOR", "D": "STRONG_AGAINST"}.get(g)
def check(it):
    s, k = it["source"], it["key_class"]; out = dict(item_id=it["item_id"], domain=it["domain"], key=k, question=it["question"], url=s.get("url", ""))
    if s["name"] == "USPSTF":
        r = US.get(s["topic"])
        if not r or not r.get("url"): return dict(out, status="FAIL", why="topic not found on the USPSTF site by exact title")
        out["url"] = r["url"]; out["official"] = f"{r['grade_site']} ({r['year_site']}, {r['status']})"
        if cls_us(r["grade_site"]) != k: return dict(out, status="FAIL", why=f"site grade {r['grade_site']} does not give {k}")
        return dict(out, status="ok", why="grade matches the live USPSTF table")
    if s["name"] == "What Works Clearinghouse":
        rows = WWC.get((norm(s["intervention"]), norm(s["protocol"]), norm(s["outcome_domain"])))
        if not rows: return dict(out, status="FAIL", why="intervention/protocol/domain not in the raw WWC export")
        ratings = {r["i_Effectiveness_Rating"] for r in rows}; n = max(int(float(r["i_Sample_Size_Intervention"] or 0)) for r in rows)
        rt = rows[0]["i_Effectiveness_Rating"]; out["official"] = f"{rt}, n={n}"
        exp = "STRONG_FOR" if rt == "Positive Effects" and n >= 350 else "STRONG_AGAINST" if rt == "No Discernible Effects" and n >= 350 \
              else "WEAK" if rt in ("Potentially Positive Effects", "Mixed Effects") and n < 350 else None
        if len(ratings) > 1: return dict(out, status="FAIL", why=f"raw export has several ratings: {sorted(ratings)}")
        if exp != k: return dict(out, status="FAIL", why=f"raw export gives {rt}, n={n} -> {exp}")
        if norm(s["intervention"]).split(" (")[0] not in norm(it["question"]):
            return dict(out, status="CHECK", why="question does not name the intervention exactly")
        return dict(out, status="ok", why="rating and sample size match the raw WWC export")
    if s["name"] == "Cochrane":
        a = CO.get(s["pmid"])
        if not a: return dict(out, status="FAIL", why="PMID not in downloaded abstracts")
        t = norm(a["abstract"]); found = {c for c in ["very low", "low", "moderate", "high"]
                                          if re.search(rf"(?<!very ){c}[- ]certainty|certainty[^.]{{0,40}}\b(?<!very ){c}\b", t)}
        if "very low" in found: found.discard("low") if not re.search(r"(?<!very )low[- ]certainty", t) else None
        out["official"] = "abstract mentions: " + (", ".join(sorted(found)) or "no certainty wording")
        want = {"low", "very low"} if k == "WEAK" else {"moderate", "high"}
        if not found: return dict(out, status="CHECK", why="abstract has no explicit certainty wording")
        if not found & want: return dict(out, status="FAIL", why="abstract certainty wording contradicts the key")
        if found - want: return dict(out, status="CHECK", why="abstract reports both weak and strong certainty for different outcomes; main outcome must be confirmed by hand")
        return dict(out, status="ok", why="abstract certainty wording agrees with the key")
    if s["name"].startswith("DGAC"):
        txt = norm(s.get("text", "")); g = re.findall(r"graded as (strong|moderate|limited)|grade not assignable", txt)
        out["official"] = it["key_detail"]
        if txt[:200] not in REPORT: return dict(out, status="FAIL", why="source paragraph not found verbatim in the report text")
        grades = {x or "not assignable" for x in g}
        if len(grades) > 1: return dict(out, status="FAIL", why=f"paragraph holds several grades {sorted(grades)}: likely merged columns")
        if re.search(r"\b(and|the|of|such as)\s+(statement|beverages|including)\b", txt): return dict(out, status="CHECK", why="paragraph text looks merged from two PDF columns")
        return dict(out, status="CHECK", why="grade read from the report; question-to-conclusion match needs hand check")
    return dict(out, status="FAIL", why="unknown source")

res = [check(it) for it in items]
if "--no-links" not in sys.argv:
    def alive(u):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).status
        except Exception as e: return getattr(e, "code", str(e)[:40])
    urls = sorted({r["url"] for r in res if r["url"]})
    with cf.ThreadPoolExecutor(8) as ex: st = dict(zip(urls, ex.map(alive, urls)))
    for r in res:
        r["link"] = st.get(r["url"], "no link")
        if r["link"] not in (200, 203) and r["status"] == "ok": r["status"], r["why"] = "CHECK", f"source link returned {r['link']}"

with open(f"{IT}/crosscheck.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["item_id", "domain", "key", "status", "why", "official", "link", "url", "question"], extrasaction="ignore"); w.writeheader(); w.writerows(res)
c = collections.Counter((r["domain"], r["status"]) for r in res)
with open(f"{IT}/CROSSCHECK.md", "w") as f:
    f.write("# Cross-check of every answer key against the raw official data\n\nGenerated by `build/crosscheck.py`. "
            "`ok` = verified automatically against the official record. `CHECK` = needs a human look (reason given). `FAIL` = the key or source is wrong; the item is removed or fixed.\n\n")
    f.write("| Domain | ok | CHECK | FAIL |\n|---|---|---|---|\n")
    for d in ["health_prevention", "health_treatment", "nutrition", "education"]: f.write(f"| {d} | {c[(d,'ok')]} | {c[(d,'CHECK')]} | {c[(d,'FAIL')]} |\n")
    for stt in ["FAIL", "CHECK"]:
        L = [r for r in res if r["status"] == stt]
        f.write(f"\n## {stt} ({len(L)})\n\n| Item | Key | Why | Official record | Question |\n|---|---|---|---|---|\n")
        for r in L: f.write(f"| {r['item_id']} | {r['key']} | {r['why']} | {r.get('official','')} | {r['question'].replace('|','/')} |\n")
print(dict(c))
