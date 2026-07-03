from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.scan_videos import move_candidates_to_trash, remote_to_local, remote_to_trash


class ScanPathTest(unittest.TestCase):
    def test_remote_to_local_requires_remote_prefix(self):
        with self.assertRaises(ValueError):
            remote_to_local("/volume2/video.mp4", "/volume1", "/mnt")

    def test_remote_to_trash_preserves_relative_path(self):
        self.assertEqual(
            remote_to_trash(
                "/volume1/camera/2024/clip.mp4",
                "/volume1/camera",
                "/volume1/#recycle/camera",
            ),
            "/volume1/#recycle/camera/2024/clip.mp4",
        )

    def test_remote_to_trash_requires_source_root_prefix(self):
        with self.assertRaises(ValueError):
            remote_to_trash(
                "/volume1/other/clip.mp4",
                "/volume1/camera",
                "/volume1/#recycle/camera",
            )

    def test_ssh_move_uses_configured_target(self):
        src = "/volume1/camera/2024/clip one.mp4"
        expected_dst = "/volume1/#recycle/camera/2024/clip one.mp4"
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "scan.csv"
            csv_path.write_text(f"remote_path,decision\n{src},empty_candidate\n", encoding="utf-8")

            with patch("scripts.scan_videos.subprocess.run") as run:
                moved = move_candidates_to_trash(
                    str(csv_path),
                    dry_run=False,
                    max_count=None,
                    via="ssh",
                    remote_prefix="/volume1/camera",
                    local_prefix="/mnt/camera",
                    source_root="/volume1/camera",
                    trash_prefix="/volume1/#recycle/camera",
                    ssh_host="nas.example",
                    ssh_user="operator",
                    ssh_port=2202,
                )

        self.assertEqual(moved, [(src, expected_dst, "moved")])
        run.assert_called_once_with(
            [
                "ssh",
                "-p",
                "2202",
                "operator@nas.example",
                "mkdir -p '/volume1/#recycle/camera/2024' && mv -n '/volume1/camera/2024/clip one.mp4' '/volume1/#recycle/camera/2024/clip one.mp4'",
            ],
            check=True,
        )
        command_text = " ".join(run.call_args.args[0])
        self.assertNotIn("admin@192.168.0.103", command_text)
        self.assertNotIn("192.168.0.103", command_text)

    def test_dry_run_does_not_call_subprocess(self):
        src = "/volume1/camera/2024/clip.mp4"
        expected_dst = "/volume1/#recycle/camera/2024/clip.mp4"
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "scan.csv"
            csv_path.write_text(f"remote_path,decision\n{src},empty_candidate\n", encoding="utf-8")

            with patch("scripts.scan_videos.subprocess.run") as run:
                moved = move_candidates_to_trash(
                    str(csv_path),
                    dry_run=True,
                    max_count=None,
                    via="ssh",
                    remote_prefix="/volume1/camera",
                    local_prefix="/mnt/camera",
                    source_root="/volume1/camera",
                    trash_prefix="/volume1/#recycle/camera",
                )

        self.assertEqual(moved, [(src, expected_dst, "dry_run")])
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
