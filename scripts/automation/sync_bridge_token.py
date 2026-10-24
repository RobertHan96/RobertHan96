#!/usr/bin/env python3
from __future__ import annotations

"""GitHub의 기존 브리지 토큰을 지정한 Worker에 동기화한다. 값은 출력하지 않는다."""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from .runtime import get_required_env

USER_AGENT = "RH96-bridge-maintenance/1.0"


def worker_name(base_url: str) -> str:
    url = urllib.parse.urlsplit(base_url)
    if (
        url.scheme != "https" or url.username or url.password or url.port
        or url.path not in {"", "/"} or url.query or url.fragment
        or not re.fullmatch(r"[a-z0-9-]+\.[a-z0-9-]+\.workers\.dev", url.hostname or "")
    ):
        raise ValueError("브리지 주소는 https://Worker이름.계정.workers.dev 형식이어야 합니다.")
    return url.hostname.split(".")[0]


def api_json(url: str, token: str, *, method: str, payload: dict | None = None) -> dict:
    request = urllib.request.Request(
        url, method=method,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={
            "Authorization": f"Bearer {token}", "Content-Type": "application/json",
            "Accept": "application/json", "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        # 공급자 오류 본문에는 입력값이 포함될 수 있으므로 상태 코드만 남긴다.
        raise RuntimeError(f"Cloudflare API {method}: HTTP {exc.code}") from None
    except (urllib.error.URLError, OSError):
        raise RuntimeError("Cloudflare API 연결에 실패했습니다.") from None
    if not isinstance(result, dict) or result.get("success") is not True:
        raise RuntimeError("Cloudflare API가 작업을 승인하지 않았습니다.")
    return result


def bridge_authorized(base_url: str, token: str) -> bool:
    request = urllib.request.Request(
        base_url.rstrip("/") + "/state/get", method="POST",
        data=json.dumps({"key": "crypto-premium/btc-upbit-binance/v1"}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}", "Content-Type": "application/json",
            "Accept": "application/json", "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return False
        raise RuntimeError(f"브리지 검증 실패: HTTP {exc.code}") from None
    except (urllib.error.URLError, OSError):
        raise RuntimeError("브리지 검증 중 연결에 실패했습니다.") from None
    if not isinstance(result, dict) or result.get("ok") is not True or type(result.get("found")) is not bool:
        raise RuntimeError("브리지 상태 조회 응답이 올바르지 않습니다.")
    return True


def sync_token() -> None:
    base_url = get_required_env("TELEGRAM_MEMORY_BRIDGE_URL")
    name = worker_name(base_url)
    token = get_required_env("TELEGRAM_MEMORY_BRIDGE_TOKEN")
    if bridge_authorized(base_url, token):
        print("브리지 토큰이 이미 일치합니다. 변경 없이 KV 읽기 검증을 완료했습니다.")
        return

    account = urllib.parse.quote(get_required_env("CLOUDFLARE_ACCOUNT_ID"), safe="")
    api_token = get_required_env("CLOUDFLARE_API_TOKEN")
    endpoint = f"https://api.cloudflare.com/client/v4/accounts/{account}/workers/scripts/{name}/secrets"
    # 대상 Worker가 실제로 존재하는지 먼저 확인한다. 다른 바인딩은 수정하지 않는다.
    existing = api_json(endpoint, api_token, method="GET")
    bindings = existing.get("result")
    if not isinstance(bindings, list):
        raise RuntimeError("대상 Worker의 시크릿 목록을 확인할 수 없습니다.")
    present = any(item.get("name") == "TELEGRAM_MEMORY_BRIDGE_TOKEN" for item in bindings)
    print(f"대상 Worker: {name}; 브리지 시크릿 등록 여부: {present}")
    api_json(endpoint, api_token, method="PUT", payload={
        "name": "TELEGRAM_MEMORY_BRIDGE_TOKEN", "text": token, "type": "secret_text",
    })
    for attempt in range(5):
        if bridge_authorized(base_url, token):
            print("기존 GitHub 토큰 동기화 및 실제 Worker KV 읽기 검증을 완료했습니다.")
            return
        if attempt < 4:
            time.sleep(2)
    raise RuntimeError("토큰 동기화 후에도 브리지 인증이 실패했습니다.")


if __name__ == "__main__":
    sync_token()
