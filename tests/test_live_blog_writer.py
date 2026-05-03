import unittest

from scripts.automation.live_blog_writer import render_hugo_draft


class LiveBlogWriterTests(unittest.TestCase):
    def test_render_hugo_draft_includes_front_matter_and_sections(self) -> None:
        markdown = render_hugo_draft(
            slug="sample-live-post",
            title="샘플 방송 정리",
            summary="샘플 요약",
            tags=["AI", "Python"],
            sections={
                "배경": "배경 내용",
                "구현 흐름": "흐름 내용",
                "막힌 점": "막힌 점 내용",
            },
        )
        self.assertIn('title: "샘플 방송 정리"', markdown)
        self.assertIn("draft: true", markdown)
        self.assertIn("## 배경", markdown)
        self.assertIn("배경 내용", markdown)


if __name__ == "__main__":
    unittest.main()
