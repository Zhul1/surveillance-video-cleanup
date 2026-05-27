import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class MoveBySizeScriptTest(unittest.TestCase):
    def test_moves_files_less_than_or_equal_to_threshold(self):
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "scripts" / "move_by_size.sh"

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "source"
            trash = Path(tmp) / "trash"
            base.mkdir()

            small = base / "small.mp4"
            exact = base / "exact.mp4"
            large = base / "large.mp4"
            small.write_bytes(b"x" * 8)
            exact.write_bytes(b"x" * 1024)
            large.write_bytes(b"x" * 1025)

            env = {
                **os.environ,
                "SOURCE_BASE": str(base),
                "TRASH_BASE": str(trash),
                "SIZE_THRESHOLD_BYTES": "1024",
            }
            subprocess.run([str(script)], check=True, env=env, text=True, capture_output=True)

            self.assertFalse(small.exists())
            self.assertFalse(exact.exists())
            self.assertTrue(large.exists())
            self.assertTrue((trash / "small.mp4").exists())
            self.assertTrue((trash / "exact.mp4").exists())


if __name__ == "__main__":
    unittest.main()
