"""Write data/QUESTIONS.md and data/items.csv (readable copies of data/items.jsonl). Run after build_items.py and crosscheck.py."""
import json, csv, os, collections
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
L = [json.loads(l) for l in open(f"{D}/items.jsonl")]
cc = {r["item_id"]: r for r in csv.DictReader(open(f"{D}/crosscheck.csv"))} if os.path.exists(f"{D}/crosscheck.csv") else {}
EV = {"WEAK": "weak", "STRONG_FOR": "strong, helps", "STRONG_AGAINST": "strong, does not help"}
def rec(it):
    o = it["official"]
    if it["source_name"] == "USPSTF": return f"{o['topic']}. Population: {o['population']}. Grade {o['grade']} ({o['year']})"
    if it["source_name"] == "Cochrane": return f"{o['title']} ({o['year']}). " + (f"Result: \"{o['result_sentence']}\"" if o.get("result_sentence") else f"Certainty: {', '.join(o['certainty_statements'])}")
    return f"{o['intervention']}. Students: {o['protocol']}. Outcome: {o['outcome_domain']}. {o['rating']}, {o['studies_meeting_standards']} studies, {o['students']} students"
with open(f"{D}/QUESTIONS.md", "w") as f:
    c = collections.Counter((it["source_name"], it["key_class"]) for it in L)
    f.write(f"# The questions ({len(L)})\n\nThe question is written by us; the verdict is the official body's grade, copied from the linked record. "
            "Check = result of `build/crosscheck.py` against the raw official data. Spreadsheet: `items.csv`.\n\n| Source | weak | strong, helps | strong, does not help |\n|---|---|---|---|\n")
    for s in ["USPSTF", "Cochrane", "What Works Clearinghouse"]: f.write(f"| {s} | {c[(s,'WEAK')]} | {c[(s,'STRONG_FOR')]} | {c[(s,'STRONG_AGAINST')]} |\n")
    for s in ["USPSTF", "Cochrane", "What Works Clearinghouse"]:
        f.write(f"\n## {s}\n\n| id | Question | Official record | Verdict | Check | Link |\n|---|---|---|---|---|---|\n")
        for it in sorted([x for x in L if x["source_name"] == s], key=lambda x: (x["key_class"], x["question"])):
            f.write(f"| {it['item_id']} | {it['question'].replace('|','/')} | {rec(it).replace('|','/')} | {EV[it['key_class']]} | {cc.get(it['item_id'],{}).get('status','-')} | [official]({it['url']}) |\n")
with open(f"{D}/items.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["item_id", "source", "verdict", "question", "official_record", "url", "set", "published", "check"])
    for it in L: w.writerow([it["item_id"], it["source_name"], EV[it["key_class"]], it["question"], rec(it), it["url"], it["split"], it.get("published") or "", cc.get(it["item_id"], {}).get("status", "")])
print("wrote QUESTIONS.md and items.csv:", len(L))
