# How the final answer treats the planted evidence statement (exploratory)

Judge: Nemotron 3 Ultra (sees only the planted statement and the final reply). % of labelled conversations; keyword = rule-based count of explicit corrections (lower bound).

| Model | Planted | n | Accepts | Says stronger | Says weaker | Retracts source | No mention | Keyword correction |
|---|---|---|---|---|---|---|---|---|
| Claude Sonnet 5.5 | weak | 64 | 27% | 17% | 0% | 38% | 19% | 56% |
| Claude Sonnet 5.5 | strong | 64 | 0% | 0% | 84% | 16% | 0% | 100% |
| Claude Haiku 5.5 | weak | 64 | 27% | 20% | 0% | 39% | 14% | 62% |
| Claude Haiku 5.5 | strong | 64 | 0% | 0% | 86% | 14% | 0% | 100% |
| GPT-6.1-Sol | weak | 64 | 45% | 42% | 0% | 11% | 2% | 56% |
| GPT-6.1-Sol | strong | 64 | 0% | 0% | 97% | 3% | 0% | 100% |
| DeepSeek V4 Pro | weak | 64 | 94% | 3% | 0% | 0% | 3% | 0% |
| DeepSeek V4 Pro | strong | 64 | 62% | 0% | 9% | 19% | 9% | 9% |
| Llama 3.1 8B (local) | weak | 64 | 67% | 0% | 0% | 2% | 31% | 2% |
| Llama 3.1 8B (local) | strong | 64 | 61% | 0% | 5% | 2% | 33% | 0% |
