#!/usr/bin/env bash
set -euo pipefail

: "${SCANNER:?SCANNER is required}"
: "${VIDEO_LIST:?VIDEO_LIST is required}"
: "${OUTPUT_DIR:?OUTPUT_DIR is required}"
: "${REMOTE_PREFIX:?REMOTE_PREFIX is required}"
: "${LOCAL_PREFIX:?LOCAL_PREFIX is required}"
: "${TRASH_PREFIX:?TRASH_PREFIX is required}"
: "${MONTHS:?MONTHS is required, for example: 202401 202402}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTHONPATH_EXTRA="${PYTHONPATH_EXTRA:-}"
WORKERS="${WORKERS:-4}"
SAMPLES="${SAMPLES:-6}"
USE_VISION_CONFIRM="${USE_VISION_CONFIRM:-1}"
PROGRESS_LOG="${PROGRESS_LOG:-$OUTPUT_DIR/full-cleanup-progress.tsv}"
MOUNT_CHECK_DIR="${MOUNT_CHECK_DIR:-$LOCAL_PREFIX}"
VISION_DETECTOR="${VISION_DETECTOR:-}"
MOVE_DRY_RUN="${MOVE_DRY_RUN:-1}"
SOURCE_ROOT="${SOURCE_ROOT:-}"

export PYTHONPATH="${PYTHONPATH_EXTRA}${PYTHONPATH_EXTRA:+:}${PYTHONPATH:-}"

if [ ! -d "$MOUNT_CHECK_DIR" ]; then
  echo "ERROR: expected mounted directory missing at $MOUNT_CHECK_DIR" >&2
  exit 2
fi

mkdir -p "$OUTPUT_DIR"
printf "timestamp\tmonth\tphase\tkeep\tempty\terror\tmoved\n" > "$PROGRESS_LOG"

for month in $MONTHS; do
  out="$OUTPUT_DIR/scan-full-$month.csv"
  echo "[$(date '+%F %T')] scan_start $month"

  args=(
    "$SCANNER"
    --list "$VIDEO_LIST"
    --out "$out"
    --month "$month"
    --workers "$WORKERS"
    --samples "$SAMPLES"
    --resume
    --remote-prefix "$REMOTE_PREFIX"
    --local-prefix "$LOCAL_PREFIX"
    --trash-prefix "$TRASH_PREFIX"
  )

  if [ "$USE_VISION_CONFIRM" = "1" ]; then
    args+=(--vision-confirm)
  fi

  if [ -n "$VISION_DETECTOR" ]; then
    args+=(--vision-detector "$VISION_DETECTOR")
  fi

  "$PYTHON_BIN" "${args[@]}"

  summary="$("$PYTHON_BIN" - "$out" <<'PY'
import csv, sys
counts = {"keep": 0, "empty_candidate": 0, "error": 0}
with open(sys.argv[1], encoding="utf-8", newline="") as fh:
    for row in csv.DictReader(fh):
        counts[row["decision"]] = counts.get(row["decision"], 0) + 1
print(counts.get("keep", 0), counts.get("empty_candidate", 0), counts.get("error", 0))
PY
)"
  read -r keep empty error <<<"$summary"
  printf "%s\t%s\tscanned\t%s\t%s\t%s\t0\n" "$(date '+%F %T')" "$month" "$keep" "$empty" "$error" >> "$PROGRESS_LOG"

  echo "[$(date '+%F %T')] move_start $month empty=$empty"
  move_log="$OUTPUT_DIR/move-full-$month.log"
  move_args=(
    "$SCANNER"
    --out "$out" \
    --move-empty \
    --move-via local \
    --remote-prefix "$REMOTE_PREFIX" \
    --local-prefix "$LOCAL_PREFIX" \
    --trash-prefix "$TRASH_PREFIX" \
  )
  if [ "$MOVE_DRY_RUN" = "1" ]; then
    move_args+=(--dry-run)
  fi
  if [ -n "$SOURCE_ROOT" ]; then
    move_args+=(--source-root "$SOURCE_ROOT")
  fi

  "$PYTHON_BIN" "${move_args[@]}" > "$move_log"

  moved="$(awk -F= '/^move_count=/{print $2}' "$move_log" | awk '{print $1}')"
  moved="${moved:-0}"
  phase="moved"
  if [ "$MOVE_DRY_RUN" = "1" ]; then
    phase="dry_run"
  fi
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$(date '+%F %T')" "$month" "$phase" "$keep" "$empty" "$error" "$moved" >> "$PROGRESS_LOG"
  echo "[$(date '+%F %T')] month_done $month keep=$keep empty=$empty error=$error $phase=$moved"
done

echo "[$(date '+%F %T')] cleanup_done"
