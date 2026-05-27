#!/usr/bin/env bash
set -euo pipefail

: "${ROOT_DIR:?ROOT_DIR is required}"
: "${SCANNER:?SCANNER is required}"
: "${VIDEO_LIST:?VIDEO_LIST is required}"
: "${OUTPUT_DIR:?OUTPUT_DIR is required}"
: "${MOUNT_ROOT:?MOUNT_ROOT is required}"
: "${REMOTE_PREFIX:?REMOTE_PREFIX is required}"
: "${LOCAL_PREFIX:?LOCAL_PREFIX is required}"
: "${TRASH_PREFIX:?TRASH_PREFIX is required}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTHONPATH_EXTRA="${PYTHONPATH_EXTRA:-}"
MONTHS="${MONTHS:-202303 202304 202305 202306 202307 202308 202309 202310 202311 202312}"
WORKERS="${WORKERS:-4}"
SAMPLES="${SAMPLES:-6}"
USE_VISION_CONFIRM="${USE_VISION_CONFIRM:-1}"
PROGRESS_LOG="${PROGRESS_LOG:-$OUTPUT_DIR/full-cleanup-progress.tsv}"
MONTH_ROOT_CHECK="${MONTH_ROOT_CHECK:-$MOUNT_ROOT/监控视频/卧室/2023}"
VISION_DETECTOR="${VISION_DETECTOR:-}"

export PYTHONPATH="${PYTHONPATH_EXTRA}${PYTHONPATH_EXTRA:+:}${PYTHONPATH:-}"

if [ ! -d "$MONTH_ROOT_CHECK" ]; then
  echo "ERROR: expected mounted directory missing at $MONTH_ROOT_CHECK" >&2
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
  "$PYTHON_BIN" "$SCANNER" \
    --out "$out" \
    --move-empty \
    --move-via local \
    --remote-prefix "$REMOTE_PREFIX" \
    --local-prefix "$LOCAL_PREFIX" \
    --trash-prefix "$TRASH_PREFIX" \
    > "$move_log"

  moved="$(awk -F= '/^move_count=/{print $2}' "$move_log" | awk '{print $1}')"
  moved="${moved:-0}"
  printf "%s\t%s\tmoved\t%s\t%s\t%s\t%s\n" "$(date '+%F %T')" "$month" "$keep" "$empty" "$error" "$moved" >> "$PROGRESS_LOG"
  echo "[$(date '+%F %T')] month_done $month keep=$keep empty=$empty error=$error moved=$moved"
done

echo "[$(date '+%F %T')] cleanup_done"
