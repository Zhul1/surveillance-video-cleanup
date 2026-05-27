#!/bin/sh
set -eu

: "${SOURCE_BASE:?SOURCE_BASE is required}"
: "${TRASH_BASE:?TRASH_BASE is required}"

SIZE_THRESHOLD_BYTES="${SIZE_THRESHOLD_BYTES:-734003}"
LABEL="${LABEL:-size_based_move}"

echo "BEGIN	$LABEL	$SOURCE_BASE	$TRASH_BASE	$SIZE_THRESHOLD_BYTES"
count=0

find "$SOURCE_BASE" \( -path "*/@eaDir/*" -o -path "*/#recycle/*" \) -prune -o \
  -type f -iname "*.mp4" -size -"${SIZE_THRESHOLD_BYTES}"c -printf "%s\t%p\n" |
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
    elif [ "$actual" -ge "$SIZE_THRESHOLD_BYTES" ]; then
      status="skip_over_threshold"
      msg="actual=$actual"
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

  printf "%s\t%s\t%s\t%s\t%s\t%s\n" "$status" "$LABEL" "$size" "$src" "$dst" "$msg"
  if [ $((count % 1000)) -eq 0 ]; then
    echo "PROGRESS $LABEL $count" >&2
  fi
done

echo "END	$LABEL"
