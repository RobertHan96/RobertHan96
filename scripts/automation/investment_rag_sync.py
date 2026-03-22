#!/usr/bin/env python3
from __future__ import annotations

"""투자자료 폴더와 생성 문서를 OpenAI Vector Store에 동기화"""

import argparse
from pathlib import Path

try:
    from .investment_digest import build_digest
    from .investment_rag import (
        IMAGE_EXTENSIONS,
        ROOT_DIR,
        SUPPORTED_DIRECT_EXTENSIONS,
        create_temp_markdown,
        ocr_image_to_markdown,
        upsert_document,
    )
except ImportError:
    from investment_digest import build_digest
    from investment_rag import (
        IMAGE_EXTENSIONS,
        ROOT_DIR,
        SUPPORTED_DIRECT_EXTENSIONS,
        create_temp_markdown,
        ocr_image_to_markdown,
        upsert_document,
    )

MANUAL_DOCS_DIR = ROOT_DIR / "data" / "investment_docs"
GENERATED_DIR = ROOT_DIR / "data" / "investment_rag" / "generated"


def collect_sync_targets() -> list[Path]:
    """동기화 대상 파일 목록 수집"""
    targets = []
    for base_dir in [MANUAL_DOCS_DIR, GENERATED_DIR]:
        if not base_dir.exists():
            continue
        for path in sorted(base_dir.rglob("*")):
            if path.is_file():
                targets.append(path)
    return targets


def sync_path(path: Path) -> dict:
    """단일 경로 동기화"""
    relative_key = str(path.relative_to(ROOT_DIR))
    extension = path.suffix.lower()
    attributes = {"relative_key": relative_key}

    if extension in SUPPORTED_DIRECT_EXTENSIONS:
        return upsert_document(path, relative_key=relative_key, attributes=attributes)

    if extension in IMAGE_EXTENSIONS:
        ocr_markdown = ocr_image_to_markdown(path)
        temp_path = create_temp_markdown(path.name, f"# OCR: {path.name}\n\n{ocr_markdown}\n")
        try:
            return upsert_document(
                temp_path,
                relative_key=f"{relative_key}.ocr.md",
                attributes={
                    **attributes,
                    "source_type": "image_ocr",
                    "original_path": relative_key,
                },
            )
        finally:
            temp_path.unlink(missing_ok=True)

    return {"status": "skipped", "reason": f"unsupported_extension:{extension}", "relative_key": relative_key}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generate-digest",
        action="store_true",
        help="동기화 전에 일일 투자 브리프 생성",
    )
    args = parser.parse_args()

    MANUAL_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    if args.generate_digest:
        build_digest()

    uploaded = 0
    skipped = 0
    for path in collect_sync_targets():
        result = sync_path(path)
        print(f"{result['status']}: {result['relative_key']}")
        if result["status"] == "uploaded":
            uploaded += 1
        else:
            skipped += 1

    print(f"동기화 완료: uploaded={uploaded}, skipped={skipped}")


if __name__ == "__main__":
    main()
