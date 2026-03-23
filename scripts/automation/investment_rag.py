#!/usr/bin/env python3
from __future__ import annotations

"""OpenAI File Search 기반 투자자료 RAG 공통 모듈"""

import base64
import hashlib
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

try:
    from .runtime import get_required_env
except ImportError:
    from runtime import get_required_env

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RAG_DATA_DIR = ROOT_DIR / "data" / "investment_rag"
RAG_DATA_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_STORE_ID_PATH = RAG_DATA_DIR / "vector_store_id.txt"
MANIFEST_PATH = RAG_DATA_DIR / "manifest.json"
SUPPORTED_DIRECT_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".json",
    ".html",
    ".docx",
    ".pptx",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

OPENAI_API_KEY = get_required_env("OPENAI_API_KEY")
INVESTMENT_RAG_MODEL = os.environ.get("INVESTMENT_RAG_MODEL", "gpt-5-mini")
INVESTMENT_OCR_MODEL = os.environ.get("INVESTMENT_OCR_MODEL", "gpt-5-mini")
INVESTMENT_VECTOR_STORE_ID = os.environ.get("INVESTMENT_VECTOR_STORE_ID", "").strip()
INVESTMENT_VECTOR_STORE_NAME = os.environ.get(
    "INVESTMENT_VECTOR_STORE_NAME",
    "investment-rag",
)

client = OpenAI(api_key=OPENAI_API_KEY)


def model_to_dict(value: Any) -> dict:
    """OpenAI SDK 객체를 dict로 정규화"""
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return dict(value)


def load_manifest() -> dict:
    """로컬 manifest 로드"""
    if not MANIFEST_PATH.exists():
        return {"files": {}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(manifest: dict) -> None:
    """로컬 manifest 저장"""
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    """파일 해시 계산"""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_vector_store_id() -> str | None:
    """저장된 vector store id 로드"""
    if not VECTOR_STORE_ID_PATH.exists():
        return None
    value = VECTOR_STORE_ID_PATH.read_text(encoding="utf-8").strip()
    return value or None


def save_vector_store_id(vector_store_id: str) -> None:
    """vector store id 저장"""
    VECTOR_STORE_ID_PATH.write_text(vector_store_id.strip() + "\n", encoding="utf-8")


def get_vector_store(vector_store_id: str) -> dict | None:
    """vector store id 유효성 확인"""
    if not vector_store_id:
        return None
    try:
        result = client.vector_stores.retrieve(vector_store_id=vector_store_id)
        return model_to_dict(result)
    except Exception:
        return None


def find_vector_store_by_name(name: str) -> str | None:
    """이름으로 기존 vector store 탐색"""
    after = None
    while True:
        kwargs = {"limit": 100}
        if after:
            kwargs["after"] = after

        page = client.vector_stores.list(**kwargs)
        page_dict = model_to_dict(page)
        data = getattr(page, "data", None) or page_dict.get("data", [])
        if not data:
            return None

        for item in data:
            item_dict = model_to_dict(item)
            if item_dict.get("name") == name:
                return item_dict.get("id")

        has_more = getattr(page, "has_more", None)
        if has_more is None:
            has_more = page_dict.get("has_more", False)
        if not has_more:
            return None

        last_item = model_to_dict(data[-1])
        after = last_item.get("id")
        if not after:
            return None


def ensure_vector_store() -> str:
    """vector store 생성 또는 재사용"""
    for candidate in [INVESTMENT_VECTOR_STORE_ID, load_vector_store_id()]:
        if not candidate:
            continue
        if get_vector_store(candidate):
            save_vector_store_id(candidate)
            return candidate

    existing_vector_store_id = find_vector_store_by_name(INVESTMENT_VECTOR_STORE_NAME)
    if existing_vector_store_id:
        save_vector_store_id(existing_vector_store_id)
        print(f"기존 vector store 재사용: {existing_vector_store_id}")
        return existing_vector_store_id

    vector_store = client.vector_stores.create(name=INVESTMENT_VECTOR_STORE_NAME)
    save_vector_store_id(vector_store.id)
    print(f"Vector store 생성: {vector_store.id}")
    return vector_store.id


def iter_vector_store_files(vector_store_id: str):
    """vector store 내 파일 전체 순회"""
    after = None
    while True:
        kwargs = {
            "vector_store_id": vector_store_id,
            "limit": 100,
        }
        if after:
            kwargs["after"] = after

        page = client.vector_stores.files.list(**kwargs)
        page_dict = model_to_dict(page)
        data = getattr(page, "data", None) or page_dict.get("data", [])
        if not data:
            break

        for item in data:
            yield model_to_dict(item)

        has_more = getattr(page, "has_more", None)
        if has_more is None:
            has_more = page_dict.get("has_more", False)
        if not has_more:
            break

        last_item = model_to_dict(data[-1])
        after = last_item.get("id")
        if not after:
            break


def find_existing_remote_file(vector_store_id: str, relative_key: str) -> dict | None:
    """속성값 relative_key 기준 기존 vector store 파일 탐색"""
    for item in iter_vector_store_files(vector_store_id):
        attributes = item.get("attributes") or {}
        if attributes.get("relative_key") == relative_key:
            return item
    return None


def delete_remote_file(vector_store_id: str, remote_file: dict | None) -> None:
    """기존 vector store 파일/원본 파일 삭제 시도"""
    if not remote_file:
        return

    vector_store_file_id = remote_file.get("id") or remote_file.get("file_id")
    openai_file_id = remote_file.get("file_id") or remote_file.get("id")

    if vector_store_file_id:
        try:
            client.vector_stores.files.delete(
                vector_store_id=vector_store_id,
                file_id=vector_store_file_id,
            )
        except Exception:
            pass

    if openai_file_id:
        try:
            client.files.delete(file_id=openai_file_id)
        except Exception:
            pass


def wait_until_file_ready(
    vector_store_id: str,
    vector_store_file_id: str,
    max_polls: int = 60,
    poll_interval_seconds: float = 2.0,
) -> dict:
    """vector store file 처리 완료까지 대기"""
    for _ in range(max_polls):
        result = client.vector_stores.files.retrieve(
            vector_store_id=vector_store_id,
            file_id=vector_store_file_id,
        )
        status = getattr(result, "status", None)
        if status == "completed":
            return model_to_dict(result)
        if status == "failed":
            raise RuntimeError(f"Vector store file 처리 실패: {vector_store_file_id}")
        time.sleep(poll_interval_seconds)
    raise TimeoutError(f"Vector store file 처리 대기 시간 초과: {vector_store_file_id}")


def upload_file_to_openai(path: Path) -> str:
    """OpenAI File API에 파일 업로드"""
    with open(path, "rb") as handle:
        result = client.files.create(file=handle, purpose="assistants")
    return result.id


def add_file_to_vector_store(
    vector_store_id: str,
    file_id: str,
    attributes: dict | None = None,
) -> dict:
    """업로드된 파일을 vector store에 연결"""
    kwargs = {
        "vector_store_id": vector_store_id,
        "file_id": file_id,
    }
    if attributes:
        kwargs["attributes"] = attributes

    result = client.vector_stores.files.create(**kwargs)
    wait_until_file_ready(vector_store_id, result.id)
    return model_to_dict(result)


def create_temp_markdown(filename: str, content: str) -> Path:
    """임시 markdown 파일 생성"""
    safe_name = Path(filename).stem or "document"
    temp = tempfile.NamedTemporaryFile(
        prefix=f"{safe_name}-",
        suffix=".md",
        delete=False,
    )
    temp.write(content.encode("utf-8"))
    temp.flush()
    temp.close()
    return Path(temp.name)


def ocr_image_to_markdown(image_path: Path, prompt_context: str = "") -> str:
    """이미지에서 텍스트/표를 추출해 markdown으로 변환"""
    mime_type = "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    input_text = (
        "다음 투자 관련 이미지를 가능한 한 구조적으로 OCR 해주세요. "
        "표는 markdown 표로, 텍스트는 markdown 문단/불릿으로 정리하고, "
        "추측하지 말고 보이는 내용만 적어주세요."
    )
    if prompt_context:
        input_text += f"\n추가 맥락: {prompt_context}"

    response = client.responses.create(
        model=INVESTMENT_OCR_MODEL,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": input_text},
                {
                    "type": "input_image",
                    "image_url": f"data:{mime_type};base64,{image_b64}",
                },
            ],
        }],
    )
    output_text = getattr(response, "output_text", "") or ""
    return output_text.strip()


def query_investment_rag(question: str, max_num_results: int = 6) -> dict:
    """vector store를 대상으로 질문 응답"""
    vector_store_id = ensure_vector_store()
    response = client.responses.create(
        model=INVESTMENT_RAG_MODEL,
        input=[
            {
                "role": "system",
                "content": [{
                    "type": "input_text",
                    "text": (
                        "당신은 투자자료 전용 RAG 도우미입니다. "
                        "검색된 자료에 근거해서만 답하고, 자료에 없으면 모른다고 말하세요. "
                        "답변은 한국어로 간결하게 작성하세요."
                    ),
                }],
            },
            {
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": question,
                }],
            },
        ],
        tools=[{
            "type": "file_search",
            "vector_store_ids": [vector_store_id],
            "max_num_results": max_num_results,
        }],
        include=["file_search_call.results"],
    )
    return model_to_dict(response)


def extract_output_text(response: dict) -> str:
    """Responses API 응답에서 텍스트 출력 추출"""
    output_text = response.get("output_text")
    if output_text:
        return output_text.strip()
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        parts = item.get("content", [])
        for part in parts:
            if part.get("type") == "output_text":
                return part.get("text", "").strip()
    return ""


def extract_file_citations(response: dict) -> list[str]:
    """응답에 포함된 파일 citation 목록 추출"""
    citations = []
    seen = set()
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            for annotation in part.get("annotations", []):
                if annotation.get("type") != "file_citation":
                    continue
                filename = annotation.get("filename") or annotation.get("file_id")
                if filename and filename not in seen:
                    seen.add(filename)
                    citations.append(filename)
    return citations


def upsert_document(
    source_path: Path,
    relative_key: str,
    attributes: dict | None = None,
) -> dict:
    """문서를 업로드하고 manifest 갱신"""
    vector_store_id = ensure_vector_store()
    manifest = load_manifest()
    files = manifest.setdefault("files", {})
    file_hash = sha256_file(source_path)
    normalized_attributes = dict(attributes or {})
    normalized_attributes["relative_key"] = relative_key
    normalized_attributes["source_sha256"] = file_hash
    existing = files.get(relative_key)
    if existing and existing.get("sha256") == file_hash:
        return {"status": "skipped", "reason": "unchanged", "relative_key": relative_key}

    remote_existing = find_existing_remote_file(vector_store_id, relative_key)
    if remote_existing:
        remote_attributes = remote_existing.get("attributes") or {}
        if remote_attributes.get("source_sha256") == file_hash:
            files[relative_key] = {
                "sha256": file_hash,
                "openai_file_id": remote_existing.get("file_id") or remote_existing.get("id"),
                "vector_store_file_id": remote_existing.get("id"),
                "attributes": remote_attributes,
            }
            save_manifest(manifest)
            return {"status": "skipped", "reason": "remote_unchanged", "relative_key": relative_key}

        delete_remote_file(vector_store_id, remote_existing)

    file_id = upload_file_to_openai(source_path)
    vector_store_file = add_file_to_vector_store(
        vector_store_id=vector_store_id,
        file_id=file_id,
        attributes=normalized_attributes,
    )

    files[relative_key] = {
        "sha256": file_hash,
        "openai_file_id": file_id,
        "vector_store_file_id": vector_store_file.get("id"),
        "attributes": normalized_attributes,
    }
    save_manifest(manifest)
    return {
        "status": "uploaded",
        "relative_key": relative_key,
        "openai_file_id": file_id,
        "vector_store_file_id": vector_store_file.get("id"),
    }
