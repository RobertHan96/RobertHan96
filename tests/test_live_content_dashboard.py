import unittest
from unittest.mock import patch
from urllib.parse import unquote
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from services.live_content_dashboard import app


class LiveDashboardTests(unittest.TestCase):
    @patch("services.live_content_dashboard.get_dashboard_recordings")
    def test_dashboard_home_responds(self, get_dashboard_recordings) -> None:
        get_dashboard_recordings.return_value = []
        client = TestClient(app)
        response = client.get("/")
        self.assertEqual(200, response.status_code)
        self.assertIn("최근 녹화 영상", response.text)

    @patch("services.live_content_dashboard.get_dashboard_recordings")
    def test_dashboard_shows_artifact_links_when_available(self, get_dashboard_recordings) -> None:
        get_dashboard_recordings.return_value = [
            {
                "recording_id": "abc123",
                "filename": "sample.mp4",
                "recorded_at": "2026-05-04 10:00",
                "formatted_duration": "10:00",
                "formatted_size": "10.0MB",
                "status": {
                    "transcript": "succeeded",
                    "analysis": "succeeded",
                    "blog_draft": "succeeded",
                    "shorts": "succeeded",
                },
                "errors": {},
                "title_candidates": [],
                "topics": [],
                "shorts_candidates": [],
                "artifacts": {
                    "blog_post_path": "/tmp/blog.md",
                    "last_short_render_path": "/tmp/short.mp4",
                },
            }
        ]
        client = TestClient(app)
        response = client.get("/")
        self.assertEqual(200, response.status_code)
        self.assertIn("블로그 초안 보기", response.text)
        self.assertIn("숏츠 재생", response.text)
        self.assertIn("Finder에서 보기", response.text)

    @patch("services.live_content_dashboard.get_dashboard_recordings")
    def test_dashboard_auto_refreshes_when_job_running(self, get_dashboard_recordings) -> None:
        get_dashboard_recordings.return_value = [
            {
                "recording_id": "abc123",
                "filename": "sample.mp4",
                "recorded_at": "2026-05-04 10:00",
                "formatted_duration": "10:00",
                "formatted_size": "10.0MB",
                "status": {"transcript": "running"},
                "errors": {},
                "title_candidates": [],
                "topics": [],
                "shorts_candidates": [],
                "artifacts": {},
            }
        ]
        client = TestClient(app)
        response = client.get("/")
        self.assertEqual(200, response.status_code)
        self.assertIn("자동 새로고침", response.text)
        self.assertIn('http-equiv="refresh"', response.text)

    @patch("services.live_content_dashboard.enqueue_pipeline_task")
    def test_transcribe_enqueues_and_redirects_immediately(self, enqueue_pipeline_task) -> None:
        enqueue_pipeline_task.return_value = (True, "STT 작업을 시작했습니다.")
        client = TestClient(app)
        response = client.post("/recordings/abc123/transcribe", follow_redirects=False)
        self.assertEqual(303, response.status_code)
        self.assertEqual("/?flash=STT%20%EC%9E%91%EC%97%85%EC%9D%84%20%EC%8B%9C%EC%9E%91%ED%96%88%EC%8A%B5%EB%8B%88%EB%8B%A4.&level=success", response.headers["location"])
        enqueue_pipeline_task.assert_called_once()

    @patch("services.live_content_dashboard.enqueue_pipeline_task")
    def test_analyze_returns_busy_message_without_blocking(self, enqueue_pipeline_task) -> None:
        enqueue_pipeline_task.return_value = (False, "이미 실행 중인 작업입니다.")
        client = TestClient(app)
        response = client.post("/recordings/abc123/analyze", follow_redirects=False)
        self.assertEqual(303, response.status_code)
        location = unquote(response.headers["location"])
        self.assertIn("이미 실행 중인 작업입니다.", location)
        self.assertIn("level=info", location)

    @patch("services.live_content_dashboard.get_recording_entry")
    def test_artifact_route_returns_file_response(self, get_recording_entry) -> None:
        with TemporaryDirectory() as temp_dir:
            artifact_path = Path(temp_dir) / "draft.md"
            artifact_path.write_text("# hello\n", encoding="utf-8")
            get_recording_entry.return_value = {
                "recording_id": "abc123",
                "artifacts": {"blog_post_path": str(artifact_path)},
            }
            client = TestClient(app)
            response = client.get("/recordings/abc123/artifacts/blog-post")
            self.assertEqual(200, response.status_code)
            self.assertIn("hello", response.text)

    @patch("services.live_content_dashboard.subprocess.run")
    @patch("services.live_content_dashboard.get_recording_entry")
    def test_reveal_artifact_redirects(self, get_recording_entry, subprocess_run) -> None:
        with TemporaryDirectory() as temp_dir:
            artifact_path = Path(temp_dir) / "blog.md"
            artifact_path.write_text("# hello\n", encoding="utf-8")
            get_recording_entry.return_value = {
                "recording_id": "abc123",
                "artifacts": {"blog_post_path": str(artifact_path)},
            }
            client = TestClient(app)
            response = client.post("/recordings/abc123/reveal/blog-post", follow_redirects=False)
            self.assertEqual(303, response.status_code)
            subprocess_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
