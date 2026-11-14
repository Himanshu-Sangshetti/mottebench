"""Write human-readable copies of items/items.jsonl:
  items/QUESTIONS.md  every question with its official verdict and source link, grouped by domain and evidence level
  items/items.csv     the same as a spreadsheet
Run after build_items.py. The .jsonl stays the file the runner reads; these two are generated from it."""
import json, csv, collections, os
H = os.path.dirname(os.path.abspath(__file__)); IT = os.path.join(H, "..")
L = [json.loads(l) for l in open(f"{IT}/items.jsonl")]
DOM = {"health_prevention": "Preventive health (USPSTF)", "health_treatment": "Treatments (Cochrane)",
       "nutrition": "Nutrition (2025 Dietary Guidelines Advisory Committee)", "education": "Education (What Works Clearinghouse)"}
EV = {"WEAK": "Weak evidence", "STRONG_FOR": "Strong evidence it helps", "STRONG_AGAINST": "Strong evidence it does not help"}
SPLIT = {"core": "core 100", "ext": "extended", "heldout": "held out"}

def src(it):
    s = it["source"]; nm = s.get("topic") or s.get("intervention") or s.get("title") or s["name"]
    return f"[{nm}]({s['url']})" if s.get("url") else nm

with open(f"{IT}/QUESTIONS.md", "w") as f:
    c = collections.Counter((it["domain"], it["key_class"]) for it in L)
    f.write(f"# The questions ({len(L)})\n\nGenerated from `items.jsonl` by `build/render.py`. Each question is a real everyday decision. "
            "The verdict column is set by the official body named, never by us or by a model. Spreadsheet version: `items.csv`.\n\n")
    f.write("| Domain | Weak | Strong, helps | Strong, does not help |\n|---|---|---|---|\n")
    for d in DOM: f.write(f"| {DOM[d]} | {c[(d,'WEAK')]} | {c[(d,'STRONG_FOR')]} | {c[(d,'STRONG_AGAINST')]} |\n")
    for d in DOM:
        f.write(f"\n## {DOM[d]}\n")
        for k in EV:
            rows = sorted([it for it in L if it["domain"] == d and it["key_class"] == k], key=lambda x: x["question"])
            if not rows: continue
            f.write(f"\n### {EV[k]} ({len(rows)})\n\n| # | Question | Official verdict | Source | Set |\n|---|---|---|---|---|\n")
            for it in rows:
                q = it["question"].replace("|", "/"); det = it["key_detail"].replace("|", "/")
                f.write(f"| {it['item_id']} | {q} | {det} | {src(it)} | {SPLIT.get(it['split'], it['split'])}{', pilot' if it.get('pilot') else ''} |\n")

with open(f"{IT}/items.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["item_id", "domain", "evidence_level", "question", "official_verdict", "source_name", "source_item", "source_url", "set", "used_in_pilot"])
    for it in sorted(L, key=lambda x: (x["domain"], x["key_class"], x["question"])):
        s = it["source"]
        w.writerow([it["item_id"], DOM[it["domain"]], EV[it["key_class"]], it["question"], it["key_detail"], s["name"],
                    s.get("topic") or s.get("intervention") or s.get("title") or "", s.get("url", ""), SPLIT.get(it["split"], it["split"]), "yes" if it.get("pilot") else "no"])
print("wrote QUESTIONS.md and items.csv for", len(L), "items")
