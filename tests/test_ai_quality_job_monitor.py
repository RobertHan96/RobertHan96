import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jobs.ai_quality_profile import AI_QUALITY_CANDIDATE
from jobs.ai_quality_monitor import (
    build_cj_detail_url,
    build_daily_summary_message,
    build_samsung_detail_api_url,
    extract_naver_anno_id,
    handle_immediate_alerts,
    is_closed_job,
    merge_summary_records,
    score_role_relevance,
    send_message_if_available,
)
from jobs.core import JobPosting, score_text


class AIQualityMonitorTests(unittest.TestCase):
    def test_score_role_relevance_rewards_ai_quality_roles(self) -> None:
        score, matched, penalized = score_role_relevance(
            "AI 서비스 품질 및 안전성 평가 담당자 LLM Evaluation Prompt Evaluation Red Teaming"
        )
        self.assertGreaterEqual(score, 80)
        self.assertIn("안전성", " ".join(matched))
        self.assertEqual([], penalized)

    def test_score_role_relevance_penalizes_generic_manufacturing_qa(self) -> None:
        score, matched, penalized = score_role_relevance(
            "반도체 공정 품질보증 QA 담당자 협력사 품질 감사 및 출하 품질 관리"
        )
        self.assertLessEqual(score, 25)
        self.assertTrue(penalized)

    def test_score_role_relevance_rewards_ai_builder_roles(self) -> None:
        score, matched, penalized = score_role_relevance(
            "AI Builder Forward Developer LLM Agent RAG Developer Productivity Platform"
        )
        self.assertGreaterEqual(score, 45)
        self.assertIn("Builder", " ".join(matched))
        self.assertEqual([], penalized)

    def test_candidate_profile_rewards_forward_developer_context(self) -> None:
        score, matched = score_text(
            "Forward Deployed Engineer building enterprise AI agent platform for developer productivity",
            AI_QUALITY_CANDIDATE,
        )
        self.assertGreaterEqual(score, 20)
        self.assertIn("developer productivity", matched)

    def test_extract_naver_anno_id_recovers_numeric_id(self) -> None:
        self.assertEqual("30004975", extract_naver_anno_id("show('30004975')"))

    def test_build_cj_detail_url_supports_regular_detail(self) -> None:
        self.assertEqual(
            "https://recruit.cj.net/recruit/ko/recruit/recruit/detail.fo?zz_jo_num=8634&closeYn=88888",
            build_cj_detail_url("goNewDetail('1', '8634', 'Y', '88888');return false;"),
        )

    def test_build_cj_detail_url_supports_best_detail(self) -> None:
        self.assertEqual(
            "https://recruit.cj.net/recruit/ko/recruit/recruit/bestDetail.fo?direct=N&zz_jo_num=J20260619039118&closeYn=88888",
            build_cj_detail_url("goNewDetail('2', 'J20260619039118', 'N', '88888');return false;"),
        )

    def test_build_samsung_detail_api_url_normalizes_seqno(self) -> None:
        self.assertEqual(
            "https://www.samsungcareers.com/recruit/detail.data?seqno=22436&strCode=",
            build_samsung_detail_api_url("22,436"),
        )

    def test_merge_summary_records_deduplicates_and_keeps_higher_score(self) -> None:
        merged = merge_summary_records(
            [
                {
                    "job_key": "kakao:https://example.com/1",
                    "title": "AI 서비스 품질 담당자",
                    "score": 78,
                }
            ],
            [
                {
                    "job_key": "kakao:https://example.com/1",
                    "title": "AI 서비스 품질 담당자",
                    "score": 88,
                },
                {
                    "job_key": "naver:https://example.com/2",
                    "title": "AI 품질 엔지니어",
                    "score": 72,
                },
            ],
        )
        self.assertEqual(2, len(merged))
        self.assertEqual(88, merged[0]["score"])

    def test_build_daily_summary_message_groups_high_fit_and_review(self) -> None:
        message = build_daily_summary_message(
            [
                {
                    "company": "카카오뱅크",
                    "title": "AI 서비스 품질 및 안전성 평가 담당자",
                    "score": 92,
                    "url": "https://example.com/high",
                    "reason": "평가와 안전성 키워드가 강하게 맞습니다.",
                },
                {
                    "company": "현대오토에버",
                    "title": "QA Engineer - 생성형 AI Service",
                    "score": 73,
                    "url": "https://example.com/review",
                    "reason": "생성형 AI 품질 역할과 맞닿아 있습니다.",
                },
            ],
            high_fit_score=85,
            date_label="2026-06-21",
        )
        self.assertIn("고적합", message)
        self.assertIn("추가 검토", message)
        self.assertIn("카카오뱅크", message)
        self.assertIn("현대오토에버", message)

    def test_is_closed_job_detects_explicit_closed_marker(self) -> None:
        job = JobPosting(
            source="kakaobank",
            url="https://example.com/job",
            raw_card_text="AI 품질 및 안전성 평가 담당자 마감 AI ~ 2026.05.28",
            title="AI 품질 및 안전성 평가 담당자 마감 AI ~ 2026.05.28",
            company="카카오뱅크",
        )
        self.assertTrue(is_closed_job(job))

    def test_is_closed_job_keeps_open_ended_hiring_open(self) -> None:
        job = JobPosting(
            source="kakao",
            url="https://example.com/job",
            raw_card_text="LLM Research Engineer 영입마감일 영입종료시",
            title="LLM Research Engineer",
            company="카카오",
            card_meta="영입마감일 영입종료시",
        )
        self.assertFalse(is_closed_job(job))

    def test_handle_immediate_alerts_can_ignore_seen_state(self) -> None:
        match = type(
            "Match",
            (),
            {
                "total_score": 91,
                "to_record": lambda self: {
                    "job_key": "kakaobank:https://example.com/1",
                    "company": "카카오뱅크",
                    "title": "AI 서비스 품질 및 안전성 평가 담당자",
                    "score": 91,
                    "url": "https://example.com/1",
                    "reason": "테스트",
                },
            },
        )()

        with TemporaryDirectory() as tmp_dir:
            from jobs.ai_quality_monitor import StateBackend

            backend = StateBackend(local_path=Path(tmp_dir) / "state.json")
            backend.put("ai-quality/high-fit-seen", ["kakaobank:https://example.com/old"])
            records = handle_immediate_alerts(
                [match],
                backend=backend,
                high_fit_score=85,
                notify_limit=5,
                ignore_seen=True,
            )
            saved_seen = backend.get("ai-quality/high-fit-seen", [])
            self.assertEqual(1, len(records))
            self.assertNotIn("kakaobank:https://example.com/1", saved_seen)

            from jobs import ai_quality_monitor

            ai_quality_monitor.mark_records_seen(records, backend=backend)
            saved_seen = backend.get("ai-quality/high-fit-seen", [])
            self.assertIn("kakaobank:https://example.com/1", saved_seen)

    def test_send_message_if_available_does_not_raise_on_telegram_failure(self) -> None:
        from jobs import ai_quality_monitor

        calls = []

        def fake_send_telegram(message: str, fail_on_error: bool = True):
            calls.append((message, fail_on_error))
            return False

        original = ai_quality_monitor.send_telegram
        ai_quality_monitor.send_telegram = fake_send_telegram
        try:
            sent = send_message_if_available("테스트 메시지")
        finally:
            ai_quality_monitor.send_telegram = original

        self.assertIs(sent, False)
        self.assertEqual([("테스트 메시지", False)], calls)

    def test_collect_unique_anchor_jobs_skips_broken_card(self) -> None:
        from jobs.ai_quality_monitor import collect_unique_anchor_jobs

        class FakeAnchors:
            @staticmethod
            def count() -> int:
                return 2

        class FakePage:
            @staticmethod
            def locator(_selector):
                return FakeAnchors()

        def builder(_page, idx):
            if idx == 0:
                raise ValueError("깨진 카드")
            return JobPosting(
                source="test",
                url="https://example.com/good",
                raw_card_text="AI Builder",
                title="AI Builder",
            )

        jobs = collect_unique_anchor_jobs(FakePage(), "a", 5, builder)

        self.assertEqual(["AI Builder"], [job.title for job in jobs])

    def test_summary_state_is_finalized_only_after_delivery(self) -> None:
        from jobs import ai_quality_monitor

        delivered_record = {
            "job_key": "kakao:https://example.com/high",
            "company": "카카오",
            "title": "AI Builder",
            "score": 90,
            "url": "https://example.com/high",
        }
        pending_record = {
            "job_key": "naver:https://example.com/pending",
            "company": "NAVER",
            "title": "LLM Evaluation Engineer",
            "score": 80,
            "url": "https://example.com/pending",
        }
        with TemporaryDirectory() as tmp_dir:
            backend = ai_quality_monitor.StateBackend(
                local_path=Path(tmp_dir) / "state.json"
            )
            backend.put(
                ai_quality_monitor.summary_key_for("2026-07-16"),
                [delivered_record, pending_record],
            )

            selected = ai_quality_monitor.drain_summary_candidates(
                [],
                backend=backend,
                summary_score=60,
                high_fit_score=65,
                summary_limit=1,
                date_label="2026-07-16",
            )

            self.assertEqual([delivered_record], selected)
            self.assertEqual(
                [delivered_record, pending_record],
                backend.get(ai_quality_monitor.summary_key_for("2026-07-16"), []),
            )

            ai_quality_monitor.finalize_summary_delivery(
                selected,
                backend=backend,
                date_label="2026-07-16",
            )

            self.assertIn(
                delivered_record["job_key"],
                backend.get("ai-quality/high-fit-seen", []),
            )
            self.assertEqual(
                [pending_record],
                backend.get(ai_quality_monitor.summary_key_for("2026-07-16"), []),
            )


if __name__ == "__main__":
    unittest.main()
