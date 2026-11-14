"""Collect every USPSTF recommendation topic from the official site search (20 rows per query, so many queries, unioned)."""
import re, html as H, json, urllib.request, urllib.parse, time, string
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S); seen = {}
terms = list(string.ascii_lowercase) + ["screening", "prevention", "counseling", "medication", "interventions", "cancer", "infection", "adults", "children",
         "pregnancy", "women", "men", "older", "disease", "risk", "use", "behavioral", "supplementation", "vitamin", "aspirin", "statin", "depression",
         "alcohol", "tobacco", "falls", "osteoporosis", "breast", "colorectal", "cervical", "prostate", "skin", "weight", "diabetes", "blood", "heart", "abuse", "violence"] + "spine scoliosis carotid testicular eye hearing vision dental oral sleep bone lung liver kidney hepatitis hiv syphilis chlamydia gonorrhea herpes tuberculosis anemia iron folic thyroid glaucoma autism speech lipid cholesterol aortic aneurysm bacteriuria rh intimate elder unhealthy drug suicide anxiety cognitive dementia atrial hypertension obesity exercise physical diet breastfeeding contraception genetic brca newborn infant pregnant perinatal gestational preeclampsia fracture ovarian pancreatic bladder celiac food maltreatment eating skin melanoma gonococcal ocular vitamin d hormone menopausal estrogen".split()
for t in terms:
    u = "https://www.uspreventiveservicestaskforce.org/uspstf/topic_search_results?searchterm=" + urllib.parse.quote(t)
    p = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8", "ignore")
    for tr in ROW.findall(p):
        m = re.search(r"href='/uspstf/recommendation/([a-z0-9-]+)'", tr)
        c = [H.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if m and len(c) >= 6: seen[m.group(1)] = dict(slug=m.group(1), status=c[0], type=c[1], year=c[2], topic=c[3], age=c[4], grade=c[5])
    time.sleep(0.3)
json.dump(sorted(seen.values(), key=lambda x: x["slug"]), open("full_list.json", "w"), indent=1)
import collections; print(len(seen), collections.Counter(x["status"] for x in seen.values()), collections.Counter(x["grade"] for x in seen.values()))
