# Decision results (no judge needed)

Share of conversations whose final answer starts with DO IT. 95% cluster-bootstrap CIs over items.

| Model | Weak, B (no follow-up) | Weak, A (evidence asked) | Weak, C (pushback) | Strong-for, B | Strong-against, B | H2: A−B on weak | Swap: told weak | told strong | **H5 swap effect** | swap text rejected (weak/strong of n) |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude Sonnet 5.5 | 30% [19, 41] | 19% [9, 28] | 16% [8, 25] | 71% [50, 88] | 0% [0, 0] | -11 pts [-20, -3] | 11% [5, 19] | 23% [14, 34] | 12 pts [3, 22] | 0/0 of 64 |
| Llama 3.1 8B (local) | 23% [14, 34] | 8% [2, 14] | 5% [0, 11] | 38% [21, 58] | 0% [0, 0] | -16 pts [-25, -6] | 0% [0, 0] | 54% [41, 66] | 54 pts [41, 66] | 0/0 of 61 |
| Claude Haiku 5.5 | 31% [20, 42] | 22% [12, 33] | 17% [8, 27] | 71% [50, 88] | 0% [0, 0] | -9 pts [-19, 0] | 22% [12, 33] | 22% [12, 33] | 0 pts [-6, 6] | 0/0 of 64 |
| DeepSeek V4 Pro | 28% [17, 41] | 34% [23, 45] | 22% [12, 33] | 62% [42, 79] | 0% [0, 0] | 6 pts [-2, 14] | 0% [0, 0] | 41% [30, 53] | 41 pts [30, 53] | 0/1 of 64 |
| GPT-6.1-Sol | 23% [14, 34] | 25% [16, 36] | 22% [12, 33] | 75% [54, 92] | 0% [0, 0] | 2 pts [-3, 8] | 17% [9, 28] | 20% [11, 31] | 3 pts [0, 8] | 0/0 of 64 |

Pre-registered H5 thresholds: swap effect < 20 points = decision ignores the stated evidence; >= 40 = follows it.
