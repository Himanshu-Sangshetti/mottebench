# How the final answer treats the planted evidence statement (exploratory)

Judge: Nemotron 3 Ultra (sees only the planted statement and the final reply). % of labelled conversations; keyword = rule-based count of explicit corrections (lower bound).

| Model | Planted | n | Accepts | Says stronger | Says weaker | Retracts source | No mention | Keyword correction |
|---|---|---|---|---|---|---|---|---|
| Claude Sonnet 5.5 | weak | 52 | 33% | 13% | 0% | 33% | 21% | 56% |
| Claude Sonnet 5.5 | strong | 52 | 0% | 0% | 88% | 12% | 0% | 100% |
| Claude Haiku 5.5 | weak | 0 | – | – | – | – | – | 62% |
| Claude Haiku 5.5 | strong | 0 | – | – | – | – | – | 100% |
| GPT-6.1-Sol | weak | 0 | – | – | – | – | – | 56% |
| GPT-6.1-Sol | strong | 0 | – | – | – | – | – | 100% |
| DeepSeek V4 Pro | weak | 0 | – | – | – | – | – | 0% |
| DeepSeek V4 Pro | strong | 0 | – | – | – | – | – | 9% |
| Llama 3.1 8B (local) | weak | 0 | – | – | – | – | – | 2% |
| Llama 3.1 8B (local) | strong | 0 | – | – | – | – | – | 0% |
