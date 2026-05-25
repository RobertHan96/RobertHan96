import unittest

from scripts.automation.live_content_pipeline import select_stable_recordings


class LiveContentPipelineWatcherTests(unittest.TestCase):
    def test_select_stable_recordings_waits_for_second_stable_scan(self) -> None:
        cache: dict[str, dict] = {}
        recordings = [
            {
                "recording_id": "rec-1",
                "path": "/tmp/a.mp4",
                "size_bytes": 100,
                "recorded_at": "2026-05-25T10:00:00",
                "status": {"transcript": "pending"},
            }
        ]

        self.assertEqual([], select_stable_recordings(recordings, cache, required_stable_polls=2))
        self.assertEqual(["rec-1"], select_stable_recordings(recordings, cache, required_stable_polls=2))

    def test_select_stable_recordings_resets_when_file_signature_changes(self) -> None:
        cache: dict[str, dict] = {}
        first = [
            {
                "recording_id": "rec-1",
                "path": "/tmp/a.mp4",
                "size_bytes": 100,
                "recorded_at": "2026-05-25T10:00:00",
                "status": {"transcript": "pending"},
            }
        ]
        changed = [
            {
                "recording_id": "rec-2",
                "path": "/tmp/a.mp4",
                "size_bytes": 200,
                "recorded_at": "2026-05-25T10:02:00",
                "status": {"transcript": "pending"},
            }
        ]

        self.assertEqual([], select_stable_recordings(first, cache, required_stable_polls=2))
        self.assertEqual([], select_stable_recordings(changed, cache, required_stable_polls=2))
        self.assertEqual(["rec-2"], select_stable_recordings(changed, cache, required_stable_polls=2))

    def test_select_stable_recordings_skips_already_processed_items(self) -> None:
        cache: dict[str, dict] = {}
        recordings = [
            {
                "recording_id": "rec-1",
                "path": "/tmp/a.mp4",
                "size_bytes": 100,
                "recorded_at": "2026-05-25T10:00:00",
                "status": {"transcript": "succeeded"},
            }
        ]

        self.assertEqual([], select_stable_recordings(recordings, cache, required_stable_polls=1))


if __name__ == "__main__":
    unittest.main()
