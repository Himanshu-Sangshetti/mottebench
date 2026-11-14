# Run matrix (fixed 14 Nov 2026, before main data)

Runs go in tiers. Every model finishes a tier before starting the next, so a stop at any point leaves a complete,
analysable set. `runner/status.py` is the monitor.

## Models
| Group | Models | Access | Role |
|---|---|---|---|
| Frontier, headline | Claude Opus 5.5, Sonnet 5.5, Haiku 5.5 | Claude Code through the sanitizing recorder (forwarded request = our system prompt + our turns only) | headline, H4, causal swap |
| Frontier, headline | GPT-6.1-Sol, DeepSeek V4.1 Flash, GLM-5.3 Flash (Gemini Pro if available) | OpenRouter API, same messages, temperature 0.7 | headline, H4, causal swap |
| Open, local | Qwen3-8B, Llama 3.1 8B, GLM-4 9B | Ollama | small-model contrast (appendix); also pipeline dry runs |
| Sensitivity | GPT-6-Astra, GPT-6.1-Sol | Codex CLI (agent harness, disclosed) | harness effect only, excluded from H4 |

## Tiers
| Tier | Items | Conditions | Answers |
|---|---|---|---|
| 1 headline | core 100 | A, B, A_F, B_F | H1, H2, format check |
| 2 mechanism | core 100 | P, C, D, EK_WEAK, EK_STRONG (EK on WEAK items) | H3, H5, placebo, fix |
| 3 scale | ext 200 | A, B | tighter CIs, domain breakdown |
| 4 robustness | 30-item subset | A x 3 repeats; A_Q1, A_Q2 (reworded user question) | noise floor, question-wording sensitivity |
| 5 exploratory | core subset | E_WEAK, E_STRONG (generic swap), F, G | reported as exploratory |

Frontier models run tiers 1-4 (5 as budget and usage allow). Local models run tiers 1-2. Sensitivity runs: tier 1 only.
Thinking/reasoning: every model runs at its provider's default setting (none is raised, lowered or turned off); the setting is recorded per call.

## Crash safety
- `runner/supervise.sh <run.py args>` runs a job: restarts after a crash (up to 20 times), stops for good on finish,
  spend cap, usage limit or deadline, keeps the Mac awake, and copies results/ and traces/ to a backup folder after every attempt.
- A conversation is saved only when complete: trace written to a temp file then renamed; result line flushed to disk.
- A half-written line from a crash is skipped on resume and that conversation reruns. Tested 14 Nov by killing a run mid-way.
- Failed conversations go to results/<run>.fails.jsonl and are retried on the next attempt.

## Monitoring and stop rules
- `python3 runner/status.py --watch 60`: per run, done per condition, failures, speed, idle time, forced-label compliance, DO rate on WEAK items, recorder hygiene check.
- Before each model's main run: a 5-conversation dry run; read the full traces by hand (messages sent, swap text in place, reply parsed).
- Stop and fix if: the recorder check reports anything injected; failures exceed 5% of a run; forced-label compliance falls below 90%; a run is idle over 20 minutes with jobs left.
- API runs carry a hard spend cap (`--opts '{"max_usd": ...}'`); the runner stops itself when reached.
- Claude runs use `--deadline` so they stop before the usage window closes; they resume where they stopped.
- Every stop, fix and rerun is written to `plan/RUNLOG.md` with the date.
