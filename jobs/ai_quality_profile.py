from __future__ import annotations

from dataclasses import asdict

from .profile import CANDIDATE, CandidateProfile


AI_QUALITY_SEED_ROLES = (
    {
        "company": "카카오뱅크",
        "title": "AI 서비스 품질 및 안전성 평가 담당자",
        "url": "https://recruit.kakaobank.com/jobs/257564?recruitClassNames=AI",
        "keywords": (
            "ai 서비스 품질",
            "안전성 평가",
            "ai quality",
            "safety evaluation",
            "llm evaluation",
        ),
    },
    {
        "company": "LG CNS",
        "title": "품질관리자 모집 / AI 품질 엔지니어",
        "url": "https://careers.lg.com/apply/detail?id=1001561",
        "keywords": (
            "ai 품질 엔지니어",
            "품질관리자",
            "테스트 엔지니어",
            "서비스 품질",
            "ai quality engineer",
        ),
    },
    {
        "company": "Generic",
        "title": "AI Builder / Forward Deployed Engineer",
        "url": "https://example.com/ai-builder-reference",
        "keywords": (
            "ai builder",
            "forward deployed",
            "forward developer",
            "developer productivity",
            "agent platform",
        ),
    },
)


def _merge_weights(*maps: dict[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for mapping in maps:
        for key, value in mapping.items():
            merged[key] = value
    return merged


AI_QUALITY_CANDIDATE = CandidateProfile(
    name=CANDIDATE.name,
    headline=(
        "실서비스 LLM·RAG 시스템을 운영하면서 응답 품질 평가 자동화, "
        "피드백 반영, 안전한 서비스 품질 개선과 AI Builder 성격의 구축 경험을 함께 쌓아온 AI Engineer."
    ),
    strengths=(
        "실서비스 AI 응답 품질 개선과 사용자 피드백 반영 경험",
        "RAG·LLM·에이전트 시스템의 평가 자동화 설계 경험",
        "기업용 AI 에이전트와 개발자 생산성 도구를 직접 설계·구축한 경험",
        "기업용 AI 서비스의 운영 품질, 로그, 접근 제어 설계 경험",
        "실험 설계와 정량 평가를 바탕으로 한 품질 개선 경험",
        "여러 조직과 협업하며 서비스 기준과 운영 체계를 만든 경험",
    ),
    positive_keywords=_merge_weights(
        CANDIDATE.positive_keywords,
        {
            "quality": 9,
            "품질": 9,
            "evaluation": 10,
            "eval": 10,
            "평가": 10,
            "safety": 11,
            "안전성": 11,
            "trust": 7,
            "responsible ai": 10,
            "red team": 9,
            "red teaming": 9,
            "benchmark": 7,
            "judge": 6,
            "judgment": 6,
            "qa": 6,
            "testing": 5,
            "test": 4,
            "validation": 7,
            "alignment": 7,
            "prompt evaluation": 9,
            "model evaluation": 10,
            "서비스 품질": 10,
            "품질 평가": 10,
            "feedback": 7,
            "human feedback": 8,
            "ai builder": 10,
            "agent builder": 9,
            "forward deployed": 10,
            "forward developer": 10,
            "developer productivity": 11,
            "solution engineer": 8,
            "customer engineer": 8,
            "implementation": 6,
            "prototype": 5,
            "productionize": 8,
            "ship": 4,
        },
    ),
    negative_keywords=_merge_weights(
        CANDIDATE.negative_keywords,
        {
            "품질보증": -11,
            "quality control": -11,
            "quality assurance ": -6,
            "협력사": -8,
            "공정": -10,
            "출하": -10,
            "생산": -10,
            "manufacturing": -10,
            "supplier": -8,
            "inspection": -8,
            "audit": -7,
            "회계": -8,
            "영업": -8,
        },
    ),
    projects=CANDIDATE.projects,
)


def candidate_profile_to_dict(profile: CandidateProfile = AI_QUALITY_CANDIDATE) -> dict:
    return asdict(profile)
