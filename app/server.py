#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}
RECYCLE_DIR_NAME = ".nas-video-cleanup-trash"
IGNORE_DIR_NAMES = {"@eaDir", "#recycle", RECYCLE_DIR_NAME}
DATE_PATTERNS = [
    re.compile(r"(?P<stamp>20\d{8})"),  # YYYYMMDDHH
    re.compile(r"(?P<stamp>20\d{6})"),  # YYYYMMDD
]


@dataclass
class VideoEntry:
    path: str
    size_bytes: int
    size_mb: float
    modified_at: str
    inferred_date: str
    year: str
    month: str
    day: str
    suggested_folder: str
    needs_organize: bool
    is_candidate: bool


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


def iter_videos(base_dir: Path) -> Iterable[Path]:
    for root, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [name for name in dirnames if name not in IGNORE_DIR_NAMES]
        root_path = Path(root)
        for filename in filenames:
            path = root_path / filename
            if path.suffix.lower() in VIDEO_EXTENSIONS:
                yield path


def infer_date_from_path(path: Path) -> datetime:
    candidates = list(path.parts[::-1])
    candidates.append(path.name)
    for chunk in candidates:
        for pattern in DATE_PATTERNS:
            match = pattern.search(chunk)
            if not match:
                continue
            stamp = match.group("stamp")
            try:
                if len(stamp) == 10:
                    return datetime.strptime(stamp, "%Y%m%d%H")
                if len(stamp) == 8:
                    return datetime.strptime(stamp, "%Y%m%d")
            except ValueError:
                continue
    return datetime.fromtimestamp(path.stat().st_mtime)


def day_folder_for(base_dir: Path, dt: datetime) -> Path:
    year = dt.strftime("%Y")
    month = dt.strftime("%Y%m")
    day = dt.strftime("%Y%m%d")
    return base_dir / year / month / day


def build_entry(base_dir: Path, path: Path, threshold_bytes: int) -> VideoEntry:
    stat = path.stat()
    dt = infer_date_from_path(path)
    target_dir = day_folder_for(base_dir, dt)
    expected_parent = target_dir.resolve()
    current_parent = path.parent.resolve()
    try:
        needs_organize = current_parent != expected_parent
    except OSError:
        needs_organize = True
    return VideoEntry(
        path=str(path),
        size_bytes=stat.st_size,
        size_mb=round(stat.st_size / (1024 * 1024), 3),
        modified_at=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        inferred_date=dt.strftime("%Y-%m-%d"),
        year=dt.strftime("%Y"),
        month=dt.strftime("%Y%m"),
        day=dt.strftime("%Y%m%d"),
        suggested_folder=str(target_dir),
        needs_organize=needs_organize,
        is_candidate=stat.st_size <= threshold_bytes,
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


def analyze_folder(base_dir: Path, threshold_mb: float) -> dict:
    threshold_bytes = int(threshold_mb * 1024 * 1024)
    entries = [build_entry(base_dir, path, threshold_bytes) for path in iter_videos(base_dir)]
    entries.sort(key=lambda item: item.path)
    candidates = [asdict(entry) for entry in entries if entry.is_candidate]
    organize_count = sum(1 for entry in entries if entry.needs_organize)
    total_size = sum(entry.size_bytes for entry in entries)
    return {
        "folder": str(base_dir),
        "threshold_mb": threshold_mb,
        "summary": {
            "video_count": len(entries),
            "candidate_count": len(candidates),
            "organize_count": organize_count,
            "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2),
            "candidate_size_gb": round(sum(item["size_bytes"] for item in candidates) / (1024 * 1024 * 1024), 2),
        },
        "candidates": candidates,
    }


def organize_folder(base_dir: Path) -> dict:
    moved = []
    skipped = []
    for video_path in list(iter_videos(base_dir)):
        dt = infer_date_from_path(video_path)
        target_dir = day_folder_for(base_dir, dt)
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
                base_dir = sanitize_folder(payload.get("folder", ""))
                threshold_mb = float(payload.get("threshold_mb", 1.0))
                if threshold_mb <= 0:
                    raise ValueError("阈值必须大于 0")
                json_response(self, analyze_folder(base_dir, threshold_mb))
                return

            if parsed.path == "/api/organize":
                base_dir = sanitize_folder(payload.get("folder", ""))
                json_response(self, organize_folder(base_dir))
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


def main() -> None:
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), AppHandler)
    print(f"NAS Video Cleanup UI running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
