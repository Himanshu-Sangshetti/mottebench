#!/bin/bash
# Autopilot: drives the remaining pipeline without supervision. Every step is resumable; safe to restart.
# Log: results/autopilot.log. Stops spending at the OpenRouter cap (runner) and never exceeds the key's own limit.
cd "$(dirname "$0")/.." || exit 1
LOG=results/autopilot.log; say(){ echo "$(date '+%F %T') $*" | tee -a $LOG; }
OR='{"max_usd": 9.3}'
running(){ pgrep -f "run.py .*--tag $1( |$)" >/dev/null; }
MAIN="results/main__claude__sonnet.jsonl results/main__or__anthropic_claude-haiku-5.5.jsonl results/main__or__deepseek_deepseek-v4-pro.jsonl results/main__or__openai_gpt-6.1-sol.jsonl"
LOCAL="results/main__local__qwen3_8b.jsonl results/main__local__llama3.1_8b.jsonl"

say "autopilot start"
# 1. wait for the OpenRouter main runs
while running main__or__anthropic_claude-haiku-5.5 || running main__or__deepseek_deepseek-v4-pro || running main__or__openai_gpt-6.1-sol; do sleep 60; done
say "OpenRouter main runs finished"

# 2. robustness: reworded questions (A_Q1, A_Q2) and 3 repeats of A on the 30-item subset (cheap models first, GPT last)
for M in anthropic/claude-haiku-5.5 deepseek/deepseek-v4-pro openai/gpt-6.1-sol; do
  T="main__or__$(echo $M | tr '/:' '__')"
  runner/supervise.sh --provider openrouter --model $M --conds A_Q1,A_Q2 --items q30 --workers 10 --tag $T --opts "$OR" >/dev/null 2>&1
  runner/supervise.sh --provider openrouter --model $M --conds A --reps 3 --items q30 --workers 10 --tag $T --opts "$OR" >/dev/null 2>&1
  say "robustness done for $M"
done

# 3. Opus judge on GPT, DeepSeek and local conversations (Claude plan), in the background, looping
( while true; do python3 grading/judge.py $MAIN $LOCAL --judges opus --workers 3 --max-usd 9.3 >> results/judge_opus.log 2>&1; sleep 300; done ) &

# 4. local models (free, one at a time for memory): core A,B,C + weak A_F, EK
for M in qwen3:8b llama3.1:8b; do
  T="main__local__$(echo $M | tr ':' '_')"
  runner/supervise.sh --provider ollama --model $M --conds A,B,C --items core --workers 1 --tag $T >/dev/null 2>&1
  runner/supervise.sh --provider ollama --model $M --conds A_F,EK_WEAK,EK_STRONG --items weak_core --workers 1 --tag $T >/dev/null 2>&1
  say "local model done: $M"
done &

# 5. Sonnet: retry until complete (stops cleanly on a Claude usage limit; resumes after reset)
( while true; do
    runner/supervise.sh --provider claude --model sonnet --conds A,B,C --items core --workers 6 --tag main__claude__sonnet >/dev/null 2>&1
    runner/supervise.sh --provider claude --model sonnet --conds A_F,EK_WEAK,EK_STRONG --items weak_core --workers 6 --tag main__claude__sonnet >/dev/null 2>&1; c=$?
    runner/supervise.sh --provider claude --model sonnet --conds A_Q1,A_Q2 --items q30 --workers 6 --tag main__claude__sonnet >/dev/null 2>&1
    [ $c = 0 ] && { say "Sonnet complete"; break; }
    say "Sonnet paused (usage limit?), retry in 30 min"; sleep 1800
  done ) &

# 6. every 20 min: aggregate, Gemini tiebreaks on disagreements, calibration set, provisional analysis
while true; do
  python3 grading/aggregate.py $MAIN $LOCAL >> $LOG 2>&1
  if [ -s grading/needs_tiebreak.txt ]; then
    python3 grading/judge.py $MAIN $LOCAL --judges gemini,nemotron,astra --only grading/needs_tiebreak.txt --workers 3 --max-usd 9.3 >> results/judge_tiebreak.log 2>&1
    python3 grading/aggregate.py $MAIN $LOCAL >> $LOG 2>&1
  fi
  [ -s grading/calibration_set.txt ] || python3 grading/make_calibration.py >> $LOG 2>&1
  python3 analysis/analyze.py > /dev/null 2>> $LOG && say "analysis refreshed: $(head -c 0 analysis/RESULTS.md)$(grep -c '^|' analysis/RESULTS.md) table rows"
  git add -A data grading/labels grading/final_labels.jsonl grading/calibration_set.txt analysis plan runner grading/*.py 2>/dev/null
  git commit -q -m "Autopilot: labels and provisional analysis $(date '+%H:%M')" 2>/dev/null && git push -q 2>/dev/null
  sleep 1200
done
