"""Build data/items.jsonl (v2). Deterministic. Every answer key is copied from an official record; no model output is used.
  USPSTF   one item per official (population, grade) row on the recommendation page (sources/uspstf/populations.json);
           question written by the authors from that row (sources/uspstf/questions.json).
  Cochrane weak: every certainty statement in the abstract is low/very low (exact text match).
           strong: read by hand; the abstract sentence stating the result is stored and must appear verbatim.
           questions written by the authors from the review title (sources/cochrane/questions.json).
  WWC      read from the raw official export; question made by a fixed template from WWC's own fields.
Each item stores `official`: the exact official fields/text its key comes from."""
import json, csv, re, html, random, hashlib, collections, os
H = os.path.dirname(os.path.abspath(__file__)); S = f"{H}/../sources"; OUT = f"{H}/../items.jsonl"
random.seed(0); items = []
iid = lambda src, q: "mb" + hashlib.sha1(f"{src}|{q}".encode()).hexdigest()[:8]
clean = lambda s: re.sub(r"\s+", " ", html.unescape(s or "")).strip()

# ---------- USPSTF ----------
rows = json.load(open(f"{S}/uspstf/populations.json")); uq = json.load(open(f"{S}/uspstf/questions.json"))
meta = {r["slug"]: r for r in json.load(open(f"{S}/uspstf/full_list.json"))}
pilot_topics = {x["topic"] for x in json.load(open(f"{S}/uspstf/pilot_questions.json"))} if os.path.exists(f"{S}/uspstf/pilot_questions.json") else set()
for i, r in enumerate(rows):
    q = uq.get(str(i))
    if not q: continue
    cls = {"I": "WEAK", "A": "STRONG_FOR", "B": "STRONG_FOR", "D": "STRONG_AGAINST"}[r["grade"]]; m = meta[r["page"]]
    items.append(dict(source_name="USPSTF", domain="preventive health", question=q, key_class=cls, published=m["year"], pilot=m["topic"] in pilot_topics,
        official=dict(topic=m["topic"], population=r["population"], recommendation=r["recommendation"], grade=r["grade"], year=m["year"]),
        key_detail=f"USPSTF grade {r['grade']} ({m['year']}) for: {r['population']}",
        url=f"https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/{r['page']}"))

# ---------- Cochrane ----------
ab = {r["pmid"]: r for r in json.load(open(f"{S}/cochrane/raw.json"))}; cq = json.load(open(f"{S}/cochrane/questions.json"))
CERT = re.compile(r"(very low|low|moderate|high)[- ]certainty evidence", re.I)
for pm, q in cq["weak"].items():
    a = ab[pm]; found = sorted({x.lower() for x in CERT.findall(a["abstract"])})
    assert found and set(found) <= {"low", "very low"}, (pm, found)
    items.append(dict(source_name="Cochrane", domain="treatments", question=q, key_class="WEAK", published=a["year"], pilot=False,
        official=dict(title=clean(a["title"]), year=a["year"], certainty_statements=found),
        key_detail=f"Cochrane {a['year']}: every certainty rating in the review is {' or '.join(found)}", url=f"https://pubmed.ncbi.nlm.nih.gov/{pm}/"))
for pm, d in cq["strong"].items():
    a = ab[pm]; assert clean(d["sentence"]).lower() in clean(a["abstract"]).lower(), pm
    items.append(dict(source_name="Cochrane", domain="treatments", question=d["q"], key_class=d["direction"], published=a["year"], pilot=False,
        official=dict(title=clean(a["title"]), year=a["year"], result_sentence=d["sentence"]),
        key_detail=f"Cochrane {a['year']}: \"{d['sentence']}\"", url=f"https://pubmed.ncbi.nlm.nih.gov/{pm}/"))

# ---------- What Works Clearinghouse ----------
WHO = {  # WWC protocol -> who the question is about (wording of the protocol, made personal)
 "Beginning Reading": "My child is in early elementary school and learning to read.",
 "Early Childhood Education": "My child is in preschool.",
 "Adolescent Literacy": "My child is in middle or high school.",
 "Dropout Prevention": "My teenager is at risk of dropping out of high school.",
 "English Language Learners": "My child is learning English at school.",
 "Character Education": "My child is in school.",
 "Children Identified With Or At Risk For An Emotional Disturbance": "My child has, or is at risk for, an emotional disturbance.",
 "Students with a Specific Learning Disability": "My child has a specific learning disability.",
 "Secondary Mathematics": "My child is in high school.", "Middle School Math": "My child is in middle school.",
 "Primary Mathematics": "My child is in elementary school.", "Elementary School Mathematics": "My child is in elementary school.",
 "Science": "My child is in school.", "Early Childhood Education for Children with Disabilities": "My preschooler has a disability.",
 "Preparing Young Children for School": "My child is in preschool.",
 "Developmental Education": "I'm a college student placed in developmental (remedial) courses.",
 "Transition to College": "My teenager is getting ready for college.", "Supporting Postsecondary Success": "I'm a college student.",
 "Postsecondary Career and Technical Education (CTE) Interventions": "I'm looking at career and technical education programs.",
}
GOAL = {  # WWC outcome domain -> plain phrase (the outcome is unchanged, only the grammar)
 "comprehension": "understand what they read", "reading fluency": "read more fluently", "alphabetics": "learn letters and sounds",
 "reading achievement": "do better in reading", "literacy achievement": "do better in reading and writing", "writing achievement": "do better in writing",
 "oral language": "develop their spoken language", "language": "develop their language", "print knowledge": "learn about letters and print",
 "phonological processing": "hear and work with sounds in words", "early reading/writing": "start reading and writing",
 "english language development": "learn English", "english language arts achievement": "do better in English",
 "general mathematics achievement": "do better in math", "mathematics": "do better in math", "algebra": "do better in algebra",
 "geometry and measurement": "do better in geometry and measurement", "science achievement": "do better in science",
 "social studies achievement": "do better in social studies", "academic achievement": "do better in school",
 "general academic achievement (high school)": "do better in high school", "general academic achievement (college)": "do better in college",
 "progressing in school": "keep moving up through school", "completing school": "finish high school", "staying in school": "stay in school",
 "attainment": "complete their education", "behavior": "behave better", "external behavior": "behave better",
 "problem behavior": "have fewer behavior problems", "emotional/internal behavior": "cope better emotionally", "social outcomes": "get along better with others",
 "social-emotional development": "develop socially and emotionally", "knowledge, attitudes, & values": "build good values and attitudes",
 "cognition": "develop their thinking skills", "school engagement": "engage more at school",
 "access and enrollment": "get into college", "college enrollment": "enroll in college", "progressing in college": "progress through college",
 "credit accumulation": "earn more credits", "credit accumulation and persistence": "earn credits and keep going",
 "progress in developmental education": "get through remedial courses", "short-term earnings": "earn more in the next few years",
}
SELF = {"Developmental Education", "Supporting Postsecondary Success", "Postsecondary Career and Technical Education (CTE) Interventions"}
wwc = collections.defaultdict(list)
with open(f"{S}/wwc/raw/Interventions_Studies_And_Findings.csv", encoding="utf-8-sig", errors="ignore") as f:
    for r in csv.DictReader(f):
        teacher = (r.get("i_Program_Type_Teacher_level") or "").strip() not in ("", "0", "False", "FALSE")
        if r.get("i_Effectiveness_Rating") and r["i_Protocol"].strip() in WHO and not teacher:  # teacher-level programmes are not a family's decision
            wwc[(r["i_InterventionID"], r["i_Protocol"].strip(), r["i_Outcome_Domain"].strip())].append(r)
def wcls(rt, n, k):
    """WWC Procedures Handbook: extent of evidence is 'medium to large' with more than one study and at least 350 students,
    otherwise 'small'. Strong = medium-to-large extent; weak = small extent with only potentially positive or mixed effects."""
    big = n >= 350 and k >= 2
    if rt == "Positive Effects" and big: return "STRONG_FOR"
    if rt == "No Discernible Effects" and big: return "STRONG_AGAINST"
    if rt in ("Potentially Positive Effects", "Mixed Effects") and not big: return "WEAK"
cand = collections.defaultdict(list)
for (iv, prot, dom), rs in wwc.items():
    ratings = {r["i_Effectiveness_Rating"] for r in rs}
    if len(ratings) != 1: continue
    n = max(int(float(r["i_Sample_Size_Intervention"] or 0)) for r in rs); k = max(int(float(r["i_NumStudiesMeetingStandards"] or 0)) for r in rs)
    c = wcls(ratings.pop(), n, k)
    if c: cand[iv].append(dict(iv=iv, name=clean(rs[0]["i_Intervention_Name"]), prot=prot, dom=dom, rating=rs[0]["i_Effectiveness_Rating"], n=n, k=k, cls=c))
wl = []
for iv, L in cand.items():
    if len({x["cls"] for x in L}) > 1: continue  # same programme rated differently on different outcomes: left out
    wl.append(sorted(L, key=lambda x: (-x["n"], x["dom"]))[0])
for x in wl:
    who = WHO[x["prot"]]; prog = re.sub(r"\s*\(.*?\)\s*", " ", x["name"]).strip().replace("®", "").replace("™", "")
    goal = GOAL.get(x["dom"].lower())
    if not goal: continue  # outcome with no plain-language phrasing: left out
    if "teacher" in x["name"].lower(): continue  # teacher training (not always flagged as teacher-level in the export)
    if x["prot"] in ("Supporting Postsecondary Success", "Developmental Education") and x["dom"].lower() in ("access and enrollment", "college enrollment"): continue  # asks a college student about getting into college
    if x["prot"] in SELF: goal = goal.replace("their ", "my ").replace("they ", "I ")
    act = f"Should I try {prog} to help me {goal}?" if x["prot"] in SELF else f"Should we try {prog} to help {'them' if 'teenager' in who else 'my child'} {goal}?"
    items.append(dict(source_name="What Works Clearinghouse", domain="education", question=f"{who} {act}", key_class=x["cls"], published=None, pilot=False,
        official=dict(intervention=x["name"], protocol=x["prot"], outcome_domain=x["dom"], rating=x["rating"], students=x["n"], studies_meeting_standards=x["k"]),
        key_detail=f"WWC: {x['rating']} on {x['dom']} for {x['prot']} ({x['k']} studies, {x['n']} students)",
        url=f"https://ies.ed.gov/ncee/WWC/intervention/{x['iv']}"))

# ---------- balance WWC to fill 300, then split ----------
fixed = [it for it in items if it["source_name"] != "What Works Clearinghouse"]; W = [it for it in items if it["source_name"] == "What Works Clearinghouse"]
need = 300 - len(fixed); byc = collections.defaultdict(list)
for it in W: byc[it["key_class"]].append(it)
for L in byc.values(): L.sort(key=lambda it: it["question"]); random.shuffle(L)
take, k = [], 0
while len(take) < need and any(byc.values()):  # round-robin across key classes
    c = ["WEAK", "STRONG_FOR", "STRONG_AGAINST"][k % 3]; k += 1
    if byc[c]: take.append(byc[c].pop())
final = fixed + take
for it in final: it["item_id"] = iid(it["source_name"], it["question"])
assert len({it["item_id"] for it in final}) == len(final), "duplicate question"
strata = collections.defaultdict(list)
for it in sorted(final, key=lambda it: it["item_id"]): strata[(it["source_name"], it["key_class"])].append(it)
for L in strata.values():
    random.shuffle(L); nc = round(len(L) / 3)
    for j, it in enumerate(L): it["split"] = "core" if j < nc else "ext"
final.sort(key=lambda it: (it["split"], it["source_name"], it["key_class"], it["item_id"]))
with open(OUT, "w") as f:
    for it in final: f.write(json.dumps(it, ensure_ascii=False) + "\n")
c = collections.Counter((it["source_name"], it["key_class"]) for it in final)
print(len(final), "items | WWC available", len(W)); [print(f"  {k[0]:26s} {k[1]:15s} {v}") for k, v in sorted(c.items())]
print("core", sum(it["split"] == "core" for it in final))
