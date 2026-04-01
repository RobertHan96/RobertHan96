from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProjectProfile:
    name: str
    summary: str
    keywords: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class CandidateProfile:
    name: str
    headline: str
    strengths: tuple[str, ...]
    positive_keywords: dict[str, int]
    negative_keywords: dict[str, int]
    projects: tuple[ProjectProfile, ...] = field(default_factory=tuple)


CANDIDATE = CandidateProfile(
    name="한영신",
    headline=(
        "실무 AI 에이전트 서비스와 연구 역량을 함께 갖춘 AI Engineer. "
        "RAG, LLM, context engineering, enterprise AI, 품질 평가 자동화, "
        "온프레미스 운영 경험을 보유."
    ),
    strengths=(
        "실서비스 AI 에이전트 설계 및 운영",
        "RAG 기반 지식검색 및 맥락 설계",
        "온프레미스 LLM 및 기업용 AI 시스템 구축",
        "응답 품질 평가 자동화와 사용자 피드백 기반 개선",
        "대규모 데이터 정제와 연구 실험 설계",
        "전사 서비스 런칭과 부서 간 협업",
    ),
    positive_keywords={
        "ai": 2,
        "agent": 8,
        "에이전트": 8,
        "agentic": 8,
        "llm": 9,
        "gen ai": 9,
        "generative ai": 9,
        "생성형": 8,
        "rag": 10,
        "retrieval": 8,
        "검색": 5,
        "search": 5,
        "knowledge": 6,
        "지식": 6,
        "memory": 7,
        "long-term memory": 8,
        "prompt": 7,
        "프롬프트": 7,
        "langchain": 8,
        "langgraph": 8,
        "mcp": 9,
        "tool": 5,
        "도구": 5,
        "tool calling": 8,
        "context": 7,
        "컨텍스트": 7,
        "evaluation": 6,
        "eval": 6,
        "평가": 5,
        "품질": 4,
        "quality": 4,
        "feedback": 4,
        "python": 5,
        "backend": 4,
        "fastapi": 5,
        "vllm": 8,
        "on-prem": 8,
        "온프레미스": 8,
        "internal": 4,
        "내부망": 7,
        "enterprise": 6,
        "권한": 4,
        "로그": 4,
        "observability": 6,
        "ci/cd": 5,
        "code review": 5,
        "코드리뷰": 5,
        "data": 3,
        "데이터": 3,
        "preprocess": 4,
        "전처리": 4,
        "research": 4,
        "연구": 4,
        "summary": 4,
        "요약": 4,
        "nlp": 5,
        "serving": 4,
        "serving engineer": 7,
        "ai engineer": 8,
        "llm engineer": 9,
        "ml engineer": 6,
        "machine learning": 6,
    },
    negative_keywords={
        "영업": -5,
        "sales": -5,
        "마케팅": -4,
        "marketing": -4,
        "회계": -6,
        "accounting": -6,
        "재무": -5,
        "finance": -5,
        "인사": -6,
        "hr ": -6,
        "hrbp": -6,
        "법무": -6,
        "legal": -6,
        "간호": -8,
        "간호사": -8,
        "생산": -5,
        "품질관리": -4,
        "md": -4,
        "디자인": -5,
        "디자이너": -5,
        "cs": -4,
        "cx": -4,
        "행정": -5,
    },
    projects=(
        ProjectProfile(
            name="SOOPi 실시간 페르소나 에이전트",
            summary=(
                "RAG만으로 해결되지 않는 한계를 Long-term Memory, 도구 연계, "
                "Whisper STT, 품질 평가 자동화로 보완하며 실무 AI 에이전트를 개선."
            ),
            keywords=(
                "agent",
                "에이전트",
                "llm",
                "rag",
                "memory",
                "mcp",
                "tool",
                "prompt",
                "feedback",
                "evaluation",
                "whisper",
                "personalized",
            ),
            evidence=(
                "실시간 대화형 페르소나 에이전트 개발",
                "사용자 피드백 기반 개선 경험",
                "Long-term Memory 및 도메인 특화 RAG 설계",
            ),
        ),
        ProjectProfile(
            name="전사 통합 지식정보 시스템(KMS)",
            summary=(
                "100만 건 이상 사내 데이터를 연결해 내부망에서 동작하는 "
                "RAG 기반 지식검색 시스템과 온프레미스 vLLM 서빙 환경을 구축."
            ),
            keywords=(
                "enterprise",
                "knowledge",
                "search",
                "rag",
                "on-prem",
                "vllm",
                "internal",
                "access control",
                "security",
                "eval",
            ),
            evidence=(
                "100만 건 이상 사내 데이터 통합",
                "온프레미스 vLLM 서빙",
                "접근 제어 및 답변 평가 자동화",
            ),
        ),
        ProjectProfile(
            name="전사 AI 코드리뷰 자동화",
            summary=(
                "300명+ 개발조직이 사용하는 AI 코드리뷰 시스템을 구축하고 "
                "권한, 로그, CI/CD 연동, 운영 체계를 설계."
            ),
            keywords=(
                "automation",
                "ci/cd",
                "quality",
                "evaluation",
                "logs",
                "agent",
                "organization",
                "developer productivity",
            ),
            evidence=(
                "300명+ 개발조직 대상 서비스",
                "GitLab CI/CD 기반 자동 리뷰",
                "권한 정책 및 로그 체계 설계",
            ),
        ),
        ProjectProfile(
            name="SOOP RAG 요약 연구",
            summary=(
                "SOOP 수천만 건 채팅 데이터를 정제해 방송 요약용 RAG 파이프라인을 설계하고 "
                "품질과 효율을 함께 검증."
            ),
            keywords=(
                "research",
                "rag",
                "summary",
                "bertscore",
                "data",
                "preprocess",
                "evaluation",
                "nlp",
            ),
            evidence=(
                "수천만 건 채팅 데이터 정제",
                "BERTScore 약 8.6% 개선",
                "입력 토큰 약 84.6% 절감",
            ),
        ),
        ProjectProfile(
            name="온디바이스 번역 모델",
            summary=(
                "도메인 특화 채팅 데이터셋 구축과 모바일 실측 기반 성능 검증으로 "
                "모델 품질과 운영성을 함께 다룸."
            ),
            keywords=(
                "mobile",
                "optimization",
                "translation",
                "benchmark",
                "latency",
                "evaluation",
            ),
            evidence=(
                "모바일 5개 디바이스 실측 검증",
                "도메인 특화 데이터셋 구축",
                "논문 성과로 연결",
            ),
        ),
    ),
)
