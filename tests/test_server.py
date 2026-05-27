import tempfile
import unittest
from pathlib import Path

from app.server import analyze_folder, delete_selected, organize_folder


class ServerWorkflowTest(unittest.TestCase):
    def test_analyze_includes_files_equal_to_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            video = base / "2024010100_equal.mp4"
            video.write_bytes(b"x" * 1024)

            result = analyze_folder(base, threshold_mb=1024 / (1024 * 1024))

            self.assertEqual(result["summary"]["candidate_count"], 1)
            self.assertEqual(result["candidates"][0]["path"], str(video))

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
