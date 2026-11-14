# How MotteBench compares with existing benchmarks

Facts below are taken from each paper or repository (arXiv ids given). Where MotteBench is weaker, it says so.

## What existing honesty / consistency benchmarks measure

| Benchmark | Items | Turns | What triggers the behaviour | Answer key | Grading |
|---|---|---|---|---|---|
| MASK (2503.03750) | 1,000 public + 500 private, human-written | 1 exchange per prompt | pressure prompt to lie | model's own elicited belief + ground truth | LLM judge, 86.4% agreement with humans |
| SYCON-Bench (2505.23840) | 100 debate + 200 ethical + 200 false-presupposition | multi-turn | sustained user disagreement | stance / facts | Turn-of-Flip, Number-of-Flips |
| FlipFlop (2311.08596) | classification tasks | 2 | "Are you sure?" | task labels | flip rate (~46% of answers flip) |
| MedPRESS (2608.02520) | 600 medical dialogues | 5 | escalating patient pressure | medical answers | flip patterns |
| HealthBench (2505.08775) | 5,000 conversations, 48,562 rubric criteria by 262 physicians | multi-turn (fixed history) | none (realistic conversations) | physician rubrics per conversation | model grader vs rubric; only the final reply is graded |
| MedEvidence (2505.22787) | 100 systematic reviews | 1 | none (studies given) | review conclusions | finds models overconfident, no skepticism toward low-quality evidence |
| AA-Omniscience (2511.13029) | 6,000 questions, 42 topics | 1 | none | facts | penalises confident wrong answers |
| **MotteBench** | 300 (x up to 9 conditions x models) | 3 live turns (model writes every turn); 6-turn natural variant | **nothing: a neutral evidence question** | **official evidence-strength ratings (USPSTF grades, Cochrane GRADE certainty, WWC ratings)** | 2 cross-lab LLM judges + tiebreak, validated on 300 human gold labels |

## What is new here
1. **No pressure.** Every multi-turn benchmark above makes the model change position by pushing it. Here nobody pushes. The model is asked a neutral information question and later a decision question. The inconsistency, if present, is the model's own.
2. **An evidence-strength key.** The other benchmarks key on facts (true/false, correct answer). Here the key is *how strong the evidence is*, set by official bodies, so we can tell a calibrated admission ("evidence is weak", on an item officially rated weak) from an over- or under-statement.
3. **Decision vs stated evidence, measured causally.** The swap condition replaces the model's evidence statement with a fixed weak or strong one and checks whether the decision moves. None of the papers above tests whether the decision depends on the model's own evidence statement.
4. **Link to reported honesty scores.** The pre-registered H4 asks whether the honesty benchmarks labs publish in system cards (MASK, AA-Omniscience) predict this behaviour.
5. **Harness audit.** Requests to each model are recorded at the network boundary; we found and removed hidden context added by agent CLIs. Most benchmarks do not report what extra context their access path adds.

## Where existing benchmarks are stronger (and what we do about it)
| Gap | Them | Us | Mitigation |
|---|---|---|---|
| Scale | 1,000-6,000 items | 300 items | Items x up to 9 conditions per model, 5 phrasings of each follow-up; CIs by cluster bootstrap; power checked in plan |
| Item authorship | human-written (MASK), physician-written (HealthBench) | questions written by the authors from each official record's own fields (WWC by fixed template) | answer key always copied from the official record; every key re-verified by an independent script against raw official data (300/300) |
| Expert annotation | 262 physicians (HealthBench) | 1 author gold (300) + 1 second annotator (50) | report human-human and judge-human agreement; rubric has worked examples |
| Release | Hugging Face dataset, private hold-out (MASK) | GitHub only | dataset card + HF release planned after the sprint; hold-out not possible at this size |
| Domain breadth | many | 3 sources: preventive health, treatments, education | stated as scope |

## What a complete benchmark release usually includes, and our status
| Part | Typical (MASK / SYCON / simple-evals) | MotteBench |
|---|---|---|
| Paper with method + results | yes | sprint report (in progress) |
| Dataset with per-item provenance | yes | items.jsonl with source link per item |
| Evaluation code + one command to run | yes | runner/supervise.sh, README |
| Judge validation against humans | MASK: 86.4% | planned: 300 gold + 50 second annotator, kappa |
| Raw model outputs | rarely | every request and raw response kept (traces/) |
| Pre-registration | rarely | plan/PLAN.md committed before data, dated amendments |
| License + citation | yes | to add at release |
