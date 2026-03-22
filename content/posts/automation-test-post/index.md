---
title: "GitHub Actions 기반 개인 자동화 시스템 구축기"
date: 2026-03-22
draft: false
tags: ["GitHub Actions", "자동화", "Todoist", "Dev.to", "Telegram"]
categories: ["AI Engineering"]
summary: "GitHub Actions와 Telegram을 활용해 주식 알림, 기술 뉴스, 할일 관리, 블로그 크로스포스팅까지 8가지 자동화 태스크를 구축한 경험을 공유합니다."
cover:
  image: ""
  alt: "자동화 시스템 아키텍처"
  hidden: false
ShowToc: true
TocOpen: true
---

## 배경

매일 반복하는 루틴 — 뉴스 확인, 주가 체크, 일정 관리 — 을 자동화하고 싶었습니다.
별도 서버 없이 GitHub Actions의 스케줄 기능만으로 8가지 자동화 태스크를 구현했습니다.

## 자동화 태스크 목록

| # | 태스크 | 스케줄 | 핵심 기술 |
|---|--------|--------|-----------|
| 1 | 관심 종목 뉴스 모니터링 | 매일 08:00 | RSS + 키워드 필터링 |
| 2 | 종목 가격 변동 알림 | 매 시간 | yfinance API |
| 3 | 기술 뉴스 브리핑 | 매일 08:00 | GeekNews RSS + OpenAI 요약 |
| 4 | Jira 릴리즈 일정 | 평일 09:00 | Jira REST API |
| 5 | 오늘의 할일 알림 | 평일 08:30 | Todoist REST API v2 |
| 6 | 생일 알림 | 매일 08:00 | YAML 데이터 |
| 7 | 채용공고 모니터링 | 매일 09:00 | 웹 스크래핑 |
| 8 | 블로그 크로스포스팅 | 매주 월요일 | Dev.to API |

## 아키텍처

```
GitHub Actions (cron) → Python 스크립트 → 외부 API 호출 → Telegram Bot 발송
```

모든 태스크가 동일한 패턴을 따릅니다:
1. 스케줄에 따라 GitHub Actions가 트리거
2. Python 스크립트가 외부 데이터 수집
3. 필요시 AI 요약 (OpenAI GPT)
4. Telegram으로 결과 발송

## 서비스 선택 기준

### Todoist (캘린더 대체)
- Google Calendar API는 OAuth2가 필요해 GitHub Actions에서 토큰 갱신이 번거로움
- Todoist는 설정에서 API 토큰을 바로 발급받을 수 있어 연동이 간단
- 모바일 앱이 우수하고 무료 플랜으로 충분

### Dev.to (블로그 크로스포스팅)
- Medium API가 2024년부터 OAuth 토큰 발급을 중단
- Dev.to는 API 키 방식으로 간편하고, Markdown 네이티브 지원
- 높은 도메인 권위로 Google SEO에 유리
- canonical URL 설정으로 Hugo 블로그 원본 인정

## 핵심 코드

### Todoist 당일 태스크 조회

```python
def get_today_tasks() -> list[dict]:
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    filter_param = urllib.parse.quote(f"due: {today_str}")
    tasks = todoist_get(f"tasks?filter={filter_param}")
    return sorted(tasks, key=lambda x: x["priority"], reverse=True)
```

### Dev.to 크로스포스팅

```python
def post_to_devto(title, body, tags, canonical_url=""):
    article_data = {
        "article": {
            "title": title,
            "body_markdown": body,
            "published": False,  # draft
            "tags": tags[:4],
            "canonical_url": canonical_url,
        }
    }
    # Dev.to API 호출
```

## 비용

- 전부 무료: GitHub Actions (월 2,000분), Telegram Bot, Todoist 무료 플랜, Dev.to

## 마무리

서버 없이 GitHub Actions만으로 충분한 수준의 개인 자동화가 가능합니다.
핵심은 OAuth2 같은 복잡한 인증 대신 API 키 방식의 서비스를 선택하는 것이었습니다.
