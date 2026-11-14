RUNLOG started 14 Nov 2026.
- 14 Nov: item ids changed to stable hashes (rebuild had renumbered items; found via trace viewer showing a stale key). Result rows now store their own key. Item count after filters: 285 (plan said ~400); topping up to 300 from the same sources.
- 14 Nov 18:20: DeepSeek V4 Pro host changed DeepInfra -> StreamLake (fp8, with Baidu fp8 as fixed backup) before main runs, for cost (trial: $0.007/conv on DeepInfra). Both full fp8; logged per call.
- 14 Nov 18:22: concurrency bug: the shared spend ledger (one JSON file) was corrupted by parallel writers; affected conversations failed after the reply was paid for (~80 conversations, < $0.30). Fixed: append-only ledger with an exclusive lock; cap checked before each call so a paid reply is never discarded. Runs restarted (resume).
- 14 Nov 18:40: Codex (GPT-6-Astra judge) hit the ChatGPT plan limit (resets 23:23); Astra judging paused until then. Opus judges GPT and DeepSeek conversations meanwhile. Local models: llama3.1:8b full matrix; qwen3:8b A,B on weak core only (time: default thinking ~1 min/conversation).
- 14 Nov 18:47: GPT-6.1-Sol robustness (_Q, repeats) skipped for budget (~$1.6); Haiku and DeepSeek robustness run. Claude plan: Opus judge paused at 17% of 5h window, resumes 23:45.
- 14 Nov 20:05: llama3.1:8b sped up: 3 parallel workers, num_ctx 8192 (conversations ~3k tokens; no effect on outputs).
- 14 Nov 20:38: all runs and judges stopped by owner request (owner travelling). Resume: Llama stage 2, Nemotron/Astra/Opus judging, Gemini tiebreaks.
