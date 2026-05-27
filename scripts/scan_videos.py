#!/usr/bin/env python3
import argparse
import csv
import hashlib
import os
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class ScanResult:
    remote_path: str
    local_path: str
    decision: str
    reason: str
    person_hits: int
    motion_avg: float
    motion_max: float
    vision_hits: int
    frames_read: int
    duration: float
    size_bytes: int
    elapsed: float
    error: str = ""


def remote_to_local(remote_path: str, remote_prefix: str, local_prefix: str) -> str:
    if not remote_path.startswith(remote_prefix.rstrip("/") + "/"):
        raise ValueError(f"unexpected remote path: {remote_path}")
    return local_prefix.rstrip("/") + remote_path[len(remote_prefix.rstrip("/")) :]


def remote_to_trash(remote_path: str, source_root: str, trash_prefix: str) -> str:
    rel = remote_path[len(source_root.rstrip("/") + "/") :]
    return trash_prefix.rstrip("/") + "/" + rel


def remote_to_local_trash(remote_path: str, source_root: str, local_prefix: str, trash_prefix: str, remote_prefix: str) -> str:
    trash_remote = remote_to_trash(remote_path, source_root, trash_prefix)
    return remote_to_local(trash_remote, remote_prefix, local_prefix)


def load_cascades():
    base = cv2.data.haarcascades
    names = [
        "haarcascade_frontalface_default.xml",
        "haarcascade_profileface.xml",
        "haarcascade_upperbody.xml",
        "haarcascade_fullbody.xml",
    ]
    return [(name, cv2.CascadeClassifier(base + name)) for name in names]


def resize_width(frame, width):
    h, w = frame.shape[:2]
    if w <= width:
        return frame
    scale = width / float(w)
    return cv2.resize(frame, (width, max(1, int(h * scale))), interpolation=cv2.INTER_AREA)


def detect_people(frame, cascades, hog):
    small = resize_width(frame, 640)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    hits = 0

    for name, cascade in cascades:
        if cascade.empty():
            continue
        min_size = (24, 24) if "face" in name else (36, 36)
        detections = cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=min_size)
        hits += len(detections)

        if "profileface" in name:
            flipped = cv2.flip(gray, 1)
            detections = cascade.detectMultiScale(flipped, scaleFactor=1.05, minNeighbors=3, minSize=min_size)
            hits += len(detections)

    if hits:
        return hits

    _, weights = hog.detectMultiScale(small, winStride=(8, 8), padding=(16, 16), scale=1.05)
    for weight in np.asarray(weights).reshape(-1):
        if float(weight) >= 0.25:
            hits += 1
    return hits


def motion_scores(frames):
    prev = None
    scores = []
    for frame in frames:
        small = resize_width(frame, 320)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        if prev is not None:
            diff = cv2.absdiff(prev, gray)
            scores.append(float(np.mean(diff > 18)))
        prev = gray
    if not scores:
        return 0.0, 0.0
    return float(np.mean(scores)), float(np.max(scores))


def vision_confirm(frames, token, vision_detector, max_frames=6):
    if not vision_detector or not os.path.exists(vision_detector):
        return -1, "missing_vision_detector"
    tmp_dir = Path("/private/tmp/codex_vision_frames")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    image_paths = []
    try:
        selected = frames[:max_frames]
        for idx, frame in enumerate(selected):
            small = resize_width(frame, 640)
            path = tmp_dir / f"{os.getpid()}_{token}_{idx}.jpg"
            cv2.imwrite(str(path), small, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
            image_paths.append(str(path))
        proc = subprocess.run(
            [vision_detector] + image_paths,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
        if proc.returncode == 0:
            return 1, ""
        if proc.returncode == 1:
            return 0, ""
        return -1, (proc.stderr or proc.stdout).strip()[:240]
    except Exception as exc:
        return -1, repr(exc)
    finally:
        for path in image_paths:
            try:
                os.unlink(path)
            except OSError:
                pass


def sample_frames(path, sample_count):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError("cannot open video")

    frame_count = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    duration = frame_count / fps if frame_count > 0 and fps > 0 else 60.0
    duration = max(1.0, min(duration, 120.0))

    if sample_count <= 1:
        times = [duration / 2.0]
    else:
        margin = min(2.0, duration * 0.08)
        start = margin
        end = max(start, duration - margin)
        times = np.linspace(start, end, sample_count)

    frames = []
    for sec in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, float(sec) * 1000.0)
        ok, frame = cap.read()
        if ok and frame is not None:
            frames.append(frame)
    cap.release()
    return frames, duration


def scan_one(remote_path, args_dict):
    t0 = time.time()
    local_path = remote_to_local(remote_path, args_dict["remote_prefix"], args_dict["local_prefix"])
    try:
        size_bytes = os.path.getsize(local_path)
        frames, duration = sample_frames(local_path, args_dict["samples"])
        if not frames:
            return ScanResult(remote_path, local_path, "error", "no_frames", 0, 0.0, 0.0, 0, 0, 0.0, size_bytes, time.time() - t0, "no frames")

        cascades = load_cascades()
        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        person_hits = 0
        for frame in frames:
            person_hits += detect_people(frame, cascades, hog)
            if person_hits >= args_dict["person_hit_keep"]:
                break

        motion_avg, motion_max = motion_scores(frames)
        vision_hits = 0
        vision_error = ""

        low_motion = motion_max < args_dict["motion_max_keep"] and motion_avg < args_dict["motion_avg_keep"]
        if args_dict["vision_confirm"] and low_motion:
            token = hashlib.sha1(remote_path.encode("utf-8")).hexdigest()[:12]
            vision_hits, vision_error = vision_confirm(frames, token, args_dict["vision_detector"], max_frames=args_dict["vision_frames"])

        if low_motion and args_dict["vision_confirm"]:
            if vision_hits > 0:
                decision = "keep"
                reason = "vision_person"
            elif vision_hits == 0:
                decision = "empty_candidate"
                reason = "low_motion_vision_empty"
            elif person_hits >= args_dict["person_hit_keep"]:
                decision = "keep"
                reason = "vision_error_opencv_person"
            else:
                decision = "keep"
                reason = "vision_error_conservative"
        elif person_hits >= args_dict["person_hit_keep"]:
            decision = "keep"
            reason = "person"
        elif motion_max >= args_dict["motion_max_keep"] or motion_avg >= args_dict["motion_avg_keep"]:
            decision = "keep"
            reason = "motion"
        else:
            decision = "empty_candidate"
            reason = "no_person_low_motion"

        return ScanResult(
            remote_path,
            local_path,
            decision,
            reason,
            person_hits,
            motion_avg,
            motion_max,
            vision_hits,
            len(frames),
            duration,
            size_bytes,
            time.time() - t0,
            vision_error,
        )
    except Exception as exc:
        return ScanResult(remote_path, local_path, "error", "exception", 0, 0.0, 0.0, 0, 0, 0.0, 0, time.time() - t0, repr(exc))


def read_remote_list(path, limit=None, offset=0, month=None):
    selected = []
    with open(path, "r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh):
            if idx < offset:
                continue
            remote = line.rstrip("\n")
            if not remote:
                continue
            if month and f"/{month}/" not in remote:
                continue
            selected.append(remote)
            if limit and len(selected) >= limit:
                break
    return selected


def append_csv(path, results):
    exists = os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        if not exists:
            writer.writerow([
                "remote_path",
                "local_path",
                "decision",
                "reason",
                "person_hits",
                "motion_avg",
                "motion_max",
                "vision_hits",
                "frames_read",
                "duration",
                "size_bytes",
                "elapsed",
                "error",
            ])
        for r in results:
            writer.writerow([
                r.remote_path,
                r.local_path,
                r.decision,
                r.reason,
                r.person_hits,
                f"{r.motion_avg:.6f}",
                f"{r.motion_max:.6f}",
                r.vision_hits,
                r.frames_read,
                f"{r.duration:.3f}",
                r.size_bytes,
                f"{r.elapsed:.3f}",
                r.error,
            ])


def move_candidates_to_trash(csv_path, dry_run, max_count, via, remote_prefix, local_prefix, source_root, trash_prefix):
    moved = []
    with open(csv_path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row["decision"] != "empty_candidate":
                continue
            src = row["remote_path"]
            dst = remote_to_trash(src, source_root, trash_prefix)
            if dry_run:
                moved.append((src, dst, "dry_run"))
            elif via == "local":
                local_src = remote_to_local(src, remote_prefix, local_prefix)
                local_dst = remote_to_local_trash(src, source_root, local_prefix, trash_prefix, remote_prefix)
                os.makedirs(os.path.dirname(local_dst), exist_ok=True)
                if os.path.exists(local_dst):
                    moved.append((src, dst, "skip_exists"))
                elif not os.path.exists(local_src):
                    moved.append((src, dst, "skip_missing"))
                else:
                    os.rename(local_src, local_dst)
                    moved.append((src, dst, "moved"))
            else:
                parent = os.path.dirname(dst)
                subprocess.run(
                    ["ssh", "-p", "22", "admin@192.168.0.103", f"mkdir -p {sh_quote(parent)} && mv -n {sh_quote(src)} {sh_quote(dst)}"],
                    check=True,
                )
                moved.append((src, dst, "moved"))
            if max_count and len(moved) >= max_count:
                break
    return moved


def sh_quote(value):
    return "'" + value.replace("'", "'\"'\"'") + "'"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", required=False)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--month", help="Example: 202303")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--samples", type=int, default=6)
    parser.add_argument("--person-hit-keep", type=int, default=1)
    parser.add_argument("--motion-avg-keep", type=float, default=0.006)
    parser.add_argument("--motion-max-keep", type=float, default=0.015)
    parser.add_argument("--vision-confirm", action="store_true")
    parser.add_argument("--vision-frames", type=int, default=6)
    parser.add_argument("--vision-detector", default="")
    parser.add_argument("--move-empty", action="store_true")
    parser.add_argument("--move-via", choices=["local", "ssh"], default="local")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--move-max", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--remote-prefix", required=True)
    parser.add_argument("--local-prefix", required=True)
    parser.add_argument("--trash-prefix", required=True)
    parser.add_argument("--source-root", help="Path segment used to preserve relative structure under trash")
    args = parser.parse_args()

    source_root = args.source_root
    if not source_root:
        source_root = os.path.commonpath([args.trash_prefix.replace("/#recycle", ""), args.remote_prefix]).rstrip("/")

    if args.move_empty:
        moved = move_candidates_to_trash(
            args.out,
            dry_run=args.dry_run,
            max_count=args.move_max,
            via=args.move_via,
            remote_prefix=args.remote_prefix,
            local_prefix=args.local_prefix,
            source_root=source_root,
            trash_prefix=args.trash_prefix,
        )
        for src, dst, status in moved:
            print(f"{status}\t{src}\t{dst}")
        print(f"move_count={len(moved)} dry_run={args.dry_run}")
        return

    if not args.list:
        raise SystemExit("--list is required unless --move-empty is used")

    remotes = read_remote_list(args.list, limit=args.limit, offset=args.offset, month=args.month)
    if args.resume and os.path.exists(args.out):
        done = set()
        with open(args.out, "r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                done.add(row["remote_path"])
        before = len(remotes)
        remotes = [remote for remote in remotes if remote not in done]
        print(f"resume_skipped={before - len(remotes)}", flush=True)

    print(f"scan_count={len(remotes)} workers={args.workers} samples={args.samples}", flush=True)
    args_dict = {
        "samples": args.samples,
        "person_hit_keep": args.person_hit_keep,
        "motion_avg_keep": args.motion_avg_keep,
        "motion_max_keep": args.motion_max_keep,
        "vision_confirm": args.vision_confirm,
        "vision_frames": args.vision_frames,
        "vision_detector": args.vision_detector,
        "remote_prefix": args.remote_prefix,
        "local_prefix": args.local_prefix,
    }

    totals = {"keep": 0, "empty_candidate": 0, "error": 0}
    batch = []
    started = time.time()

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(scan_one, remote, args_dict) for remote in remotes]
        for idx, future in enumerate(as_completed(futures), 1):
            result = future.result()
            totals[result.decision] = totals.get(result.decision, 0) + 1
            batch.append(result)
            if len(batch) >= 50:
                append_csv(args.out, batch)
                batch.clear()
            if idx % 25 == 0 or idx == len(futures):
                elapsed = time.time() - started
                rate = idx / elapsed if elapsed else 0.0
                print(
                    f"progress={idx}/{len(futures)} rate={rate:.2f}/s "
                    f"keep={totals.get('keep', 0)} empty={totals.get('empty_candidate', 0)} error={totals.get('error', 0)}",
                    flush=True,
                )

    if batch:
        append_csv(args.out, batch)

    print(f"done keep={totals.get('keep', 0)} empty={totals.get('empty_candidate', 0)} error={totals.get('error', 0)}", flush=True)


if __name__ == "__main__":
    main()
