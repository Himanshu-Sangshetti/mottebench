"""For each topic in official_list.json: search the USPSTF site, accept only a result row whose title is EXACTLY the topic
title, and record that row's own link, grade and year. Writes official_check.json (one row per topic: link, grade on
the site, grade in our list, match yes/no). No fuzzy matching: a topic with no exact title match is reported, not guessed."""
import json, re, urllib.request, urllib.parse, html as H, time
L = json.load(open("official_list.json")); out = []
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
def cells(tr): return [H.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
for x in L:
    found = None
    for term in [x["topic"].split(":")[0], " ".join(x["topic"].split()[:3])]:
        u = "https://www.uspreventiveservicestaskforce.org/uspstf/topic_search_results?searchterm=" + urllib.parse.quote(term)
        page = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8", "ignore")
        for tr in ROW.findall(page):
            m = re.search(r"href='(/uspstf/recommendation/[a-z0-9-]+)'", tr); c = cells(tr)
            if m and len(c) >= 6 and c[3] == x["topic"]:
                found = dict(url="https://www.uspreventiveservicestaskforce.org" + m.group(1), status=c[0], year_site=c[2], grade_site=c[5]); break
        if found: break
        time.sleep(0.4)
    r = dict(topic=x["topic"], grade_ours=x["grade"], year_ours=x["year"], **(found or dict(url=None)))
    r["check"] = "no exact title match on site" if not found else ("ok" if found["grade_site"] == x["grade"] and found["year_site"] == x["year"] else "MISMATCH")
    out.append(r); print(r["check"], "|", x["topic"], "|", (found or {}).get("grade_site"), flush=True)
json.dump(out, open("official_check.json", "w"), indent=1)
