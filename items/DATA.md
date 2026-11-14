# What every data file is

Three kinds of file: **official** (downloaded unchanged from the source body), **made by a model** (a local model's output,
checked by the rules in `build/build_items.py` and by hand), and **final** (what the benchmark uses).

## Final
| File | What it is |
|---|---|
| `QUESTIONS.md` | every question, readable: question, official verdict, source link. Start here. |
| `items.csv` | the same as a spreadsheet |
| `items.jsonl` | the same, one JSON object per line; the file the runner reads |

## Preventive health: USPSTF (`sources/uspstf/`)
| File | Kind | What it is |
|---|---|---|
| `official_list.json` | official | USPSTF topics with their grade (A, B, C, D, I) and year |
| `pilot_questions.json` | written by us | user questions for 36 topics, used in the pilot (flagged in items) |
| `added_questions.json` | written by us | user questions for 20 more topics |

Verdict rule: grade I = weak; A or B = strong, helps; D = strong, does not help; C is left out (a judgement call, not an evidence level).

## Treatments: Cochrane (`sources/cochrane/`)
| File | Kind | What it is |
|---|---|---|
| `raw.json` | official, **not in the repo** (copyright) | Cochrane review abstracts 2019-2026 from PubMed; `fetch.py` downloads them |
| `labeled.jsonl` | made by a model (Qwen3-8B) | per review: is it an everyday decision, main outcome, direction, GRADE certainty, a user question |
| `cross.jsonl` | made by a second model (GLM-4 9B), independently | main outcome, direction, certainty for the same reviews |

Verdict rule: kept only if both models read the same certainty band from the abstract (and the same direction for strong items);
45 of 203 dropped for disagreeing. Low/very low = weak; moderate/high = strong.

## Nutrition: 2025 Dietary Guidelines Advisory Committee (`sources/nesr/`)
| File | Kind | What it is |
|---|---|---|
| `dgac2025_report.pdf`, `report.txt` | official | the Scientific Report, and its text |
| `graded_paras.json` | extracted from official | every conclusion paragraph with the grade the Committee gave it |
| `drafted.jsonl` | made by a model | a user question for each conclusion |
| `cross.jsonl` | made by a second model | does the conclusion support doing the action? |

Verdict rule: limited / grade not assignable = weak; strong or moderate = strong, direction confirmed by the second model.

## Education: What Works Clearinghouse (`sources/wwc/`)
| File | Kind | What it is |
|---|---|---|
| `wwc.zip`, `raw/*.csv`, `raw/ReadMe.txt` | official | the full WWC findings export (US Department of Education) |
| `interventions.json` | extracted from official | one row per programme and outcome: rating and number of students |
| `drafted.jsonl` | made by a model | a user question for each |

Verdict rule: Positive Effects with 350+ students = strong, helps; No Discernible Effects with 350+ = strong, does not help;
Potentially Positive or Mixed with fewer than 350 = weak; everything else left out.

## Scripts (`build/`)
`draft_q.py` writes the questions, `cross_label.py` runs the second labeller, `build_items.py` applies the verdict rules,
removes duplicates, balances domains and splits the sets, `render.py` writes `QUESTIONS.md` and `items.csv`.
