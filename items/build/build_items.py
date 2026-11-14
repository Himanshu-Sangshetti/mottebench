"""Assemble items/items.jsonl from the four sources. Deterministic (seed 0).
Key rule: an item is kept only if its key class is unambiguous; Cochrane and nutrition keys must agree between
two independent labelers (Qwen3-8B draft + DeepSeek V4.1 Flash cross-label); WWC and USPSTF keys come straight
from the official rating fields."""
import json, re, random, collections, os
S = "../sources"; random.seed(0)
def J(p): return [json.loads(l) for l in open(p)] if p.endswith("l") else json.load(open(p))
def is_action(q): return bool(re.match(r"^(i'm|i am|my|i have|i've|we|our|i)\b.*\bshould\b|^should\b", q.strip(), re.I)) or q.lower().startswith("should")
def norm(q): return re.sub(r"[^a-z ]", "", q.lower())
items = []

# --- USPSTF (official grade) ---
off = {x["topic"]: x for x in J(f"{S}/uspstf/official_list.json")}
uurl = {x["topic"]: x.get("url") for x in J(f"{S}/uspstf/official_check.json")}  # exact recommendation page (link.py)
qs = {x["topic"]: x["q"] for x in J(f"{S}/uspstf/pilot_questions.json")}; pilot_topics = set(qs); qs.update(J(f"{S}/uspstf/added_questions.json"))
for t, q in qs.items():
    g = off[t]["grade"]; cls = {"I": "WEAK", "A": "STRONG_FOR", "B": "STRONG_FOR", "D": "STRONG_AGAINST"}.get(g)
    if cls: items.append(dict(domain="health_prevention", pilot=t in pilot_topics, question=q, key_class=cls, key_detail=f"USPSTF grade {g} ({off[t]['year']})",
                              source=dict(name="USPSTF", topic=t, url=uurl.get(t) or "https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics")))

# --- Cochrane (two labelers must agree) ---
A = {r["pmid"]: r for r in J(f"{S}/cochrane/labeled.jsonl")}
B = {r["src_id"]: r for r in J(f"{S}/cochrane/cross.jsonl")} if os.path.exists(f"{S}/cochrane/cross.jsonl") else {}
bucket = lambda c: "S" if c in ("high", "moderate") else ("W" if c in ("low", "very_low") else None)
agree = collections.Counter()
for pm, a in A.items():
    b = B.get(pm)
    if not a.get("consumer_relevant") or not b: continue
    ca, cb = bucket(a.get("certainty")), bucket(b.get("certainty"))
    ok = ca == cb and ca is not None
    if ok and ca == "S": ok = a.get("direction") == b.get("direction") and a.get("direction") in ("benefit", "no_benefit")
    agree[ok] += 1
    if not ok or not is_action(a.get("question", "")): continue
    cls = "WEAK" if ca == "W" else ("STRONG_FOR" if a["direction"] == "benefit" else "STRONG_AGAINST")
    items.append(dict(domain="health_treatment", question=a["question"], key_class=cls,
                      key_detail=f"Cochrane {a['year']}: {a.get('main_outcome','')} - certainty {a['certainty']}, {a['direction']}",
                      source=dict(name="Cochrane", pmid=pm, title=a["title"], url=f"https://pubmed.ncbi.nlm.nih.gov/{pm}/")))
print("cochrane labeler agreement", dict(agree))

# --- Nutrition (DGAC 2025 grade; action direction must be confirmed by second labeler) ---
C = {r["src_id"]: r for r in J(f"{S}/nesr/cross.jsonl")} if os.path.exists(f"{S}/nesr/cross.jsonl") else {}
for d in J(f"{S}/nesr/drafted.jsonl"):
    q = d.get("question", ""); g = d["source"]["grade"]
    if not d.get("consumer_relevant") or not is_action(q): continue
    if g in ("limited", "not assignable"): cls = "WEAK"
    else:
        c = C.get(d["src_id"], {}).get("supported")
        cls = {"yes": "STRONG_FOR", "no": "STRONG_AGAINST"}.get(c)
        if not cls: continue
    items.append(dict(domain="nutrition", question=q, key_class=cls, key_detail=f"DGAC 2025 conclusion graded {g}",
                      source=dict(name="DGAC 2025 Scientific Report", text=d["source"]["text"][:600],
                                  url="https://www.dietaryguidelines.gov/2025-advisory-committee-report")))

# --- Education (WWC official effectiveness rating + sample size) ---
for d in J(f"{S}/wwc/drafted.jsonl") if os.path.exists(f"{S}/wwc/drafted.jsonl") else []:
    s = d["source"]; q = d.get("question", ""); n = int(s.get("n") or 0); r = s["rating"]
    if not d.get("consumer_relevant") or not is_action(q): continue
    if r == "Positive Effects" and n >= 350: cls = "STRONG_FOR"
    elif r == "No Discernible Effects" and n >= 350: cls = "STRONG_AGAINST"
    elif r in ("Potentially Positive Effects", "Mixed Effects") and n < 350: cls = "WEAK"
    else: continue
    items.append(dict(domain="education", question=q, key_class=cls, key_detail=f"WWC: {r} on {s['domain']} (n={n})",
                      source=dict(name="What Works Clearinghouse", intervention=s["name"], protocol=s["protocol"],
                                  outcome_domain=s["domain"], url="https://ies.ed.gov/ncee/WWC" + s.get("url", ""))))

# --- dedupe near-identical questions, one WWC item per intervention ---
seen, seen_iv, out = set(), set(), []
for it in items:
    k = norm(it["question"])[:70]; iv = it["source"].get("intervention")
    if k in seen or (iv and iv in seen_iv): continue
    seen.add(k); seen_iv.add(iv) if iv else None; out.append(it)

# --- cap per domain x class for balance, then split core/ext/heldout (stratified) ---
CAP = {"health_prevention": 60, "health_treatment": 50, "nutrition": 45, "education": 45}
by = collections.defaultdict(list)
for it in out: by[(it["domain"], it["key_class"])].append(it)
final = []
for (dom, cls), L in sorted(by.items()):
    random.shuffle(L); cap = CAP[dom] if cls == "WEAK" else CAP[dom] // 2
    final += L[:cap]
random.shuffle(final)
strata = collections.defaultdict(list)
for it in final: strata[(it["domain"], it["key_class"])].append(it)
N = len(final); tgt = {"core": 100, "ext": 200}
for L in strata.values():
    nc = round(len(L) * 100 / N); ne = round(len(L) * 200 / N)
    for j, it in enumerate(L): it["split"] = "core" if j < nc else ("ext" if j < nc + ne else "heldout")
for i, it in enumerate(sorted(final, key=lambda x: (x["split"], x["domain"], x["key_class"], x["question"]))):
    it["idx"] = i; it["item_id"] = "mb" + __import__("hashlib").sha1((it["source"]["name"] + "|" + it["question"]).encode()).hexdigest()[:8]  # stable across rebuilds
final.sort(key=lambda x: x["idx"])
with open("../items.jsonl", "w") as f:
    for it in final: f.write(json.dumps(it) + "\n")
c = collections.Counter((it["split"], it["domain"], it["key_class"]) for it in final)
print(len(final)); [print(k, v) for k, v in sorted(c.items())]
