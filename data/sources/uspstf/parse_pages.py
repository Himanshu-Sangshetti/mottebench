"""Read the official recommendation table (Population | Recommendation | Grade) from each saved USPSTF page."""
import re, html, json, glob, os
out = []
for fn in sorted(glob.glob("pages/*.html")):
    h = open(fn, encoding="utf-8", errors="ignore").read()
    t = re.search(r"<table[^>]*>.*?Population.*?Recommendation.*?Grade.*?</table>", h, re.S)
    if not t: out.append(dict(page=os.path.basename(fn), error="no table")); continue
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t.group(0), re.S)[1:]:
        c = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(c) >= 3 and c[-1] in ("A", "B", "C", "D", "I"):
            out.append(dict(page=os.path.basename(fn)[:-5], population=c[0], recommendation=c[1].split(" Literature scans")[0][:600], grade=c[-1]))
json.dump(out, open("populations.json", "w"), indent=1)
import collections
print(len(out), "rows;", collections.Counter(r.get("grade", "ERR") for r in out), "; pages with >1 row:", sum(1 for v in collections.Counter(r["page"] for r in out).values() if v > 1))
