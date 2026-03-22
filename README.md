학습을 즐기고, 항상 목표 달성을 위해 나아가는 개발자 한영신 입니다.   
즐거운 👩‍💻   을 위해 긍정적으로 생각하고, 새로운 것을 배우는 것 또한 좋아합니다.   
자세한 내용은 각 페이지에서 확인 해주세요!

*** 

### 🎫   [자기소개와 이력서](https://github.com/RobertHan96/RobertHan96/blob/main/resume.md)

*** 

### 💼 [포트폴리오](https://github.com/RobertHan96/RobertHan96/blob/main/portfolio.pdf)

*** 

### ✍️ 블로그 작성 가이드

이제 Hugo 포스트는 로컬에서 파일을 만들고 `git push`하지 않아도 됩니다.  
GitHub의 `Issues`에서 `블로그 글 작성` 폼을 열어 내용만 작성하면, GitHub Actions가 자동으로 `content/posts/<slug>/index.md` 파일을 만들고 커밋한 뒤 배포까지 연결합니다.

#### 가장 쉬운 방법: Issue Form으로 작성

1. GitHub 저장소의 `Issues` 탭으로 이동합니다.
2. `New issue`에서 `블로그 글 작성` 템플릿을 선택합니다.
3. 아래 항목을 입력합니다.
   - 글 제목
   - 슬러그(선택)
   - 한 줄 요약
   - 태그
   - 카테고리
   - 발행 방식: `초안으로 저장` 또는 `즉시 발행`
   - 본문(Markdown)
4. 이슈를 등록하면 GitHub Actions가 자동으로 포스트를 생성합니다.
5. 처리 결과는 해당 이슈 댓글로 안내됩니다.

#### 동작 방식

- `초안으로 저장`을 선택하면 `draft: true`로 생성됩니다.
- `즉시 발행`을 선택하면 `draft: false`로 생성되어 배포됩니다.
- 같은 이슈를 수정하면 기존 포스트가 다시 갱신됩니다.
- 제목이나 슬러그를 바꾸면 포스트 폴더도 함께 이동됩니다.
- 공개 저장소이지만 실제 포스트 생성은 `OWNER`, `MEMBER`, `COLLABORATOR` 권한이 있는 작성자만 실행됩니다.

#### 예전 방식도 가능

필요하면 기존처럼 로컬에서 직접 포스트를 작성하거나, `scripts/publish.py`를 사용해 Confluence 문서를 Hugo 포스트 초안으로 변환할 수도 있습니다.  
다만 평소에는 Issue Form 방식이 가장 빠르고 편합니다.
