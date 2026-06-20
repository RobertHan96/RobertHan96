import unittest

from jobs.ai_quality_monitor import (
    build_daily_summary_message,
    extract_naver_anno_id,
    merge_summary_records,
    score_role_relevance,
)


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

    def test_extract_naver_anno_id_recovers_numeric_id(self) -> None:
        self.assertEqual("30004975", extract_naver_anno_id("show('30004975')"))

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


if __name__ == "__main__":
    unittest.main()
