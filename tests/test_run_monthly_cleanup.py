import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


class RunMonthlyCleanupScriptTest(unittest.TestCase):
    def test_monthly_cleanup_defaults_move_phase_to_dry_run(self):
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / "scripts" / "run_monthly_cleanup.sh"

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            mount = base / "mount"
            output = base / "output"
            video_list = base / "videos.txt"
            scanner = base / "fake_scanner.py"
            mount.mkdir()
            video_list.write_text("/remote/camera/202401/clip.mp4\n", encoding="utf-8")
            scanner.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import argparse
                    import csv

                    parser = argparse.ArgumentParser()
                    parser.add_argument("--list")
                    parser.add_argument("--out", required=True)
                    parser.add_argument("--month")
                    parser.add_argument("--workers")
                    parser.add_argument("--samples")
                    parser.add_argument("--resume", action="store_true")
                    parser.add_argument("--vision-confirm", action="store_true")
                    parser.add_argument("--vision-detector")
                    parser.add_argument("--move-empty", action="store_true")
                    parser.add_argument("--move-via")
                    parser.add_argument("--dry-run", action="store_true")
                    parser.add_argument("--remote-prefix", required=True)
                    parser.add_argument("--local-prefix", required=True)
                    parser.add_argument("--trash-prefix", required=True)
                    parser.add_argument("--source-root")
                    args = parser.parse_args()

                    if args.move_empty:
                        print(f"dry_run={args.dry_run}")
                        print(f"move_count=1 dry_run={args.dry_run}")
                    else:
                        with open(args.out, "w", encoding="utf-8", newline="") as fh:
                            writer = csv.DictWriter(fh, fieldnames=["remote_path", "decision"])
                            writer.writeheader()
                            writer.writerow({"remote_path": "/remote/camera/202401/clip.mp4", "decision": "empty_candidate"})
                    """
                ),
                encoding="utf-8",
            )
            scanner.chmod(0o755)

            env = {
                **os.environ,
                "MONTHS": "202401",
                "SCANNER": str(scanner),
                "VIDEO_LIST": str(video_list),
                "OUTPUT_DIR": str(output),
                "REMOTE_PREFIX": "/remote",
                "LOCAL_PREFIX": str(mount),
                "TRASH_PREFIX": "/remote/#recycle",
                "USE_VISION_CONFIRM": "0",
            }
            subprocess.run([str(script)], check=True, env=env, text=True, capture_output=True)

            progress = (output / "full-cleanup-progress.tsv").read_text(encoding="utf-8")
            move_log = (output / "move-full-202401.log").read_text(encoding="utf-8")
            self.assertIn("\t202401\tdry_run\t", progress)
            self.assertIn("dry_run=True", move_log)


if __name__ == "__main__":
    unittest.main()
