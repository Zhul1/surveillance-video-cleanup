#!/bin/sh
set -eu

: "${SOURCE_BASE:?SOURCE_BASE is required}"
: "${TRASH_BASE:?TRASH_BASE is required}"

SIZE_THRESHOLD_BYTES="${SIZE_THRESHOLD_BYTES:-734003}"
LABEL="${LABEL:-size_based_move}"
DRY_RUN="${DRY_RUN:-0}"

echo "BEGIN	$LABEL	$SOURCE_BASE	$TRASH_BASE	$SIZE_THRESHOLD_BYTES	dry_run=$DRY_RUN"
count=0

find "$SOURCE_BASE" \( -path "*/@eaDir/*" -o -path "*/#recycle/*" \) -prune -o \
  -type f \( \
    -iname "*.3g2" -o -iname "*.3gp" -o -iname "*.264" -o -iname "*.asf" -o \
    -iname "*.avi" -o -iname "*.dav" -o -iname "*.flv" -o -iname "*.h264" -o \
    -iname "*.h265" -o -iname "*.hevc" -o -iname "*.m2ts" -o -iname "*.m4v" -o \
    -iname "*.mjpeg" -o -iname "*.mjpg" -o -iname "*.mkv" -o -iname "*.mov" -o \
    -iname "*.mp4" -o -iname "*.mpeg" -o -iname "*.mpg" -o -iname "*.mts" -o \
    -iname "*.ts" -o -iname "*.vob" -o -iname "*.webm" \
  \) -exec sh -c '
    threshold=$1
    shift
    for src do
      size=$(wc -c < "$src" 2>/dev/null | tr -d " ")
      [ -n "$size" ] || continue
      [ "$size" -le "$threshold" ] || continue
      printf "%s\t%s\n" "$size" "$src"
    done
  ' sh "$SIZE_THRESHOLD_BYTES" {} + |
while IFS="	" read -r size src; do
  count=$((count + 1))
  rel=${src#"$SOURCE_BASE"/}
  dst="$TRASH_BASE/$rel"
  status="unknown"
  msg=""

  if [ ! -f "$src" ]; then
    status="skip_missing"
  elif [ -e "$dst" ]; then
    status="skip_exists"
  else
    actual=$(wc -c < "$src" 2>/dev/null | tr -d ' ')
    if [ -z "$actual" ]; then
      status="error"
      msg="size_read_failed"
    elif [ "$actual" -ne "$size" ]; then
      status="skip_size_changed"
      msg="actual=$actual"
    elif [ "$actual" -gt "$SIZE_THRESHOLD_BYTES" ]; then
      status="skip_over_threshold"
      msg="actual=$actual"
    elif [ "$DRY_RUN" = "1" ]; then
      status="dry_run"
      msg="dry_run=1"
    else
      mkdir -p "${dst%/*}"
      if mv -n "$src" "$dst"; then
        status="moved"
      else
        status="error"
        msg="mv_failed"
      fi
    fi
  fi

  if [ "$DRY_RUN" = "1" ] && [ "$status" != "dry_run" ]; then
    continue
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\n" "$status" "$LABEL" "$size" "$src" "$dst" "$msg"
  if [ $((count % 1000)) -eq 0 ]; then
    echo "PROGRESS $LABEL $count" >&2
  fi
done

echo "END	$LABEL"
