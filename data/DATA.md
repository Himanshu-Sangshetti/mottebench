# The data (v2, 300 questions)

Each item = one everyday "should I...?" question + the official verdict on how strong the evidence is.
**The verdict is always copied from an official record** (no model is involved in any answer key).
**The question sentence is written by us** from that record's own fields, because no official body publishes user questions.
Every item stores the official fields it came from (`official`) and a link to the official page (`url`).

| Source | Who publishes it | What the verdict is | Items |
|---|---|---|---|
| USPSTF | US Preventive Services Task Force | the grade for one specific population on the recommendation page: I = weak; A/B = strong, helps; D = strong, does not help (C left out: a judgement call, not an evidence level) | 127 |
| Cochrane | Cochrane systematic reviews (via PubMed) | weak = every certainty statement in the review is low or very low; strong = a moderate/high-certainty result, read by hand, with the review's sentence stored word for word | 74 |
| What Works Clearinghouse | US Department of Education | the WWC effectiveness rating plus WWC's own extent-of-evidence rule (medium-to-large = 2+ studies and 350+ students): positive + large = strong, helps; no discernible effects + large = strong, does not help; potentially positive or mixed + small = weak | 99 |

Totals: 191 weak, 73 strong-helps, 36 strong-does-not-help. Core set 100 (balanced by source and verdict), extended 200.

## Files
| File | What it is |
|---|---|
| `QUESTIONS.md` | every question next to its official record, verdict, check result and link. Start here. |
| `items.csv` | the same as a spreadsheet |
| `items.jsonl` | the same, read by the runner |
| `CROSSCHECK.md`, `crosscheck.csv` | independent re-check of every key against the raw official data (all 300 ok) |
| `sources/uspstf/full_list.json` | every USPSTF topic from the official site search: status, year, grades |
| `sources/uspstf/pages/` | saved official recommendation pages |
| `sources/uspstf/populations.json` | the population / recommendation / grade table read from each page |
| `sources/uspstf/questions.json` | our question for each population row |
| `sources/cochrane/raw.json` | Cochrane abstracts from PubMed (**not in the repo**, copyright; `fetch.py` downloads them) |
| `sources/cochrane/questions.json` | our question for each selected review; for strong reviews also the direction and the review's own sentence |
| `sources/wwc/raw/` | the official WWC data export (used directly) |

## How items were chosen
- USPSTF: all current recommendations, one item per population row, except 5 rows that are not a personal decision (clinician abuse screening, food insecurity screening, two "preventive interventions by primary care" rows, child maltreatment interventions).
- Cochrane: everyday decisions only (not hospital, surgical technique, specialist or low-income-country programme reviews); reviews that would repeat or contradict a USPSTF item left out.
- WWC: programmes a family or student would choose (teacher training and school-management programmes left out); one outcome per programme; programmes rated differently on different outcomes left out.

## Not used (and why)
- 2025 Dietary Guidelines Advisory Committee report: grades could not be read reliably from the PDF (columns merged).
- The earlier model-drafted question set (v1): wording drifted from the records (e.g. dropped the population the rating applies to).

## Scripts (`build/`)
`build_items.py` builds `items.jsonl`; `crosscheck.py` re-verifies every key; `render.py` writes the readable files.
`sources/uspstf/full_list.py`, `parse_pages.py` and `sources/cochrane/fetch.py` re-download the official data.
