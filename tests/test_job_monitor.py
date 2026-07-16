import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "automation"))

import job_monitor  # noqa: E402


class JobMonitorMessageTests(unittest.TestCase):
    def test_build_message_appends_failed_source_notice(self) -> None:
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
        self.assertIn("일부 소스 수집 실패", message)
        self.assertIn("클린아이 공공채용", message)

    def test_build_partial_failure_message_avoids_false_no_jobs_claim(self) -> None:
        message = job_monitor.build_partial_failure_message(
            {
                "AI 엔지니어": [],
                "클린아이 공공채용": [],
            },
            failed_labels=["클린아이 공공채용"],
        )
        self.assertIn("일부 소스 수집이 실패했습니다", message)
        self.assertIn("정상 수집된 소스 기준으로는 새로 알릴 채용공고가 없습니다.", message)
        self.assertNotIn("최근 조회 범위에서 새로 알릴 채용공고가 없습니다.", message)

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
        posted_date_mock.return_value = datetime.now(job_monitor.KST) - timedelta(days=2)

        jobs = job_monitor.search_wanted_jobs(
            "AI",
            limit=50,
            size=50,
            today_only=True,
            lookback_days=4,
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


if __name__ == "__main__":
    unittest.main()
