import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.automation.live_pipeline_media import build_recording_id, scan_recordings
from scripts.automation.live_shorts_pipeline import build_shorts_ffmpeg_command


class LivePipelineMediaTests(unittest.TestCase):
    def test_build_recording_id_changes_when_size_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.mp4"
            path.write_bytes(b"abc")
            first = build_recording_id(path)
            path.write_bytes(b"abcd")
            second = build_recording_id(path)
            self.assertNotEqual(first, second)

    @patch("scripts.automation.live_pipeline_media.probe_video_metadata")
    def test_scan_recordings_lists_supported_video_files(self, probe_video_metadata) -> None:
        probe_video_metadata.return_value = {"duration_seconds": 10, "width": 1920, "height": 1080}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.mp4").write_bytes(b"x")
            (root / "b.txt").write_text("ignore", encoding="utf-8")
            items = scan_recordings(root)
            self.assertEqual(1, len(items))
            self.assertEqual("a.mp4", items[0]["filename"])

    def test_build_shorts_ffmpeg_command_targets_vertical_render(self) -> None:
        command = build_shorts_ffmpeg_command(
            input_path="/tmp/input.mp4",
            output_path="/tmp/output.mp4",
            start_seconds=10,
            end_seconds=50,
            subtitle_path="/tmp/subtitles.srt",
        )
        joined = " ".join(command)
        self.assertIn("/tmp/input.mp4", joined)
        self.assertIn("/tmp/output.mp4", joined)
        self.assertIn("scale=1080:1920", joined)


if __name__ == "__main__":
    unittest.main()
