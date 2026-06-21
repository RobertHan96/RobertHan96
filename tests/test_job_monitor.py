import sys
import unittest
from pathlib import Path

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
        self.assertIn("정상 수집된 소스 기준으로는 오늘 등록된 새 채용공고가 없습니다.", message)
        self.assertNotIn("오늘 등록된 새 채용공고가 없습니다.", message.splitlines()[-1])


if __name__ == "__main__":
    unittest.main()
