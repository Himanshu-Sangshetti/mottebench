# Run matrix (fixed 14 Nov 2026, before main data)

Runs go in tiers. Every model finishes a tier before starting the next, so a stop at any point leaves a complete,
analysable set. `runner/status.py` is the monitor.

## Models
| Group | Models | Access | Role |
|---|---|---|---|
| Frontier, headline | Claude Opus 5.5, Sonnet 5.5, Haiku 5.5 | Claude Code through the sanitizing recorder (forwarded request = our system prompt + our turns only) | headline, H4, causal swap |
| Frontier, headline | GPT-6.1-Sol, DeepSeek V4.1 Flash, GLM-5.3 Flash (Gemini Pro if available) | OpenRouter API, same messages, temperature 0.7 | headline, H4, causal swap |
| Open, local | Qwen3-8B, Llama 3.1 8B, GLM-4 9B, Mistral 7B | Ollama | all tiers, all items |
| Sensitivity | GPT-6-Astra, GPT-6.1-Sol | Codex CLI (agent harness, disclosed) | harness effect only, excluded from H4 |

## Tiers
| Tier | Items | Conditions | Answers |
|---|---|---|---|
| 1 headline | core 100 | A, B, A_F, B_F | H1, H2, format check |
| 2 mechanism | core 100 | P, C, D, EK_WEAK, EK_STRONG (EK on WEAK items) | H3, H5, placebo, fix |
| 3 scale | ext 200 | A, B | tighter CIs, domain breakdown |
| 4 robustness | 30-item subset | A x 3 repeats; A_Q1, A_Q2 (reworded user question) | noise floor, question-wording sensitivity |
| 5 exploratory | core subset | E_WEAK, E_STRONG (generic swap), F, G | reported as exploratory |

Local models run tiers 1-5 on all items. Sensitivity runs: tier 1 only.

## Monitoring and stop rules
- `python3 runner/status.py --watch 60`: per run, done per condition, failures, speed, idle time, forced-label compliance, DO rate on WEAK items, recorder hygiene check.
- Before each model's main run: a 5-conversation dry run; read the full traces by hand (messages sent, swap text in place, reply parsed).
- Stop and fix if: the recorder check reports anything injected; failures exceed 5% of a run; forced-label compliance falls below 90%; a run is idle over 20 minutes with jobs left.
- API runs carry a hard spend cap (`--opts '{"max_usd": ...}'`); the runner stops itself when reached.
- Claude runs use `--deadline` so they stop before the usage window closes; they resume where they stopped.
- Every stop, fix and rerun is written to `plan/RUNLOG.md` with the date.
