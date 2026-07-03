import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class SortIntoMonthsScriptTest(unittest.TestCase):
    def test_moves_hour_directories_into_month_directories(self):
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "scripts" / "sort_into_months.sh"

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "source"
            year_dir = base / "2026"
            hour_dir = year_dir / "2026010203"
            video = hour_dir / "clip.mp4"
            hour_dir.mkdir(parents=True)
            video.write_bytes(b"x")

            env = {**os.environ, "SOURCE_BASE": str(base)}
            result = subprocess.run(
                [str(script)], check=True, env=env, text=True, capture_output=True
            )

            dst = year_dir / "202601" / "2026010203"
            self.assertFalse(hour_dir.exists())
            self.assertTrue((dst / "clip.mp4").exists())
            self.assertIn("dry_run=0", result.stdout)
            self.assertIn(f"moved\t{hour_dir}\t{dst}", result.stdout)

    def test_dry_run_reports_without_moving_or_creating_target(self):
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "scripts" / "sort_into_months.sh"

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "source"
            year_dir = base / "2026"
            hour_dir = year_dir / "2026010203"
            video = hour_dir / "clip.mp4"
            hour_dir.mkdir(parents=True)
            video.write_bytes(b"x")

            env = {**os.environ, "SOURCE_BASE": str(base), "DRY_RUN": "1"}
            result = subprocess.run(
                [str(script)], check=True, env=env, text=True, capture_output=True
            )

            dst = year_dir / "202601" / "2026010203"
            self.assertTrue((hour_dir / "clip.mp4").exists())
            self.assertFalse(dst.exists())
            self.assertFalse(dst.parent.exists())
            self.assertIn("dry_run=1", result.stdout)
            self.assertIn(f"dry_run\t{hour_dir}\t{dst}", result.stdout)


if __name__ == "__main__":
    unittest.main()
