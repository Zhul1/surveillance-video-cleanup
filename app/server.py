#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import errno
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
VIDEO_EXTENSIONS = {
    ".3g2",
    ".3gp",
    ".264",
    ".asf",
    ".avi",
    ".dav",
    ".flv",
    ".h264",
    ".h265",
    ".hevc",
    ".m2ts",
    ".m4v",
    ".mjpeg",
    ".mjpg",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".mts",
    ".ts",
    ".vob",
    ".webm",
}
RECYCLE_DIR_NAME = ".nas-video-cleanup-trash"
IGNORE_DIR_NAMES = {"@eaDir", "#recycle", RECYCLE_DIR_NAME}
STATIC_FRAME_WIDTH = 96
STATIC_FRAME_HEIGHT = 54
DATE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<!\d)(?P<stamp>20\d{12})(?!\d)"), "%Y%m%d%H%M%S"),
    (re.compile(r"(?<!\d)(?P<stamp>20\d{10})(?!\d)"), "%Y%m%d%H%M"),
    (re.compile(r"(?<!\d)(?P<stamp>20\d{8})(?!\d)"), "%Y%m%d%H"),
    (re.compile(r"(?<!\d)(?P<stamp>20\d{6})(?!\d)"), "%Y%m%d"),
]
SEPARATED_DATE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?P<year>20\d{2})[./_\- ]"
    r"(?P<month>0[1-9]|1[0-2])[./_\- ]"
    r"(?P<day>0[1-9]|[12]\d|3[01])"
    r"(?:[ T_@\-]+(?P<hour>[01]\d|2[0-3])"
    r"(?::|\.|_|-)?(?P<minute>[0-5]\d)?"
    r"(?::|\.|_|-)?(?P<second>[0-5]\d)?)?"
    r"(?!\d)"
)
DEFAULT_PROTECTED_KEYWORDS = [
    "alarm",
    "event",
    "favorite",
    "human",
    "lock",
    "motion",
    "people",
    "person",
    "保留",
    "报警",
    "告警",
    "人形",
    "事件",
    "移动侦测",
    "重要",
]
DEVICE_SIGNATURES = {
    "Hikvision": ["hikvision", "海康", "ds-", "ch01"],
    "Dahua": ["dahua", "大华", ".dav"],
    "Uniview": ["uniview", "宇视"],
    "Reolink": ["reolink"],
    "EZVIZ": ["ezviz", "萤石"],
    "TP-Link/Tapo": ["tapo", "tplink", "tp-link"],
    "Eufy": ["eufy"],
    "Xiaomi/Mijia": ["xiaomi", "mijia", "米家", "小米"],
    "Ring": ["ring"],
    "Wyze": ["wyze"],
}
ORGANIZE_GRANULARITIES = {"day", "month"}
ANALYZE_JOBS: dict[str, dict] = {}
ANALYZE_JOBS_LOCK = threading.Lock()


@dataclass(frozen=True)
class CleanupOptions:
    threshold_mb: float = 1.0
    use_size_filter: bool = True
    use_empty_filter: bool = True
    use_retention_filter: bool = False
    retention_days: int = 180
    use_static_filter: bool = False
    static_threshold: float = 2.0
    protected_keywords: list[str] | None = None
    extensions: set[str] | None = None
    organize_granularity: str = "day"


@dataclass
class VideoEntry:
    path: str
    size_bytes: int
    size_mb: float
    extension: str
    device_hint: str
    age_days: int
    modified_at: str
    inferred_date: str
    year: str
    month: str
    day: str
    suggested_folder: str
    needs_organize: bool
    is_protected: bool
    protect_reasons: list[str]
    is_candidate: bool
    candidate_reasons: list[str]
    static_score: float | None
    static_checked: bool


def json_response(handler: BaseHTTPRequestHandler, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def sanitize_folder(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("请输入文件夹路径")
    path = Path(raw_path).expanduser().resolve()
    if not path.exists():
        raise ValueError("文件夹不存在")
    if not path.is_dir():
        raise ValueError("输入路径不是文件夹")
    return path


def choose_folder() -> dict:
    if sys.platform != "darwin":
        raise ValueError("当前只支持在 macOS 上选择目录")
    if shutil.which("osascript") is None:
        raise ValueError("找不到 osascript，无法打开目录选择器")

    proc = subprocess.run(
        ["osascript", "-e", 'POSIX path of (choose folder with prompt "选择视频目录")'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        raise ValueError("已取消选择目录")
    folder = sanitize_folder(proc.stdout.strip())
    return {"folder": str(folder)}


def open_folder(raw_path: str) -> dict:
    folder = sanitize_folder(raw_path)
    if sys.platform == "darwin":
        command = ["open", str(folder)]
    elif sys.platform.startswith("linux"):
        command = ["xdg-open", str(folder)]
    elif sys.platform.startswith("win"):
        command = ["explorer", str(folder)]
    else:
        raise ValueError("当前系统不支持打开目录")
    if shutil.which(command[0]) is None:
        raise ValueError(f"找不到 {command[0]}，无法打开目录")
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    return {"opened": str(folder)}


def normalize_extensions(raw_extensions: object | None = None) -> set[str]:
    if raw_extensions is None:
        return set(VIDEO_EXTENSIONS)
    if isinstance(raw_extensions, str):
        chunks = re.split(r"[\s,;，；]+", raw_extensions)
    elif isinstance(raw_extensions, list):
        chunks = [str(item) for item in raw_extensions]
    else:
        raise ValueError("视频格式列表无效")
    extensions = set()
    for chunk in chunks:
        item = chunk.strip().lower()
        if not item:
            continue
        if not item.startswith("."):
            item = f".{item}"
        if not re.fullmatch(r"\.[a-z0-9]+", item):
            raise ValueError(f"视频格式无效: {chunk}")
        extensions.add(item)
    if not extensions:
        raise ValueError("至少保留一种视频格式")
    return extensions


def normalize_keywords(raw_keywords: object | None) -> list[str]:
    if raw_keywords is None:
        return list(DEFAULT_PROTECTED_KEYWORDS)
    if isinstance(raw_keywords, str):
        chunks = re.split(r"[\n,;，；]+", raw_keywords)
    elif isinstance(raw_keywords, list):
        chunks = [str(item) for item in raw_keywords]
    else:
        raise ValueError("保护关键词格式无效")
    keywords = []
    seen = set()
    for chunk in chunks:
        item = chunk.strip()
        key = item.casefold()
        if item and key not in seen:
            keywords.append(item)
            seen.add(key)
    return keywords


def default_cleanup_options(**overrides) -> CleanupOptions:
    data = {
        "protected_keywords": list(DEFAULT_PROTECTED_KEYWORDS),
        "extensions": set(VIDEO_EXTENSIONS),
    }
    data.update(overrides)
    return CleanupOptions(**data)


def iter_videos(base_dir: Path, extensions: set[str] | None = None) -> Iterable[Path]:
    allowed_extensions = extensions or VIDEO_EXTENSIONS
    for root, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [name for name in dirnames if name not in IGNORE_DIR_NAMES]
        root_path = Path(root)
        for filename in filenames:
            path = root_path / filename
            if path.suffix.lower() in allowed_extensions:
                yield path


def parse_datetime_from_text(text: str) -> datetime | None:
    for pattern, fmt in DATE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                return datetime.strptime(match.group("stamp"), fmt)
            except ValueError:
                continue
    for match in SEPARATED_DATE_PATTERN.finditer(text):
        try:
            return datetime(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
                int(match.group("hour") or 0),
                int(match.group("minute") or 0),
                int(match.group("second") or 0),
            )
        except ValueError:
            continue
    return None


def infer_date_from_path(path: Path) -> datetime:
    candidates = [path.name, *path.parts[::-1], path.as_posix()]
    for chunk in candidates:
        parsed = parse_datetime_from_text(chunk)
        if parsed is not None:
            return parsed
    return datetime.fromtimestamp(path.stat().st_mtime)


def destination_folder_for(base_dir: Path, dt: datetime, granularity: str = "day") -> Path:
    year = dt.strftime("%Y")
    month = dt.strftime("%Y%m")
    if granularity == "month":
        return base_dir / year / month
    if granularity != "day":
        raise ValueError("整理粒度无效")
    day = dt.strftime("%Y%m%d")
    return base_dir / year / month / day


def day_folder_for(base_dir: Path, dt: datetime) -> Path:
    return destination_folder_for(base_dir, dt, "day")


def device_hint_for(path: Path) -> str:
    text = path.as_posix().casefold()
    for label, signatures in DEVICE_SIGNATURES.items():
        if any(signature.casefold() in text for signature in signatures):
            return label
    return "通用"


def protection_reasons_for(path: Path, keywords: list[str]) -> list[str]:
    text = path.as_posix().casefold()
    return [keyword for keyword in keywords if keyword.casefold() in text]


def ffmpeg_tools_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def probe_duration(path: Path) -> float | None:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        return None
    try:
        duration = float(proc.stdout.strip())
    except ValueError:
        return None
    return duration if duration > 0 else None


def probe_frame_count(path: Path) -> int | None:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_frames",
            "-show_entries",
            "stream=nb_read_frames,nb_frames",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        if line.isdigit():
            count = int(line)
            if count > 0:
                return count
    return None


def frame_filter(prefix: str = "") -> str:
    scale_filter = (
        f"scale={STATIC_FRAME_WIDTH}:{STATIC_FRAME_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={STATIC_FRAME_WIDTH}:{STATIC_FRAME_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "format=rgb24"
    )
    return f"{prefix}{scale_filter}"


def read_frame_from_command(command: list[str]) -> bytes | None:
    proc = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    )
    expected_size = STATIC_FRAME_WIDTH * STATIC_FRAME_HEIGHT * 3
    if proc.returncode != 0 or len(proc.stdout) != expected_size:
        return None
    return proc.stdout


def read_video_frame_at_time(path: Path, seconds: float) -> bytes | None:
    return read_frame_from_command(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{max(0.0, seconds):.3f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            frame_filter(),
            "-f",
            "rawvideo",
            "pipe:1",
        ]
    )


def read_video_frame_by_number(path: Path, frame_number: int) -> bytes | None:
    return read_frame_from_command(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-vf",
            frame_filter(f"select=eq(n\\,{max(0, frame_number)}),"),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "pipe:1",
        ]
    )


def read_video_frame(path: Path, seconds: float) -> bytes | None:
    return read_video_frame_at_time(path, seconds)


def read_first_last_frames(path: Path) -> tuple[bytes | None, bytes | None]:
    frame_count = probe_frame_count(path)
    if frame_count is not None:
        return read_video_frame_by_number(path, 0), read_video_frame_by_number(path, frame_count - 1)

    duration = probe_duration(path)
    if duration is None:
        return None, None
    return read_video_frame_at_time(path, 0.0), read_video_frame_at_time(path, max(0.0, duration - 0.5))


def mean_abs_difference(left: bytes, right: bytes) -> float:
    if len(left) != len(right):
        raise ValueError("frame sizes differ")
    if not left:
        return 0.0
    total = sum(abs(a - b) for a, b in zip(left, right))
    return total / len(left)


def static_frame_score(path: Path) -> float | None:
    first, last = read_first_last_frames(path)
    if first is None or last is None:
        return None
    return mean_abs_difference(first, last)


def age_days_for(modified_at: float, now: datetime | None = None) -> int:
    current = now or datetime.now()
    age = current - datetime.fromtimestamp(modified_at)
    return max(0, age.days)


def build_entry(
    base_dir: Path,
    path: Path,
    threshold_bytes: int,
    use_size_filter: bool,
    use_static_filter: bool,
    static_threshold: float,
    options: CleanupOptions | None = None,
) -> VideoEntry:
    if options is None:
        options = default_cleanup_options(
            threshold_mb=threshold_bytes / (1024 * 1024),
            use_size_filter=use_size_filter,
            use_static_filter=use_static_filter,
            static_threshold=static_threshold,
        )
    threshold_bytes = int(options.threshold_mb * 1024 * 1024)
    use_size_filter = options.use_size_filter
    use_static_filter = options.use_static_filter
    static_threshold = options.static_threshold
    stat = path.stat()
    dt = infer_date_from_path(path)
    target_dir = destination_folder_for(base_dir, dt, options.organize_granularity)
    expected_parent = target_dir.resolve()
    current_parent = path.parent.resolve()
    try:
        needs_organize = current_parent != expected_parent
    except OSError:
        needs_organize = True
    candidate_reasons = []
    protect_reasons = protection_reasons_for(path, options.protected_keywords or [])
    static_score = None
    static_checked = False
    if options.use_empty_filter and stat.st_size == 0:
        candidate_reasons.append("empty")
    if use_size_filter and stat.st_size > 0 and stat.st_size <= threshold_bytes:
        candidate_reasons.append("size")
    if options.use_retention_filter:
        cutoff = datetime.now() - timedelta(days=options.retention_days)
        if datetime.fromtimestamp(stat.st_mtime) < cutoff:
            candidate_reasons.append("old")
    if use_static_filter:
        static_checked = True
        static_score = static_frame_score(path)
        if static_score is not None and static_score <= static_threshold:
            candidate_reasons.append("static")
    if protect_reasons:
        candidate_reasons = []

    return VideoEntry(
        path=str(path),
        size_bytes=stat.st_size,
        size_mb=round(stat.st_size / (1024 * 1024), 3),
        extension=path.suffix.lower(),
        device_hint=device_hint_for(path),
        age_days=age_days_for(stat.st_mtime),
        modified_at=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        inferred_date=dt.strftime("%Y-%m-%d"),
        year=dt.strftime("%Y"),
        month=dt.strftime("%Y%m"),
        day=dt.strftime("%Y%m%d"),
        suggested_folder=str(target_dir),
        needs_organize=needs_organize,
        is_protected=bool(protect_reasons),
        protect_reasons=protect_reasons,
        is_candidate=bool(candidate_reasons),
        candidate_reasons=candidate_reasons,
        static_score=round(static_score, 3) if static_score is not None else None,
        static_checked=static_checked,
    )


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 1
    while True:
        candidate = parent / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def analyze_folder(
    base_dir: Path,
    threshold_mb: float,
    use_size_filter: bool = True,
    use_static_filter: bool = False,
    static_threshold: float = 2.0,
    use_empty_filter: bool = True,
    use_retention_filter: bool = False,
    retention_days: int = 180,
    protected_keywords: list[str] | None = None,
    extensions: set[str] | None = None,
    organize_granularity: str = "day",
) -> dict:
    options = default_cleanup_options(
        threshold_mb=threshold_mb,
        use_size_filter=use_size_filter,
        use_empty_filter=use_empty_filter,
        use_retention_filter=use_retention_filter,
        retention_days=retention_days,
        use_static_filter=use_static_filter,
        static_threshold=static_threshold,
        protected_keywords=list(DEFAULT_PROTECTED_KEYWORDS) if protected_keywords is None else protected_keywords,
        extensions=extensions or set(VIDEO_EXTENSIONS),
        organize_granularity=organize_granularity,
    )
    return analyze_folder_with_options(base_dir, options)


def analyze_folder_with_options(base_dir: Path, options: CleanupOptions) -> dict:
    threshold_bytes = int(options.threshold_mb * 1024 * 1024)
    if options.use_static_filter and not ffmpeg_tools_available():
        raise ValueError("首尾帧检测需要安装 ffmpeg 和 ffprobe")
    entries = analyze_entries(
        base_dir,
        list(iter_videos(base_dir, options.extensions)),
        threshold_bytes,
        options.use_size_filter,
        options.use_static_filter,
        options.static_threshold,
        options=options,
    )
    return format_analysis_result(
        base_dir,
        options,
        entries,
    )


def analyze_entries(
    base_dir: Path,
    video_paths: list[Path],
    threshold_bytes: int,
    use_size_filter: bool,
    use_static_filter: bool,
    static_threshold: float,
    options: CleanupOptions | None = None,
    progress_callback=None,
) -> list[VideoEntry]:
    if options is None:
        options = default_cleanup_options(
            threshold_mb=threshold_bytes / (1024 * 1024),
            use_size_filter=use_size_filter,
            use_static_filter=use_static_filter,
            static_threshold=static_threshold,
        )
    entries = []
    for index, path in enumerate(video_paths, 1):
        entry = build_entry(
            base_dir,
            path,
            threshold_bytes,
            use_size_filter,
            use_static_filter,
            static_threshold,
            options,
        )
        entries.append(entry)
        if progress_callback:
            progress_callback(index, path, entry)
    entries.sort(key=lambda item: item.path)
    return entries


def format_analysis_result(
    base_dir: Path,
    options: CleanupOptions,
    entries: list[VideoEntry],
    total_video_count: int | None = None,
) -> dict:
    candidates = [asdict(entry) for entry in entries if entry.is_candidate]
    organize_count = sum(1 for entry in entries if entry.needs_organize)
    protected_count = sum(1 for entry in entries if entry.is_protected)
    total_size = sum(entry.size_bytes for entry in entries)
    video_count = len(entries) if total_video_count is None else total_video_count
    reason_counts: dict[str, int] = {}
    extension_counts: dict[str, int] = {}
    for entry in entries:
        extension_counts[entry.extension] = extension_counts.get(entry.extension, 0) + 1
        for reason in entry.candidate_reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "folder": str(base_dir),
        "options": {
            "threshold_mb": options.threshold_mb,
            "use_size_filter": options.use_size_filter,
            "use_empty_filter": options.use_empty_filter,
            "use_retention_filter": options.use_retention_filter,
            "retention_days": options.retention_days,
            "use_static_filter": options.use_static_filter,
            "static_threshold": options.static_threshold,
            "protected_keywords": options.protected_keywords or [],
            "extensions": sorted(options.extensions or []),
            "organize_granularity": options.organize_granularity,
        },
        "threshold_mb": options.threshold_mb,
        "use_size_filter": options.use_size_filter,
        "use_static_filter": options.use_static_filter,
        "static_threshold": options.static_threshold,
        "summary": {
            "video_count": video_count,
            "analyzed_count": len(entries),
            "candidate_count": len(candidates),
            "organize_count": organize_count,
            "protected_count": protected_count,
            "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2),
            "candidate_size_gb": round(sum(item["size_bytes"] for item in candidates) / (1024 * 1024 * 1024), 2),
            "reason_counts": reason_counts,
            "extension_counts": dict(sorted(extension_counts.items())),
        },
        "candidates": candidates,
    }


def job_payload(job: dict) -> dict:
    elapsed = round(time.monotonic() - job["started_at"], 1)
    total = job.get("total", 0)
    processed = job.get("processed", 0)
    return {
        "job_id": job["job_id"],
        "state": job["state"],
        "phase": job["phase"],
        "folder": job["folder"],
        "processed": processed,
        "total": total,
        "remaining": max(total - processed, 0),
        "candidate_count": job.get("candidate_count", 0),
        "current_path": job.get("current_path", ""),
        "elapsed_seconds": elapsed,
        "error": job.get("error", ""),
        "result": job.get("result"),
        "control": job.get("control", "run"),
    }


def update_analyze_job(job_id: str, **changes) -> None:
    with ANALYZE_JOBS_LOCK:
        job = ANALYZE_JOBS.get(job_id)
        if not job:
            return
        job.update(changes)


def get_analyze_job(job_id: str) -> dict:
    with ANALYZE_JOBS_LOCK:
        job = ANALYZE_JOBS.get(job_id)
        if not job:
            raise ValueError("分析任务不存在")
        return job_payload(job)


def control_analyze_job(job_id: str, action: str) -> dict:
    if action not in {"pause", "resume", "stop"}:
        raise ValueError("分析控制命令无效")
    with ANALYZE_JOBS_LOCK:
        job = ANALYZE_JOBS.get(job_id)
        if not job:
            raise ValueError("分析任务不存在")
        if job["state"] in {"done", "error", "stopped"}:
            return job_payload(job)
        if action == "pause":
            job["control"] = "pause"
            if job["state"] not in {"paused", "pause_requested"}:
                job["state"] = "pause_requested"
                job["phase"] = "pausing"
        elif action == "resume":
            job["control"] = "run"
            job["state"] = "running"
            job["phase"] = "analyzing"
        else:
            job["control"] = "stop"
            job["state"] = "stopping"
            job["phase"] = "stopping"
        return job_payload(job)


def wait_for_analyze_control(job_id: str) -> str:
    while True:
        with ANALYZE_JOBS_LOCK:
            job = ANALYZE_JOBS.get(job_id)
            if not job:
                return "stop"
            control = job.get("control", "run")
            if control == "stop":
                return "stop"
            if control == "pause":
                job["state"] = "paused"
                job["phase"] = "paused"
            else:
                if job["state"] == "paused":
                    job["state"] = "running"
                    job["phase"] = "analyzing"
                return "run"
        time.sleep(0.2)


def run_analyze_job(
    job_id: str,
    base_dir: Path,
    threshold_mb: float,
    use_size_filter: bool,
    use_static_filter: bool,
    static_threshold: float,
    options: CleanupOptions | None = None,
) -> None:
    try:
        if options is None:
            options = default_cleanup_options(
                threshold_mb=threshold_mb,
                use_size_filter=use_size_filter,
                use_static_filter=use_static_filter,
                static_threshold=static_threshold,
            )
        if options.use_static_filter and not ffmpeg_tools_available():
            raise ValueError("首尾帧检测需要安装 ffmpeg 和 ffprobe")
        threshold_bytes = int(options.threshold_mb * 1024 * 1024)
        update_analyze_job(job_id, state="running", phase="collecting", current_path="")
        video_paths = list(iter_videos(base_dir, options.extensions))
        update_analyze_job(job_id, phase="analyzing", total=len(video_paths), processed=0)
        entries: list[VideoEntry] = []
        stopped = False

        for index, path in enumerate(video_paths, 1):
            if wait_for_analyze_control(job_id) == "stop":
                stopped = True
                break
            entry = build_entry(
                base_dir,
                path,
                threshold_bytes,
                options.use_size_filter,
                options.use_static_filter,
                options.static_threshold,
                options,
            )
            entries.append(entry)
            with ANALYZE_JOBS_LOCK:
                job = ANALYZE_JOBS.get(job_id)
                if not job:
                    return
                job["processed"] = index
                job["current_path"] = str(path)
                if entry.is_candidate:
                    job["candidate_count"] = job.get("candidate_count", 0) + 1
                if job.get("control") == "stop":
                    stopped = True
        entries.sort(key=lambda item: item.path)
        result = format_analysis_result(
            base_dir,
            options,
            entries,
            total_video_count=len(video_paths),
        )
        if stopped:
            update_analyze_job(
                job_id,
                state="stopped",
                phase="stopped",
                current_path="",
                candidate_count=result["summary"]["candidate_count"],
                result=result,
            )
            return
        update_analyze_job(
            job_id,
            state="done",
            phase="done",
            processed=len(video_paths),
            total=len(video_paths),
            current_path="",
            candidate_count=result["summary"]["candidate_count"],
            result=result,
        )
    except Exception as exc:
        update_analyze_job(job_id, state="error", phase="error", error=str(exc), current_path="")


def start_analyze_job(
    base_dir: Path,
    threshold_mb: float,
    use_size_filter: bool,
    use_static_filter: bool,
    static_threshold: float,
    options: CleanupOptions | None = None,
) -> dict:
    if options is None:
        options = default_cleanup_options(
            threshold_mb=threshold_mb,
            use_size_filter=use_size_filter,
            use_static_filter=use_static_filter,
            static_threshold=static_threshold,
        )
    job_id = uuid.uuid4().hex
    job = {
        "job_id": job_id,
        "state": "queued",
        "phase": "queued",
        "folder": str(base_dir),
        "processed": 0,
        "total": 0,
        "candidate_count": 0,
        "current_path": "",
        "error": "",
        "result": None,
        "control": "run",
        "started_at": time.monotonic(),
    }
    with ANALYZE_JOBS_LOCK:
        ANALYZE_JOBS[job_id] = job
    thread = threading.Thread(
        target=run_analyze_job,
        args=(job_id, base_dir, threshold_mb, use_size_filter, use_static_filter, static_threshold, options),
        daemon=True,
    )
    thread.start()
    return job_payload(job)


def parse_analyze_payload(payload: dict) -> tuple[Path, CleanupOptions]:
    base_dir = sanitize_folder(payload.get("folder", ""))
    threshold_mb = float(payload.get("threshold_mb", 1.0))
    use_size_filter = bool(payload.get("use_size_filter", True))
    use_empty_filter = bool(payload.get("use_empty_filter", True))
    use_retention_filter = bool(payload.get("use_retention_filter", False))
    retention_days = int(payload.get("retention_days", 180))
    use_static_filter = bool(payload.get("use_static_filter", False))
    static_threshold = float(payload.get("static_threshold", 2.0))
    protected_keywords = normalize_keywords(payload.get("protected_keywords"))
    extensions = normalize_extensions(payload.get("extensions"))
    organize_granularity = str(payload.get("organize_granularity", "day"))
    if threshold_mb <= 0:
        raise ValueError("阈值必须大于 0")
    if retention_days <= 0:
        raise ValueError("保留天数必须大于 0")
    if static_threshold < 0:
        raise ValueError("静态差异阈值不能小于 0")
    if organize_granularity not in ORGANIZE_GRANULARITIES:
        raise ValueError("整理粒度无效")
    return base_dir, CleanupOptions(
        threshold_mb=threshold_mb,
        use_size_filter=use_size_filter,
        use_empty_filter=use_empty_filter,
        use_retention_filter=use_retention_filter,
        retention_days=retention_days,
        use_static_filter=use_static_filter,
        static_threshold=static_threshold,
        protected_keywords=protected_keywords,
        extensions=extensions,
        organize_granularity=organize_granularity,
    )


def organize_folder(base_dir: Path, granularity: str = "day", extensions: set[str] | None = None) -> dict:
    if granularity not in ORGANIZE_GRANULARITIES:
        raise ValueError("整理粒度无效")
    moved = []
    skipped = []
    for video_path in list(iter_videos(base_dir, extensions)):
        dt = infer_date_from_path(video_path)
        target_dir = destination_folder_for(base_dir, dt, granularity)
        if video_path.parent.resolve() == target_dir.resolve():
            skipped.append(str(video_path))
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = unique_destination(target_dir / video_path.name)
        shutil.move(str(video_path), str(destination))
        moved.append({"from": str(video_path), "to": str(destination)})
    return {
        "moved_count": len(moved),
        "skipped_count": len(skipped),
        "moved_preview": moved[:30],
    }


def delete_selected(base_dir: Path, paths: list[str], mode: str) -> dict:
    deleted = []
    skipped = []
    recycle_dir = base_dir / RECYCLE_DIR_NAME
    for raw_path in paths:
        path = Path(raw_path).resolve()
        if not path.exists():
            skipped.append({"path": raw_path, "reason": "missing"})
            continue
        if base_dir not in path.parents:
            skipped.append({"path": raw_path, "reason": "outside_base"})
            continue
        if mode == "recycle":
            rel = path.relative_to(base_dir)
            destination = unique_destination(recycle_dir / rel)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(destination))
            deleted.append({"from": str(path), "to": str(destination), "mode": "recycle"})
        else:
            path.unlink()
            deleted.append({"path": str(path), "mode": "delete"})
    return {"deleted_count": len(deleted), "skipped_count": len(skipped), "deleted": deleted[:30], "skipped": skipped[:30]}


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            json_response(self, {"ok": True})
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            json_response(self, {"error": "请求数据不是合法 JSON"}, HTTPStatus.BAD_REQUEST)
            return

        try:
            if parsed.path == "/api/analyze":
                base_dir, options = parse_analyze_payload(payload)
                json_response(
                    self,
                    analyze_folder_with_options(base_dir, options),
                )
                return

            if parsed.path == "/api/analyze/start":
                base_dir, options = parse_analyze_payload(payload)
                json_response(
                    self,
                    start_analyze_job(
                        base_dir,
                        options.threshold_mb,
                        use_size_filter=options.use_size_filter,
                        use_static_filter=options.use_static_filter,
                        static_threshold=options.static_threshold,
                        options=options,
                    ),
                    HTTPStatus.ACCEPTED,
                )
                return

            if parsed.path == "/api/analyze/status":
                job_id = payload.get("job_id", "")
                if not isinstance(job_id, str) or not job_id:
                    raise ValueError("分析任务 ID 无效")
                json_response(self, get_analyze_job(job_id))
                return

            if parsed.path == "/api/analyze/control":
                job_id = payload.get("job_id", "")
                action = payload.get("action", "")
                if not isinstance(job_id, str) or not job_id:
                    raise ValueError("分析任务 ID 无效")
                if not isinstance(action, str):
                    raise ValueError("分析控制命令无效")
                json_response(self, control_analyze_job(job_id, action))
                return

            if parsed.path == "/api/pick-folder":
                json_response(self, choose_folder())
                return

            if parsed.path == "/api/open-folder":
                json_response(self, open_folder(payload.get("folder", "")))
                return

            if parsed.path == "/api/organize":
                base_dir = sanitize_folder(payload.get("folder", ""))
                granularity = str(payload.get("organize_granularity", "day"))
                extensions = normalize_extensions(payload.get("extensions"))
                json_response(self, organize_folder(base_dir, granularity=granularity, extensions=extensions))
                return

            if parsed.path == "/api/delete":
                base_dir = sanitize_folder(payload.get("folder", ""))
                paths = payload.get("paths", [])
                mode = payload.get("mode", "recycle")
                if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
                    raise ValueError("删除列表格式不正确")
                if mode not in {"recycle", "delete"}:
                    raise ValueError("删除模式无效")
                json_response(self, delete_selected(base_dir, paths, mode))
                return
        except ValueError as exc:
            json_response(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:  # pragma: no cover
            json_response(self, {"error": f"处理失败: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        json_response(self, {"error": "未找到接口"}, HTTPStatus.NOT_FOUND)

    def serve_static(self, raw_path: str) -> None:
        path = raw_path or "/"
        if path == "/":
            path = "/index.html"
        safe_path = path.lstrip("/")
        file_path = (STATIC_DIR / safe_path).resolve()
        if STATIC_DIR.resolve() not in file_path.parents and file_path != STATIC_DIR.resolve():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{mime_type or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args) -> None:
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


def create_server(port: int, max_attempts: int = 20) -> ThreadingHTTPServer:
    last_error = None
    for candidate_port in range(port, port + max_attempts):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate_port), AppHandler)
            if candidate_port != port:
                print(f"Port {port} is busy; using {candidate_port} instead.")
            return server
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
            last_error = exc
    raise OSError(errno.EADDRINUSE, f"No available port from {port} to {port + max_attempts - 1}") from last_error


def main() -> None:
    port = int(os.environ.get("PORT", "8765"))
    server = create_server(port)
    actual_port = server.server_address[1]
    print(f"NAS Video Cleanup UI running at http://127.0.0.1:{actual_port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
