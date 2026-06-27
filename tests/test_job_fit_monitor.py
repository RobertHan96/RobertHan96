import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from jobs.core import (
    HIGH_FIT_SEEN_KEY,
    JobMatch,
    JobPosting,
    StateBackend,
    build_high_fit_titles_message,
    select_new_high_fit_matches,
)


class JobFitMonitorTests(unittest.TestCase):
    def build_match(self, url: str, title: str, score: int = 90) -> JobMatch:
        return JobMatch(
            job=JobPosting(
                source="zighang",
                url=url,
                raw_card_text=title,
                title=title,
                company="테스트회사",
            ),
            score=score,
        )

    @patch.dict(
        "os.environ",
        {
            "JOB_FIT_REPORT_BRIDGE_URL": "",
            "TELEGRAM_MEMORY_BRIDGE_URL": "",
            "JOB_FIT_REPORT_BRIDGE_TOKEN": "",
            "TELEGRAM_MEMORY_BRIDGE_TOKEN": "",
        },
        clear=False,
    )
    def test_select_new_high_fit_matches_skips_seen_jobs(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            backend = StateBackend(local_path=Path(tmp_dir) / "state.json")
            seen_match = self.build_match("https://example.com/seen", "이미 본 공고")
            new_match = self.build_match("https://example.com/new", "새 공고")
            backend.put(HIGH_FIT_SEEN_KEY, ["zighang:https://example.com/seen"])

            selected = select_new_high_fit_matches(
                [seen_match, new_match],
                backend=backend,
                min_score=80,
                limit=5,
            )

            self.assertEqual(["새 공고"], [match.job.title for match in selected])
            saved_seen = set(backend.get(HIGH_FIT_SEEN_KEY, []))
            self.assertIn("zighang:https://example.com/seen", saved_seen)
            self.assertIn("zighang:https://example.com/new", saved_seen)

    def test_build_high_fit_titles_message_returns_empty_when_no_new_jobs(self) -> None:
        self.assertEqual("", build_high_fit_titles_message([]))


if __name__ == "__main__":
    unittest.main()
