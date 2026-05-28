import tempfile
import unittest
import shutil
import subprocess
from pathlib import Path

from app.server import analyze_folder, delete_selected, mean_abs_difference, organize_folder


class ServerWorkflowTest(unittest.TestCase):
    def test_analyze_includes_files_equal_to_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            video = base / "2024010100_equal.mp4"
            video.write_bytes(b"x" * 1024)

            result = analyze_folder(base, threshold_mb=1024 / (1024 * 1024))

            self.assertEqual(result["summary"]["candidate_count"], 1)
            self.assertEqual(result["candidates"][0]["path"], str(video))
            self.assertEqual(result["candidates"][0]["candidate_reasons"], ["size"])

    def test_size_filter_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            video = base / "2024010100_small.mp4"
            video.write_bytes(b"x" * 10)

            result = analyze_folder(base, threshold_mb=1.0, use_size_filter=False)

            self.assertEqual(result["summary"]["candidate_count"], 0)

    def test_mean_abs_difference(self):
        self.assertEqual(mean_abs_difference(bytes([0, 10, 255]), bytes([0, 20, 250])), 5.0)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg and ffprobe are required")
    def test_static_filter_marks_unchanged_video_as_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            video = base / "2024010100_static.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=64x64:d=1:r=2",
                    "-pix_fmt",
                    "yuv420p",
                    str(video),
                ],
                check=True,
            )

            result = analyze_folder(
                base,
                threshold_mb=0.0001,
                use_size_filter=False,
                use_static_filter=True,
                static_threshold=0.5,
            )

            self.assertEqual(result["summary"]["candidate_count"], 1)
            self.assertIn("static", result["candidates"][0]["candidate_reasons"])
            self.assertLessEqual(result["candidates"][0]["static_score"], 0.5)

    def test_organize_moves_to_year_month_day_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            video = base / "2024010100_clip.mp4"
            video.write_bytes(b"video")

            result = organize_folder(base)

            expected = base / "2024" / "202401" / "20240101" / video.name
            self.assertEqual(result["moved_count"], 1)
            self.assertTrue(expected.exists())

    def test_delete_selected_recycles_inside_base_and_skips_outside(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside_tmp:
            base = Path(tmp).resolve()
            video = base / "clip.mp4"
            outside = Path(outside_tmp).resolve() / "outside.mp4"
            video.write_bytes(b"video")
            outside.write_bytes(b"video")

            result = delete_selected(base, [str(video), str(outside)], mode="recycle")

            self.assertEqual(result["deleted_count"], 1)
            self.assertEqual(result["skipped_count"], 1)
            self.assertFalse(video.exists())
            self.assertTrue((base / ".nas-video-cleanup-trash" / "clip.mp4").exists())
            self.assertTrue(outside.exists())


if __name__ == "__main__":
    unittest.main()
