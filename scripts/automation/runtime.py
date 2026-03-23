#!/usr/bin/env python3
from __future__ import annotations

"""자동화 스크립트용 공통 런타임 헬퍼"""

import json
import os
import urllib.error
import urllib.request
from typing import Any


def get_required_env(name: str) -> str:
    """필수 환경변수를 읽고 비어 있으면 명확한 예외를 던진다."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} 환경변수가 비어 있습니다.")
    return value


def request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    data: bytes | None = None,
    timeout: int = 15,
    label: str = "HTTP 요청",
) -> dict[str, Any] | list[Any]:
    """JSON 응답을 반환하고 HTTP 오류는 읽기 쉬운 메시지로 변환한다."""
    req = urllib.request.Request(url, data=data, method=method)
    for key, value in (headers or {}).items():
        req.add_header(key, value)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            if not body:
                return {}
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"{label} 실패 [{exc.code}] {method} {url}: {body}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{label} 실패 {method} {url}: {exc.reason}") from exc

