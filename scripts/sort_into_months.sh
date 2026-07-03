#!/bin/sh
set -eu

: "${SOURCE_BASE:?SOURCE_BASE is required}"
DRY_RUN="${DRY_RUN:-0}"

echo "BEGIN_SORT	$SOURCE_BASE	dry_run=$DRY_RUN"

for year_dir in "$SOURCE_BASE"/20[0-9][0-9]; do
  [ -d "$year_dir" ] || continue

  for hour_dir in "$year_dir"/20[0-9][0-9][01][0-9][0-3][0-9][0-2][0-9]; do
    [ -d "$hour_dir" ] || continue

    name=${hour_dir##*/}
    month=$(printf "%s" "$name" | cut -c1-6)
    month_dir="$year_dir/$month"
    dst="$month_dir/$name"

    if [ -e "$dst" ]; then
      if [ "$DRY_RUN" != "1" ]; then
        printf "skip_exists\t%s\t%s\n" "$hour_dir" "$dst"
      fi
      continue
    fi

    if [ "$DRY_RUN" = "1" ]; then
      printf "dry_run\t%s\t%s\n" "$hour_dir" "$dst"
      continue
    fi

    mkdir -p "$month_dir"
    if mv "$hour_dir" "$dst"; then
      printf "moved\t%s\t%s\n" "$hour_dir" "$dst"
    else
      printf "error\t%s\t%s\n" "$hour_dir" "$dst"
    fi
  done
done

echo "END_SORT"
