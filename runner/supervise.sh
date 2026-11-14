#!/bin/bash
# Keep a run alive until it finishes. usage: runner/supervise.sh <run.py args...>
# - restarts run.py after a crash (resume skips finished conversations), up to 20 times
# - stops for good when run.py exits 0 (finished) or 3 (spend cap / usage limit / deadline); exit 4 = some failed, retried
# - keeps the Mac awake while running (caffeinate)
# - after every attempt, copies results/ and traces/ to a backup folder outside the repo
cd "$(dirname "$0")/.." || exit 1
BACKUP="${MB_BACKUP:-$HOME/mottebench_backup}"
LOG="results/supervise_$(date +%Y%m%d_%H%M%S).log"
mkdir -p results "$BACKUP"
for attempt in $(seq 1 20); do
  echo "$(date '+%F %T') attempt $attempt: run.py $*" | tee -a "$LOG"
  caffeinate -i python3 runner/run.py "$@" 2>&1 | tee -a "$LOG"
  code=${PIPESTATUS[0]}
  rsync -a results traces "$BACKUP/" 2>/dev/null
  echo "$(date '+%F %T') exit $code, backed up to $BACKUP" | tee -a "$LOG"
  [ "$code" = 0 ] && { echo "finished" | tee -a "$LOG"; exit 0; }
  [ "$code" = 2 ] && { echo "bad command line, not retrying" | tee -a "$LOG"; exit 2; }
  [ "$code" = 3 ] && { echo "stopped on purpose (limit/deadline); rerun the same command later to resume" | tee -a "$LOG"; exit 3; }
  sleep 60
done
echo "gave up after 20 crashes; see $LOG" | tee -a "$LOG"; exit 1
