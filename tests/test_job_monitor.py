import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "automation"))

import job_monitor  # noqa: E402


class JobMonitorMessageTests(unittest.TestCase):
    def test_build_message_omits_partial_failure_notice(self) -> None:
        message = job_monitor.build_message(
            {
                "AI 엔지니어": [
                    {
                        "link": "https://example.com/job",
                        "title": "AI 품질 엔지니어",
                        "company": "예시회사",
                        "source": "Wanted",
                        "summary": "생성형 AI 품질 및 평가 업무",
                    }
                ]
            },
            failed_labels=["클린아이 공공채용"],
        )
        self.assertIn("AI 품질 엔지니어", message)
        self.assertNotIn("일부 소스 수집 실패", message)
        self.assertNotIn("클린아이 공공채용", message)

    @patch("job_monitor.fetch_wanted_job_detail", return_value={})
    @patch("job_monitor.fetch_wanted_posted_date")
    @patch("job_monitor.wanted_request")
    def test_wanted_stops_after_consecutive_old_results(
        self,
        wanted_request_mock,
        posted_date_mock,
        _detail_mock,
    ) -> None:
        wanted_request_mock.return_value = {
            "data": [
                {"id": idx, "position": f"공고 {idx}", "company": {"name": "회사"}}
                for idx in range(10)
            ]
        }
        posted_date_mock.return_value = datetime.now(job_monitor.KST) - timedelta(days=4)

        jobs = job_monitor.search_wanted_jobs(
            "AI",
            limit=50,
            size=50,
            today_only=True,
            lookback_days=4,
        )

        self.assertEqual([], jobs)
        self.assertEqual(3, posted_date_mock.call_count)

    @patch("job_monitor.fetch_wanted_job_detail", return_value={})
    @patch("job_monitor.fetch_wanted_posted_date")
    @patch("job_monitor.wanted_request")
    def test_wanted_includes_jobs_from_schedule_gap(
        self,
        wanted_request_mock,
        posted_date_mock,
        _detail_mock,
    ) -> None:
        wanted_request_mock.return_value = {
            "data": [
                {"id": 101, "position": "AI Builder", "company": {"name": "회사"}}
            ]
        }
        posted_date_mock.return_value = datetime.now(job_monitor.KST) - timedelta(days=4)

        jobs = job_monitor.search_wanted_jobs(
            "AI",
            limit=50,
            size=50,
            today_only=True,
            lookback_days=5,
        )

        self.assertEqual([101], [job["id"] for job in jobs])

    def test_filter_unseen_results_removes_previously_delivered_jobs(self) -> None:
        results = {
            "AI": [
                {
                    "id": "known",
                    "source": "Wanted",
                    "title": "기존 공고",
                    "company": "회사",
                    "link": "https://example.com/known",
                    "summary": "기존",
                },
                {
                    "id": "new",
                    "source": "Wanted",
                    "title": "신규 공고",
                    "company": "회사",
                    "link": "https://example.com/new",
                    "summary": "신규",
                },
            ],
            "LLM": [
                {
                    "id": "new",
                    "source": "Wanted",
                    "title": "신규 공고",
                    "company": "회사",
                    "link": "https://example.com/new",
                    "summary": "신규",
                }
            ],
        }

        filtered, delivered_keys = job_monitor.filter_unseen_results(
            results,
            {"Wanted:known"},
        )

        self.assertEqual(["신규 공고"], [job["title"] for job in filtered["AI"]])
        self.assertEqual([], filtered["LLM"])
        self.assertEqual(["Wanted:new"], delivered_keys)

    @patch("job_monitor.fetch_cleaneye_job_detail", return_value="")
    @patch("job_monitor.cleaneye_request")
    def test_cleaneye_limits_pagination(self, cleaneye_request_mock, _detail_mock) -> None:
        cleaneye_request_mock.return_value = {
            "paginationInfo": {
                "recordCountPerPage": 10,
                "totalRecordCount": 1000,
            },
            "list": [],
        }

        job_monitor.search_cleaneye_jobs(
            {
                "name": "cleaneye",
                "today_only": False,
                "max_results": 50,
                "max_pages": 3,
            }
        )

        self.assertEqual(3, cleaneye_request_mock.call_count)


class JobMonitorDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.backend = job_monitor.JobMonitorStateBackend(Path(temp_dir.name) / "seen.json")
        self.backend.base_url = ""
        self.backend.token = ""
        self.config = self.start_patch("job_monitor.load_config")
        self.config.return_value = {"job_monitor": {"sources": [
            {"name": "zighang"}, {"name": "cleaneye"},
        ]}}
        self.zighang = self.start_patch("job_monitor.search_zighang_jobs")
        self.zighang.return_value = ("직행", [])
        self.cleaneye = self.start_patch("job_monitor.search_cleaneye_jobs")
        self.cleaneye.return_value = ("클린아이", [])
        self.send = self.start_patch("job_monitor.send_telegram")
        self.send.return_value = True
        self.start_patch("job_monitor.JobMonitorStateBackend").return_value = self.backend

    def start_patch(self, target):
        patcher = patch(target)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def test_no_new_jobs_does_not_send_telegram(self) -> None:
        job_monitor.main()
        self.send.assert_not_called()

    def test_partial_failure_without_jobs_does_not_send_telegram(self) -> None:
        self.cleaneye.side_effect = TimeoutError("느린 서버")
        job_monitor.main()
        self.send.assert_not_called()

    def test_all_sources_fail_sends_one_warning_and_fails(self) -> None:
        self.zighang.side_effect = TimeoutError("직행 응답 지연")
        self.cleaneye.side_effect = TimeoutError("클린아이 응답 지연")
        with self.assertRaisesRegex(RuntimeError, "모두 실패"):
            job_monitor.main()
        self.send.assert_called_once()
        self.assertIn("모든 소스", self.send.call_args.args[0])

    def test_existing_delivery_is_not_sent_again_on_next_run(self) -> None:
        self.zighang.return_value = ("직행", [{
            "id": "new", "source": "직행", "title": "AI Engineer",
            "company": "회사", "link": "https://example.com/new", "summary": "LLM",
        }])
        self.cleaneye.side_effect = TimeoutError("느린 서버")
        job_monitor.main()
        job_monitor.main()
        self.send.assert_called_once()
        self.assertNotIn("수집 실패", self.send.call_args.args[0])

    def test_delivery_failure_does_not_mark_jobs_as_seen(self) -> None:
        self.zighang.return_value = ("직행", [{
            "id": "new", "source": "직행", "title": "AI Engineer",
            "company": "회사", "link": "https://example.com/new", "summary": "LLM",
        }])
        self.send.side_effect = RuntimeError("텔레그램 장애")
        with self.assertRaises(RuntimeError):
            job_monitor.main()
        self.assertEqual([], self.backend.get(job_monitor.SEEN_STATE_KEY, []))


if __name__ == "__main__":
    unittest.main()
