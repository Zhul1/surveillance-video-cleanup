import unittest

from scripts.scan_videos import remote_to_local, remote_to_trash


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


if __name__ == "__main__":
    unittest.main()
