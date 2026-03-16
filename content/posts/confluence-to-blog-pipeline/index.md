---
title: "Confluence 문서를 기술 블로그로 자동 변환하는 파이프라인 만들기"
date: 2026-03-16
draft: true
tags: ["자동화", "Python", "LLM", "Confluence", "블로그"]
categories: ["Productivity"]
summary: "사내 Confluence 기술 문서를 LLM으로 블로그 초안으로 변환하고, Hugo 블로그에 발행하는 반자동화 파이프라인을 구축한 경험을 공유합니다."
ShowToc: true
TocOpen: true
---

## 왜 만들었나

기술 블로그를 운영하고 싶었지만, 이미 사내 Confluence에 정리된 문서를 처음부터 다시 쓰기엔 시간이 부족했습니다.
그래서 Confluence → LLM 변환 → Hugo 블로그 발행까지의 반자동화 파이프라인을 만들었습니다.

## 파이프라인 구조

```
[Confluence URL + 개요] → Confluence API → LLM 변환 → 마크다운 생성 → Hugo 발행
```

## 핵심 구현

### 1. Confluence 본문 추출

```python
from atlassian import Confluence

confluence = Confluence(url='https://your-domain.atlassian.net', ...)
page = confluence.get_page_by_id(page_id, expand='body.storage')
html_content = page['body']['storage']['value']
```

### 2. LLM으로 블로그 초안 생성

```python
prompt = f"""
다음 사내 기술 문서를 외부 블로그용으로 변환해주세요.
- 사내 고유명사, 민감 정보는 제거
- 기술적 인사이트 중심으로 재구성
- Hugo 마크다운 형식(front matter 포함)으로 출력

[개요]: {overview}
[원본]: {html_content}
"""
```

### 3. Hugo 포스트로 저장

생성된 마크다운을 `content/posts/` 디렉토리에 저장하고 git push하면 GitHub Actions가 자동 빌드·배포합니다.

## 마치며

이 파이프라인 덕분에 블로그 글 하나를 작성하는 데 걸리는 시간이 크게 줄었습니다.
핵심은 LLM이 초안을 만들되, 최종 검수는 반드시 직접 하는 것입니다.
