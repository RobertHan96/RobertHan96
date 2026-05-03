import json
import tempfile
import unittest
from pathlib import Path

from scripts.automation.live_pipeline_storage import (
    load_manifest,
    save_manifest,
    save_transcript_payload,
    upsert_recording_entry,
)


class LivePipelineStorageTests(unittest.TestCase):
    def test_load_manifest_returns_default_shape_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = load_manifest(root / "manifest.json")
            self.assertEqual({"recordings": []}, manifest)

    def test_upsert_recording_entry_replaces_same_recording_id(self) -> None:
        manifest = {"recordings": [{"recording_id": "abc", "title": "old"}]}
        upsert_recording_entry(manifest, {"recording_id": "abc", "title": "new"})
        self.assertEqual(1, len(manifest["recordings"]))
        self.assertEqual("new", manifest["recordings"][0]["title"])

    def test_save_manifest_writes_utf8_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            save_manifest(path, {"recordings": [{"recording_id": "x"}]})
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("x", payload["recordings"][0]["recording_id"])

    def test_save_transcript_payload_writes_json_and_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {"text": "hello world", "segments": [{"text": "hello world"}]}
            result = save_transcript_payload(root, "abc123", payload)
            self.assertTrue(result["json_path"].exists())
            self.assertTrue(result["text_path"].exists())
            self.assertEqual("hello world", result["text_path"].read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    unittest.main()
