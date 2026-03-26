#!/usr/bin/env python3
from __future__ import annotations

"""텔레그램 발송/수신 메모리 저장 및 로컬 RAG 검색"""

import hashlib
import json
import os
import re
import sqlite3
import tempfile
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from runtime import get_required_env, request_json

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - 로컬 의존성 없을 때 fallback 허용
    OpenAI = None

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - 로컬 의존성 없을 때 fallback 허용
    PdfReader = None

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
MEMORY_DIR = ROOT_DIR / "data" / "telegram_memory"
OUTBOX_DIR = MEMORY_DIR / "outbox"
INBOX_DIR = MEMORY_DIR / "inbox"
RAW_UPDATE_DIR = INBOX_DIR / "raw"
NOTE_DIR = INBOX_DIR / "notes"
FILE_DIR = INBOX_DIR / "files"
TEXT_DIR = INBOX_DIR / "text"
SUMMARY_DIR = MEMORY_DIR / "summaries"
INDEX_DB_PATH = MEMORY_DIR / "index.db"
KST = timezone(timedelta(hours=9))
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".log"}
HTML_EXTENSIONS = {".html", ".htm"}
JSON_EXTENSIONS = {".json"}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
SUPPORTED_UPLOAD_EXTENSIONS = (
    TEXT_EXTENSIONS | HTML_EXTENSIONS | JSON_EXTENSIONS | PDF_EXTENSIONS | DOCX_EXTENSIONS
)


class TextExtractor(HTMLParser):
    """HTML에서 텍스트만 추출"""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str):
        cleaned = data.strip()
        if cleaned:
            self.parts.append(cleaned)

    def get_text(self) -> str:
        return " ".join(self.parts)


def ensure_dirs() -> None:
    for path in [
        MEMORY_DIR,
        OUTBOX_DIR,
        RAW_UPDATE_DIR,
        NOTE_DIR,
        FILE_DIR,
        TEXT_DIR,
        SUMMARY_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def now_kst() -> datetime:
    return datetime.now(KST)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def html_to_text(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value or "")
    return parser.get_text()


def sanitize_filename(name: str, fallback: str = "file") -> str:
    sanitized = re.sub(r"[^0-9A-Za-z가-힣._-]+", "-", (name or "").strip()).strip("-")
    return sanitized or fallback


def collapse_text(text: str, limit: int = 240) -> str:
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def build_doc_id(prefix: str, payload: str) -> str:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    ensure_dirs()
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def db_connect() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(INDEX_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS docs (
            doc_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            path TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts
        USING fts5(
            doc_id UNINDEXED,
            title,
            body,
            tokenize='unicode61'
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_docs_created_at ON docs(created_at)"
    )
    return conn


def upsert_document(
    *,
    doc_id: str,
    kind: str,
    source: str,
    title: str,
    body: str,
    path: str = "",
    created_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    conn = db_connect()
    created_at = created_at or utc_now_iso()
    metadata_json = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
    with conn:
        conn.execute(
            """
            INSERT INTO docs (doc_id, kind, source, title, body, path, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                kind=excluded.kind,
                source=excluded.source,
                title=excluded.title,
                body=excluded.body,
                path=excluded.path,
                created_at=excluded.created_at,
                metadata_json=excluded.metadata_json
            """,
            (doc_id, kind, source, title, body, path, created_at, metadata_json),
        )
        conn.execute("DELETE FROM docs_fts WHERE doc_id = ?", (doc_id,))
        conn.execute(
            "INSERT INTO docs_fts (doc_id, title, body) VALUES (?, ?, ?)",
            (doc_id, title, body),
        )
    conn.close()


def build_fts_query(query: str) -> str:
    terms = re.findall(r"[0-9A-Za-z가-힣_]+", query or "")
    if not terms:
        return f'"{query.strip().replace(chr(34), " ")}"'
    unique_terms = []
    for term in terms:
        if term not in unique_terms:
            unique_terms.append(term)
    return " OR ".join(f'"{term}"*' for term in unique_terms[:8])


def search_documents(query: str, limit: int = 8) -> list[dict[str, Any]]:
    if not INDEX_DB_PATH.exists():
        return []

    fts_query = build_fts_query(query)
    conn = db_connect()
    try:
        rows = conn.execute(
            """
            SELECT
                d.doc_id,
                d.kind,
                d.source,
                d.title,
                d.body,
                d.path,
                d.created_at,
                d.metadata_json,
                bm25(docs_fts) AS score
            FROM docs_fts
            JOIN docs d ON d.doc_id = docs_fts.doc_id
            WHERE docs_fts MATCH ?
            ORDER BY score ASC, d.created_at DESC
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []
    conn.close()

    results = []
    for row in rows:
        results.append({
            "doc_id": row["doc_id"],
            "kind": row["kind"],
            "source": row["source"],
            "title": row["title"],
            "body": row["body"],
            "path": row["path"],
            "created_at": row["created_at"],
            "score": row["score"],
            "metadata": json.loads(row["metadata_json"] or "{}"),
        })
    return results


def build_query_context(results: list[dict[str, Any]], limit_chars: int = 5000) -> str:
    chunks = []
    total = 0
    for index, item in enumerate(results, start=1):
        excerpt = collapse_text(item["body"], limit=700)
        chunk = (
            f"[{index}] 제목: {item['title']}\n"
            f"출처: {item['source']} | 종류: {item['kind']} | 시각: {item['created_at']}\n"
            f"경로: {item['path']}\n"
            f"내용: {excerpt}"
        )
        if total + len(chunk) > limit_chars:
            break
        chunks.append(chunk)
        total += len(chunk)
    return "\n\n".join(chunks)


def answer_query(query: str, *, limit: int = 8) -> tuple[str, list[dict[str, Any]]]:
    results = search_documents(query, limit=limit)
    if not results:
        return "저장된 메모/자료에서 관련 내용을 찾지 못했습니다.", []

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or OpenAI is None:
        lines = ["관련 메모를 찾았습니다.\n"]
        for item in results[:5]:
            lines.append(f"- {item['title']}: {collapse_text(item['body'], 120)}")
        return "\n".join(lines), results

    client = OpenAI(api_key=api_key)
    model = os.environ.get("TELEGRAM_MEMORY_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    context = build_query_context(results)
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "너는 사용자의 개인 비서처럼 동작하는 텔레그램 메모리 도우미다. "
                    "항상 한국어로 답하고, 말투는 자연스럽고 부드럽되 과하게 장황하지 마라. "
                    "반드시 제공된 메모/문서 내용만 근거로 답하고, 모르면 추측하지 말고 부족한 점을 분명히 말해라. "
                    "답변은 가능하면 다음 순서를 따른다: "
                    "1) 한두 문장으로 바로 결론, "
                    "2) 필요하면 핵심 bullet 2~4개, "
                    "3) 사용자가 바로 이어서 할 만한 다음 행동이나 체크 포인트 1개. "
                    "사용자의 관심사, 반복되는 맥락, 최근 대화 흐름이 보이면 비서처럼 연결해서 설명하되 "
                    "근거 없는 기억을 만들어내지 마라."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"질문: {query}\n\n"
                    f"검색 결과:\n{context}\n\n"
                    "답변 뒤에는 반드시 '근거:' 섹션을 만들고, 참고한 제목을 bullet로 덧붙여라."
                ),
            },
        ],
    )
    answer = response.choices[0].message.content or "답변을 생성하지 못했습니다."
    return answer.strip(), results


def get_bridge_url() -> str:
    return os.environ.get("TELEGRAM_MEMORY_BRIDGE_URL", "").strip().rstrip("/")


def get_bridge_token() -> str:
    return os.environ.get("TELEGRAM_MEMORY_BRIDGE_TOKEN", "").strip()


def bridge_is_configured() -> bool:
    return bool(get_bridge_url() and get_bridge_token())


def send_bridge_log(payload: dict[str, Any]) -> bool:
    bridge_url = get_bridge_url()
    bridge_token = get_bridge_token()
    if not bridge_url or not bridge_token:
        return False

    request_json(
        f"{bridge_url}/log",
        method="POST",
        timeout=20,
        label="Telegram memory bridge write",
        headers={
            "Authorization": f"Bearer {bridge_token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )
    return True


def log_outgoing_message_to_bridge(
    source: str,
    message: str,
    *,
    parse_mode: str = "HTML",
) -> bool:
    timestamp = now_kst()
    return send_bridge_log({
        "kind": "outbox",
        "date": timestamp.strftime("%Y-%m-%d"),
        "sent_at": timestamp.isoformat(),
        "source": source,
        "parse_mode": parse_mode,
        "message": message,
    })


def log_outgoing_message(source: str, message: str, *, parse_mode: str = "HTML") -> None:
    ensure_dirs()
    timestamp = now_kst()
    payload = f"{timestamp.isoformat()}::{source}::{message}"
    doc_id = build_doc_id("outbox", payload)
    row = {
        "doc_id": doc_id,
        "sent_at": timestamp.isoformat(),
        "source": source,
        "parse_mode": parse_mode,
        "message": message,
    }
    path = OUTBOX_DIR / f"{timestamp.strftime('%Y-%m-%d')}.jsonl"
    append_jsonl(path, row)
    plain_text = html_to_text(message) if parse_mode.upper() == "HTML" else message
    first_line = next((line.strip() for line in plain_text.splitlines() if line.strip()), "Telegram alert")
    upsert_document(
        doc_id=doc_id,
        kind="telegram_outbox",
        source=source,
        title=collapse_text(first_line, 100),
        body=plain_text,
        path=str(path.relative_to(ROOT_DIR)),
        created_at=timestamp.isoformat(),
        metadata={"parse_mode": parse_mode},
    )


def store_raw_update(update: dict[str, Any]) -> str:
    ensure_dirs()
    timestamp = now_kst()
    payload = json.dumps(update, ensure_ascii=False, sort_keys=True)
    doc_id = build_doc_id("update", payload)
    path = RAW_UPDATE_DIR / f"{timestamp.strftime('%Y-%m-%d')}.jsonl"
    append_jsonl(path, {
        "doc_id": doc_id,
        "received_at": timestamp.isoformat(),
        "update": update,
    })
    return doc_id


def store_text_note(
    *,
    source: str,
    title: str,
    text: str,
    chat_id: int | str,
    message_id: int | str,
    created_at: str | None = None,
) -> dict[str, str]:
    ensure_dirs()
    timestamp = datetime.fromisoformat(created_at) if created_at else now_kst()
    safe_title = sanitize_filename(title, fallback="note")
    filename = f"{timestamp.strftime('%Y%m%d-%H%M%S')}-{chat_id}-{message_id}-{safe_title}.md"
    path = NOTE_DIR / filename
    markdown = f"# {title}\n\n{text.strip()}\n"
    path.write_text(markdown, encoding="utf-8")

    body = text.strip()
    doc_id = build_doc_id("note", f"{chat_id}:{message_id}:{body}")
    upsert_document(
        doc_id=doc_id,
        kind="telegram_note",
        source=source,
        title=title,
        body=body,
        path=str(path.relative_to(ROOT_DIR)),
        created_at=timestamp.isoformat(),
        metadata={"chat_id": str(chat_id), "message_id": str(message_id)},
    )
    return {"doc_id": doc_id, "path": str(path.relative_to(ROOT_DIR))}


def extract_text_from_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix in HTML_EXTENSIONS:
        return html_to_text(path.read_text(encoding="utf-8", errors="ignore"))
    if suffix in JSON_EXTENSIONS:
        raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return json.dumps(raw, ensure_ascii=False, indent=2)
    if suffix in PDF_EXTENSIONS:
        if PdfReader is None:
            raise RuntimeError("pypdf가 설치되어 있지 않아 PDF 텍스트 추출을 할 수 없습니다.")
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n\n".join(pages).strip()
    if suffix in DOCX_EXTENSIONS:
        with zipfile.ZipFile(path) as archive:
            xml_text = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        return html_to_text(xml_text)
    raise RuntimeError(f"지원하지 않는 파일 형식입니다: {suffix}")


def store_document_file(
    *,
    source: str,
    original_name: str,
    content: bytes,
    extracted_text: str,
    chat_id: int | str,
    message_id: int | str,
    caption: str = "",
    created_at: str | None = None,
) -> dict[str, str]:
    ensure_dirs()
    timestamp = datetime.fromisoformat(created_at) if created_at else now_kst()
    safe_name = sanitize_filename(original_name, fallback="document")
    stored_name = f"{timestamp.strftime('%Y%m%d-%H%M%S')}-{chat_id}-{message_id}-{safe_name}"
    file_path = FILE_DIR / stored_name
    file_path.write_bytes(content)

    text_title = Path(original_name).name or "첨부 문서"
    body_parts = []
    if caption.strip():
        body_parts.append(f"[캡션]\n{caption.strip()}")
    body_parts.append(extracted_text.strip())
    body = "\n\n".join(part for part in body_parts if part).strip()

    text_path = TEXT_DIR / f"{stored_name}.md"
    text_path.write_text(f"# {text_title}\n\n{body}\n", encoding="utf-8")

    doc_id = build_doc_id("file", f"{chat_id}:{message_id}:{original_name}:{hashlib.sha256(content).hexdigest()}")
    upsert_document(
        doc_id=doc_id,
        kind="telegram_file",
        source=source,
        title=text_title,
        body=body,
        path=str(text_path.relative_to(ROOT_DIR)),
        created_at=timestamp.isoformat(),
        metadata={
            "chat_id": str(chat_id),
            "message_id": str(message_id),
            "original_file_path": str(file_path.relative_to(ROOT_DIR)),
            "original_name": original_name,
        },
    )
    return {
        "doc_id": doc_id,
        "file_path": str(file_path.relative_to(ROOT_DIR)),
        "text_path": str(text_path.relative_to(ROOT_DIR)),
    }


def collect_outbox_rows(target_date: date) -> list[dict[str, Any]]:
    path = OUTBOX_DIR / f"{target_date.strftime('%Y-%m-%d')}.jsonl"
    if not path.exists():
        return []

    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def fetch_bridge_logs(kind: str, target_date: date) -> list[dict[str, Any]]:
    bridge_url = get_bridge_url()
    bridge_token = get_bridge_token()
    if not bridge_url or not bridge_token:
        if kind == "outbox":
            return collect_outbox_rows(target_date)
        return []

    query = urllib.parse.urlencode({
        "kind": kind,
        "date": target_date.isoformat(),
    })
    response = request_json(
        f"{bridge_url}/logs?{query}",
        timeout=20,
        label=f"Telegram memory bridge read [{kind}]",
        headers={"Authorization": f"Bearer {bridge_token}"},
    )
    if not isinstance(response, dict):
        return []
    logs = response.get("logs") or []
    return [row for row in logs if isinstance(row, dict)]


def collapse_outbox_message(row: dict[str, Any], limit: int = 180) -> str:
    message = str(row.get("message", ""))
    parse_mode = str(row.get("parse_mode", "")).upper()
    plain_text = html_to_text(message) if parse_mode == "HTML" else message
    return collapse_text(plain_text, limit)


def fallback_daily_summary(
    target_date: date,
    inbox_rows: list[dict[str, Any]],
    outbox_rows: list[dict[str, Any]],
) -> str:
    grouped: dict[str, list[str]] = {}
    for row in outbox_rows:
        grouped.setdefault(row.get("source", "unknown"), []).append(
            collapse_outbox_message(row, 180)
        )

    lines = [
        f"# Telegram Memory Summary - {target_date.isoformat()}",
        "",
        f"- 사용자 대화 로그: {len(inbox_rows)}건",
        f"- 자동화 발송 로그: {len(outbox_rows)}건",
        "",
        "## 오늘의 대화 요약",
        "",
    ]
    if inbox_rows:
        for row in inbox_rows[:8]:
            lines.append(f"- {collapse_text(str(row.get('text', '')), 180)}")
    else:
        lines.append("- 저장된 사용자 대화 로그가 없습니다.")
    lines.extend(["", "## 오늘의 자동화 알림 요약", ""])

    if not grouped:
        lines.append("- 저장된 자동화 알림 로그가 없습니다.")
        return "\n".join(lines).rstrip() + "\n"

    for source, messages in sorted(grouped.items()):
        lines.append(f"### {source}")
        lines.append("")
        lines.append(f"- 발송 건수: {len(messages)}")
        for message in messages[:5]:
            lines.append(f"- {message}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def summarize_daily_rows(
    target_date: date,
    inbox_rows: list[dict[str, Any]],
    outbox_rows: list[dict[str, Any]],
) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or OpenAI is None:
        return fallback_daily_summary(target_date, inbox_rows, outbox_rows)

    client = OpenAI(api_key=api_key)
    model = os.environ.get("TELEGRAM_MEMORY_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

    inbox_payload_lines = []
    for row in inbox_rows[:60]:
        inbox_payload_lines.append(
            f"[{row.get('received_at', '')}] {collapse_text(str(row.get('text', '')), 220)}"
        )

    outbox_payload_lines = []
    for row in outbox_rows[:80]:
        outbox_payload_lines.append(
            f"[{row.get('sent_at','')}] ({row.get('source','unknown')}) "
            f"{collapse_outbox_message(row, 300)}"
        )

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "너는 사용자의 하루를 정리해 주는 개인 비서다. "
                    "하루치 텔레그램 대화와 자동화 알림 로그를 보고, 나중에 다시 찾아보기 쉬운 한국어 마크다운 일일 메모를 만든다. "
                    "형식은 다음 순서를 지켜라: "
                    "1) 제목, "
                    "2) 오늘의 핵심 요약 bullet, "
                    "3) 사용자가 오늘 관심 보인 주제, "
                    "4) 오늘의 자동화 알림 요약, "
                    "5) 나중에 기억할 메모/할 일. "
                    "반복된 관심사, 투자 관점의 체크 포인트, 후속 행동이 보이면 짧게 정리하되 과장하거나 추측하지 마라."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"날짜: {target_date.isoformat()}\n"
                    f"사용자 대화 로그 수: {len(inbox_rows)}\n"
                    f"자동화 발송 로그 수: {len(outbox_rows)}\n\n"
                    "사용자 대화 로그:\n"
                    + ("\n".join(inbox_payload_lines) or "(없음)")
                    + "\n\n자동화 발송 로그:\n"
                    + ("\n".join(outbox_payload_lines) or "(없음)")
                ),
            },
        ],
    )
    return (response.choices[0].message.content or "").strip() + "\n"


def save_daily_memory_summary(target_date: date) -> dict[str, str] | None:
    inbox_rows = fetch_bridge_logs("inbox", target_date)
    outbox_rows = fetch_bridge_logs("outbox", target_date)
    if not inbox_rows and not outbox_rows:
        return None

    summary_markdown = summarize_daily_rows(target_date, inbox_rows, outbox_rows)
    path = SUMMARY_DIR / f"{target_date.isoformat()}.md"
    path.write_text(summary_markdown, encoding="utf-8")

    doc_id = f"summary:{target_date.isoformat()}"
    upsert_document(
        doc_id=doc_id,
        kind="telegram_daily_summary",
        source="telegram-memory",
        title=f"Telegram Memory Summary {target_date.isoformat()}",
        body=summary_markdown,
        path=str(path.relative_to(ROOT_DIR)),
        created_at=datetime.combine(target_date, datetime.min.time(), tzinfo=KST).isoformat(),
        metadata={
            "date": target_date.isoformat(),
            "inbox_count": len(inbox_rows),
            "outbox_count": len(outbox_rows),
        },
    )
    return {"doc_id": doc_id, "path": str(path.relative_to(ROOT_DIR))}


def save_daily_outbox_summary(target_date: date) -> dict[str, str] | None:
    """이전 함수명 호환용 래퍼"""
    return save_daily_memory_summary(target_date)


def telegram_api(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = get_required_env("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return request_json(
        url,
        method="POST",
        data=data,
        timeout=30,
        label=f"Telegram API [{method}]",
        headers={"Content-Type": "application/json"},
    )


def send_telegram_message(chat_id: int | str, text: str) -> None:
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": text[:4000],
        "disable_web_page_preview": True,
    })


def get_telegram_file_bytes(file_id: str) -> bytes:
    token = get_required_env("TELEGRAM_BOT_TOKEN")
    result = telegram_api("getFile", {"file_id": file_id})
    file_path = result["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    with urllib.request.urlopen(download_url, timeout=60) as response:
        return response.read()


def save_temp_bytes(content: bytes, suffix: str) -> Path:
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp.write(content)
    temp.flush()
    temp.close()
    return Path(temp.name)
