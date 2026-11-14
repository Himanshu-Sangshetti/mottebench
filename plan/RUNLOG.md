RUNLOG started 14 Nov 2026.
- 14 Nov: item ids changed to stable hashes (rebuild had renumbered items; found via trace viewer showing a stale key). Result rows now store their own key. Item count after filters: 285 (plan said ~400); topping up to 300 from the same sources.
- 14 Nov 18:20: DeepSeek V4 Pro host changed DeepInfra -> StreamLake (fp8, with Baidu fp8 as fixed backup) before main runs, for cost (trial: $0.007/conv on DeepInfra). Both full fp8; logged per call.
