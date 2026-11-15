#!/bin/bash
# Rebuild every result and the paper from the raw result files and judge labels.
# usage: report/build.sh   (needs python3 + matplotlib, tectonic)
set -e; cd "$(dirname "$0")/.."
F="results/main__claude__sonnet.jsonl results/main__or__anthropic_claude-haiku-5.5.jsonl results/main__or__openai_gpt-6.1-sol.jsonl results/main__or__deepseek_deepseek-v4-pro.jsonl"
python3 grading/aggregate.py $F
python3 analysis/judgefree.py > /dev/null
python3 analysis/analyze.py > /dev/null
python3 analysis/extra.py > /dev/null
python3 analysis/correction.py report > /dev/null
python3 analysis/paper_figs.py
python3 analysis/paper_tables.py
(cd report/paper && tectonic -X compile main.tex)
cp report/paper/main.pdf report/MotteBench.pdf
echo "built report/MotteBench.pdf"
