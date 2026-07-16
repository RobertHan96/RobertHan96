import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from jobs import core
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
            self.assertNotIn("zighang:https://example.com/new", saved_seen)

            core.mark_high_fit_matches_seen(selected, backend=backend)
            saved_seen = set(backend.get(HIGH_FIT_SEEN_KEY, []))
            self.assertIn("zighang:https://example.com/new", saved_seen)

    def test_collect_browser_sources_uses_fresh_page_and_keeps_other_sources(self) -> None:
        class FakePage:
            def __init__(self) -> None:
                self.closed = False

            def close(self) -> None:
                self.closed = True

        class FakeBrowser:
            def __init__(self) -> None:
                self.pages = []

            def new_page(self, **_kwargs):
                page = FakePage()
                self.pages.append(page)
                return page

        browser = FakeBrowser()

        def failing_scraper(_page, _limit):
            raise TimeoutError("첫 번째 소스 지연")

        def successful_scraper(_page, _limit):
            return [
                JobPosting(
                    source="test",
                    url="https://example.com/job",
                    raw_card_text="AI 엔지니어",
                    title="AI 엔지니어",
                )
            ]

        jobs, errors = core.collect_browser_sources(
            browser,
            [("실패소스", failing_scraper), ("정상소스", successful_scraper)],
            limit=5,
        )

        self.assertEqual(["AI 엔지니어"], [job.title for job in jobs])
        self.assertEqual(1, len(errors))
        self.assertEqual(2, len(browser.pages))
        self.assertTrue(all(page.closed for page in browser.pages))

    @patch("jobs.core.sync_playwright", side_effect=RuntimeError("Chromium 시작 실패"))
    @patch("jobs.core.scrape_zighang")
    @patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False)
    def test_run_monitor_keeps_http_results_when_browser_fails(
        self,
        zighang_mock,
        _playwright_mock,
    ) -> None:
        zighang_mock.return_value = [
            JobPosting(
                source="zighang",
                url="https://example.com/zighang",
                raw_card_text="LLM Agent Engineer",
                title="LLM Agent Engineer",
            )
        ]

        matches = core.run_monitor(limit_per_site=5, detail_top_n=1, min_score=0)

        self.assertEqual(["LLM Agent Engineer"], [match.job.title for match in matches])

    @patch.dict(
        "os.environ",
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_TIMEOUT_SECONDS": "90",
            "OPENAI_MAX_RETRIES": "1",
        },
        clear=False,
    )
    @patch("jobs.core.OpenAI")
    def test_openai_client_has_bounded_timeout_and_retries(self, openai_mock) -> None:
        core.get_openai_client()

        openai_mock.assert_called_once_with(
            api_key="test-key",
            timeout=90.0,
            max_retries=1,
        )

    def test_build_high_fit_titles_message_returns_empty_when_no_new_jobs(self) -> None:
        self.assertEqual("", build_high_fit_titles_message([]))


if __name__ == "__main__":
    unittest.main()
