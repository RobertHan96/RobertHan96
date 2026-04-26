#!/usr/bin/env python3
from __future__ import annotations

"""
태스크9: 임대주택 공고 모니터링
- GH / SH / LH 웹 공고를 하루 1회 수집
- 부모님 조건에 맞는 공고를 점수화해 텔레그램으로 전달
- 새로 게시된 공고만 알림하고 상태는 repo에 저장
"""

import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

try:
    import requests
except ImportError:
    requests = None

try:
    from .config.loader import load_config
    from .notify import send_telegram
except ImportError:
    from config.loader import load_config
    from notify import send_telegram

KST = timezone(timedelta(hours=9))
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
)

GH_RENT_LIST_URL = "https://apply.gh.or.kr/sb/sr/sr7150/selectPbancRentHouseList.do"
GH_RENT_DETAIL_URL = "https://apply.gh.or.kr/sb/sr/sr7150/selectPbancDetailView.do"
GH_BUY_RENT_LIST_URL = "https://apply.gh.or.kr/sb/sr/sr7155/selectPbancRentHouseList.do"
GH_BUY_RENT_DETAIL_URL = "https://apply.gh.or.kr/sb/sr/sr7155/selectPbancDetailView.do"
SH_LIST_URL = "https://housing.seoul.go.kr/site/main/sh/publicLease/list"
LH_LIST_URL = "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1026"
LH_DETAIL_URL = "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancInfo.do"
MYHOME_RENT_LIST_URL = "https://apis.data.go.kr/1613000/HWSPR02/rsdtRcritNtcList"

ROOT_DIR = Path(__file__).resolve().parents[2]


def load_housing_config() -> dict[str, Any]:
    return load_config().get("housing_monitor", {})


def fetch_html(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, str] | None = None,
    timeout: int = 20,
    label: str = "웹 요청",
) -> str:
    data = None
    if payload:
        data = urllib.parse.urlencode(payload).encode()

    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept-Language", "ko,en;q=0.9")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        if requests is not None:
            try:
                response = requests.request(
                    method,
                    url,
                    data=payload if method.upper() != "GET" else None,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept-Language": "ko,en;q=0.9",
                    },
                    timeout=timeout,
                )
                response.raise_for_status()
                return response.text
            except Exception as fallback_exc:
                raise RuntimeError(
                    f"{label} 실패 [{method} {url}]: {exc} / requests fallback: {fallback_exc}"
                ) from fallback_exc
        raise RuntimeError(f"{label} 실패 [{method} {url}]: {exc}") from exc


def fetch_json_api(
    url: str,
    *,
    service_key: str,
    params: dict[str, Any],
    timeout: int = 20,
    label: str = "API 요청",
) -> dict[str, Any]:
    serialized_params = urllib.parse.urlencode(
        {
            key: value
            for key, value in params.items()
            if value is not None and value != ""
        },
        doseq=True,
    )
    delimiter = "&" if "?" in url else "?"
    full_url = f"{url}{delimiter}serviceKey={service_key}"
    if serialized_params:
        full_url = f"{full_url}&{serialized_params}"

    req = urllib.request.Request(full_url, method="GET")
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept", "application/json,*/*")
    req.add_header("Accept-Language", "ko,en;q=0.9")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        if requests is not None:
            try:
                response = requests.get(
                    full_url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "application/json,*/*",
                        "Accept-Language": "ko,en;q=0.9",
                    },
                    timeout=timeout,
                )
                response.raise_for_status()
                return response.json()
            except Exception as fallback_exc:
                raise RuntimeError(
                    f"{label} 실패 [GET {url}]: {exc} / requests fallback: {fallback_exc}"
                ) from fallback_exc
        raise RuntimeError(f"{label} 실패 [GET {url}]: {exc}") from exc


def clean_text(value: str | None) -> str:
    return " ".join((value or "").replace("\xa0", " ").split()).strip()


def clean_notice_title(value: str | None) -> str:
    text = clean_text(value)
    text = re.sub(r"\s+\d+일전$", "", text)
    return clean_text(text)


def parse_date(value: str | None) -> datetime | None:
    text = clean_text(value)
    if not text or text in {"-", "공고문 확인"}:
        return None

    iso_candidate = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_candidate)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=KST)
        return parsed.astimezone(KST)
    except ValueError:
        pass

    normalized = text.replace("/", "-").replace(".", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    candidates = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y%m%d",
        "%Y%m%d %H:%M",
        "%Y%m%d%H%M%S",
        "%y-%m-%d",
    ]
    for fmt in candidates:
        try:
            return datetime.strptime(normalized, fmt).replace(tzinfo=KST)
        except ValueError:
            continue
    return None


def format_date(value: datetime | None) -> str:
    if not value:
        return "-"
    return value.astimezone(KST).strftime("%Y-%m-%d")


def format_datetime_range(value: str | None) -> str:
    text = clean_text(value)
    if not text:
        return "-"
    return text


def format_number(value: Any) -> str:
    text = clean_text(str(value))
    if not text or text in {"0", "0.0", "None"}:
        return "-"
    try:
        return f"{int(float(text)):,}"
    except ValueError:
        return text


def derive_notice_status(
    today: datetime,
    apply_start: datetime | None,
    apply_end: datetime | None,
    fallback: str = "",
) -> str:
    if apply_start and apply_end:
        today_date = today.astimezone(KST).date()
        start_date = apply_start.astimezone(KST).date()
        end_date = apply_end.astimezone(KST).date()
        if today_date < start_date:
            return "공고중"
        if start_date <= today_date <= end_date:
            if (end_date - today_date).days <= 3:
                return "마감임박"
            return "접수중"
        return "마감"
    return clean_text(fallback)


def notice_richness(item: dict[str, Any]) -> int:
    return sum(
        1
        for value in [
            item.get("region"),
            item.get("housing_type"),
            item.get("apply_start"),
            item.get("apply_end"),
            item.get("status"),
            item.get("detail_summary"),
            item.get("eligibility"),
            item.get("url"),
        ]
        if clean_text(str(value))
    )


def source_rank(source_name: str) -> int:
    order = {
        "gh_rent": 0,
        "gh_buy_rent": 0,
        "sh": 1,
        "lh": 2,
        "myhome": 3,
    }
    return order.get(source_name, 9)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def stable_notice_id(*parts: str) -> str:
    joined = "||".join(clean_text(part) for part in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def infer_region_from_text(text: str, config: dict[str, Any]) -> str:
    combined = clean_text(text)
    target_regions = config.get("target_regions", {})
    candidates = (
        target_regions.get("primary", [])
        + target_regions.get("secondary", [])
        + target_regions.get("tertiary", [])
    )
    for region in candidates:
        if region and region in combined:
            return region
    district_match = re.search(r"([가-힣]+(?:시|군|구|동|읍|면))", combined)
    return district_match.group(1) if district_match else ""


def find_priority_region(region_text: str, configured_regions: list[str]) -> str:
    normalized = clean_text(region_text)
    for region in configured_regions:
        if region and region in normalized:
            return region
    return ""


def is_today(value: datetime | None, today: datetime) -> bool:
    return bool(value and value.astimezone(KST).date() == today.date())


def extract_schedule_range(text: str) -> tuple[str | None, str | None]:
    matches = re.findall(
        r"(\d{4}[.\-]\d{2}[.\-]\d{2}(?:\s+\d{2}:\d{2})?)",
        clean_text(text),
    )
    if len(matches) >= 2:
        return matches[0], matches[1]
    if len(matches) == 1:
        return matches[0], None
    return None, None


def extract_lines(soup: BeautifulSoup) -> list[str]:
    return [clean_text(line) for line in soup.get_text("\n", strip=True).splitlines() if clean_text(line)]


def extract_line_by_labels(lines: list[str], labels: list[str]) -> str:
    for index, line in enumerate(lines):
        for label in labels:
            if label in line:
                remainder = clean_text(line.split(label, 1)[1].lstrip(":： "))
                if remainder:
                    return remainder
                if index + 1 < len(lines):
                    return clean_text(lines[index + 1])
                return line
    return ""


def extract_table_pairs(table: Any) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        index = 0
        while index + 1 < len(cells):
            key = clean_text(cells[index].get_text(" ", strip=True))
            value = clean_text(cells[index + 1].get_text(" ", strip=True))
            if key:
                pairs[key] = value
            index += 2
    return pairs


def text_from_notice(item: dict[str, Any]) -> str:
    parts = [
        item.get("title", ""),
        item.get("housing_type", ""),
        item.get("region", ""),
        item.get("status", ""),
        item.get("eligibility", ""),
        item.get("detail_summary", ""),
    ]
    return clean_text(" ".join(parts))


def score_notice(item: dict[str, Any], config: dict[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    combined = text_from_notice(item)

    target_regions = config.get("target_regions", {})
    region = item.get("region", "") or infer_region_from_text(combined, config)
    item["region"] = region

    matched_primary = find_priority_region(region, target_regions.get("primary", []))
    matched_secondary = find_priority_region(region, target_regions.get("secondary", []))
    matched_tertiary = find_priority_region(region, target_regions.get("tertiary", []))

    if matched_primary:
        score += 30
        reasons.append(f"1순위 지역({matched_primary})")
    elif matched_secondary:
        score += 20
        reasons.append(f"2순위 지역({matched_secondary})")
    elif matched_tertiary:
        score += 10
        reasons.append(f"확장 지역({matched_tertiary})")

    housing_type = clean_text(item.get("housing_type", ""))
    preferred_types = config.get("preferred_types", [])
    for preferred in preferred_types:
        if preferred in housing_type or preferred in combined:
            score += 25
            reasons.append(f"{preferred} 유형")
            break

    if "고령자" in combined:
        score += 30
        reasons.append("고령자 키워드")

    for keyword in config.get("high_keywords", []):
        if keyword == "고령자":
            continue
        if keyword in combined:
            if keyword == "예비입주자":
                score += 20
            elif keyword in {"잔여세대", "미계약", "선착순", "수의계약"}:
                score += 20
            else:
                score += 10
            reasons.append(f"{keyword} 조건")

    for keyword in config.get("exclude_keywords", []):
        if keyword in combined:
            score -= 50
            reasons.append(f"{keyword} 전용 가능성")
            break

    if item.get("status") in {"공고중", "접수중"}:
        score += 5

    score = max(score, 0)
    deduped_reasons: list[str] = []
    for reason in reasons:
        if reason not in deduped_reasons:
            deduped_reasons.append(reason)
    item["priority_score"] = score
    item["reason"] = ", ".join(deduped_reasons[:3]) or "부모님 조건 기준으로 추가 검토 필요"
    return score, deduped_reasons


def summarize_gh_detail(html_text: str) -> dict[str, str]:
    soup = BeautifulSoup(html_text, "html.parser")
    lines = extract_lines(soup)

    first_table = soup.find("table")
    published = ""
    status = ""
    housing_type = ""
    if first_table:
        first_pairs = extract_table_pairs(first_table)
        status = first_pairs.get("공고상태", "")
        housing_type = first_pairs.get("유형", "")
        published = first_pairs.get("공고일", "")

    location = ""
    for table in soup.find_all("table"):
        pairs = extract_table_pairs(table)
        if "소재지" in pairs and ("지구명" in pairs or "입주예정월" in pairs):
            location = pairs.get("소재지", "")
            break
    if not location:
        location = extract_line_by_labels(lines, ["소재지"])

    online_range = extract_line_by_labels(lines, ["온라인접수기간"])
    offline_range = extract_line_by_labels(lines, ["현장접수기간"])
    contract_range = extract_line_by_labels(lines, ["계약기간"])

    deposit = ""
    rent = ""
    for table in soup.find_all("table"):
        headers = [clean_text(th.get_text(" ", strip=True)) for th in table.find_all("th")]
        if "임대보증금(원)" in headers and "월임대료(원)" in headers:
            data_rows = table.find_all("tr")
            if len(data_rows) >= 2:
                tds = data_rows[1].find_all("td")
                if len(tds) >= 5:
                    deposit = clean_text(tds[3].get_text(" ", strip=True))
                    rent = clean_text(tds[4].get_text(" ", strip=True))
            break

    detail_summary_parts = []
    if location:
        detail_summary_parts.append(f"소재지: {location}")
    if online_range:
        detail_summary_parts.append(f"온라인접수: {online_range}")
    elif offline_range:
        detail_summary_parts.append(f"현장접수: {offline_range}")
    elif contract_range:
        detail_summary_parts.append(f"계약기간: {contract_range}")
    if (deposit or rent) and {deposit, rent} != {"공고문 확인"}:
        detail_summary_parts.append(f"임대조건: 보증금 {deposit or '-'} / 월임대료 {rent or '-'}")

    return {
        "published": published,
        "status": status,
        "housing_type": housing_type,
        "location": location,
        "apply_start": extract_schedule_range(online_range or offline_range or contract_range)[0] or "",
        "apply_end": extract_schedule_range(online_range or offline_range or contract_range)[1] or "",
        "detail_summary": " / ".join(detail_summary_parts),
    }


def summarize_lh_detail(html_text: str) -> dict[str, str]:
    soup = BeautifulSoup(html_text, "html.parser")
    lines = extract_lines(soup)

    published = extract_line_by_labels(lines, ["공고일"])
    apply_range = extract_line_by_labels(lines, ["접수기간"])
    qualification = ""
    pre_tag = soup.find("pre")
    if pre_tag:
        qualification = clean_text(pre_tag.get_text(" ", strip=True))

    deposit = ""
    rent = ""
    for table in soup.find_all("table"):
        headers = [clean_text(th.get_text(" ", strip=True)) for th in table.find_all("th")]
        if "임대보증금" in " ".join(headers) and "월임대료" in " ".join(headers):
            data_rows = table.find_all("tr")
            if len(data_rows) >= 2:
                tds = data_rows[1].find_all("td")
                if len(tds) >= 4:
                    deposit = clean_text(tds[-3].get_text(" ", strip=True))
                    rent = clean_text(tds[-2].get_text(" ", strip=True))
            break

    detail_summary_parts = []
    if apply_range:
        detail_summary_parts.append(f"접수기간: {apply_range}")
    if qualification:
        detail_summary_parts.append(f"자격: {qualification[:120]}")
    if deposit or rent:
        detail_summary_parts.append(f"임대조건: 보증금 {deposit or '-'} / 월임대료 {rent or '-'}")

    apply_start, apply_end = extract_schedule_range(apply_range)
    return {
        "published": published,
        "apply_start": apply_start or "",
        "apply_end": apply_end or "",
        "eligibility": qualification[:220],
        "detail_summary": " / ".join(detail_summary_parts),
    }


def collect_myhome_source(
    source_config: dict[str, Any],
    today: datetime,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    label = source_config["label"]
    service_key = clean_text(os.environ.get("MYHOME_API_KEY"))
    if not service_key:
        raise RuntimeError("MYHOME_API_KEY 환경변수가 비어 있습니다.")

    num_of_rows = int(source_config.get("num_of_rows", 100))
    max_pages = int(source_config.get("max_pages", 10))
    brtc_codes = source_config.get("brtc_codes", ["41", "28"])
    year_month = today.strftime("%Y%m")
    notices: list[dict[str, Any]] = []

    for brtc_code in brtc_codes:
        total_count = None
        for page in range(1, max_pages + 1):
            data = fetch_json_api(
                MYHOME_RENT_LIST_URL,
                service_key=service_key,
                params={
                    "numOfRows": str(num_of_rows),
                    "pageNo": str(page),
                    "brtcCode": str(brtc_code),
                    "yearMtBegin": year_month,
                    "yearMtEnd": year_month,
                    "_type": "json",
                },
                label=f"{label} 목록",
            )
            response = data.get("response", {})
            header = response.get("header", {})
            if header.get("resultCode") not in {None, "00"}:
                raise RuntimeError(
                    f"{label} 응답 오류 [{header.get('resultCode')}]: {header.get('resultMsg')}"
                )

            body = response.get("body", {})
            page_total = int(body.get("totalCount", 0) or 0)
            if total_count is None:
                total_count = page_total

            items = body.get("item", [])
            if isinstance(items, dict):
                items = [items]
            if not items:
                break

            page_today_count = 0
            for raw_item in items:
                published_at = parse_date(raw_item.get("rcritPblancDe"))
                if not is_today(published_at, today):
                    continue

                page_today_count += 1
                apply_start_dt = parse_date(raw_item.get("beginDe"))
                apply_end_dt = parse_date(raw_item.get("endDe"))
                address = clean_text(raw_item.get("fullAdres"))
                source_institution = clean_text(raw_item.get("suplyInsttNm"))
                title = clean_notice_title(raw_item.get("pblancNm"))
                region = clean_text(
                    " ".join(
                        part
                        for part in [
                            clean_text(raw_item.get("brtcNm")),
                            clean_text(raw_item.get("signguNm")),
                        ]
                        if part
                    )
                ) or infer_region_from_text(" ".join([title, address]), config)

                housing_type = clean_text(
                    " ".join(
                        part
                        for part in [
                            clean_text(raw_item.get("suplyTyNm")),
                            clean_text(raw_item.get("houseTyNm")),
                        ]
                        if part
                    )
                )
                supply_count = clean_text(str(raw_item.get("sumSuplyCo", "")))
                deposit = format_number(raw_item.get("rentGtn"))
                monthly_rent = format_number(raw_item.get("mtRntchrg"))

                detail_summary_parts = []
                if source_institution:
                    detail_summary_parts.append(f"공급기관: {source_institution}")
                if address:
                    detail_summary_parts.append(f"위치: {address}")
                if supply_count and supply_count != "0":
                    detail_summary_parts.append(f"공급호수: {supply_count}호")
                if deposit != "-" or monthly_rent != "-":
                    detail_summary_parts.append(
                        f"임대조건: 보증금 {deposit} / 월임대료 {monthly_rent}"
                    )

                myhome_detail_url = clean_text(raw_item.get("url")) or clean_text(raw_item.get("pcUrl"))
                notices.append(
                    {
                        "id": stable_notice_id(
                            "myhome",
                            str(raw_item.get("pblancId", "")),
                            str(raw_item.get("houseSn", "")),
                        ),
                        "source": f"{label}{f' · {source_institution}' if source_institution else ''}",
                        "source_name": "myhome",
                        "source_id": f"{raw_item.get('pblancId', '')}:{raw_item.get('houseSn', '')}",
                        "title": title,
                        "region": region,
                        "housing_type": housing_type,
                        "published_at": published_at.isoformat() if published_at else "",
                        "apply_start": format_date(apply_start_dt),
                        "apply_end": format_date(apply_end_dt),
                        "status": derive_notice_status(
                            today,
                            apply_start_dt,
                            apply_end_dt,
                            clean_text(raw_item.get("sttusNm")),
                        ),
                        "url": myhome_detail_url,
                        "detail_summary": " / ".join(detail_summary_parts),
                        "eligibility": clean_text(raw_item.get("refrnc"))[:220],
                    }
                )

            if page_today_count == 0 or page * num_of_rows >= (total_count or 0):
                break

    return notices


def collect_gh_source(source_config: dict[str, Any], today: datetime) -> list[dict[str, Any]]:
    name = source_config["name"]
    label = source_config["label"]
    max_pages = int(source_config.get("max_pages", 5))
    list_url = GH_RENT_LIST_URL if name == "gh_rent" else GH_BUY_RENT_LIST_URL
    detail_url = GH_RENT_DETAIL_URL if name == "gh_rent" else GH_BUY_RENT_DETAIL_URL

    notices: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        html_text = fetch_html(
            list_url,
            method="POST",
            payload={"pageIndex": str(page)},
            label=f"{label} 목록",
        )
        soup = BeautifulSoup(html_text, "html.parser")
        rows = soup.select("tbody tr")
        if not rows:
            break

        page_today_count = 0
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 8:
                continue
            parts = [clean_text(part) for part in row.stripped_strings]
            if len(parts) < 7:
                continue

            title_link = cells[2].find("a", class_="text_cut")
            if not title_link:
                continue

            published_at = parse_date(parts[4])
            if not is_today(published_at, today):
                continue

            page_today_count += 1
            pbanc_no = title_link.get("data-pbancno", "")
            pbanc_kind_cd = title_link.get("data-pbanckndcd", "")
            biz_ty_nm = title_link.get("data-biztynm", "")
            preview_yn = title_link.get("data-previewyn", "N")
            detail_query = urllib.parse.urlencode(
                {
                    "previewYn": preview_yn,
                    "pbancNo": pbanc_no,
                    "pbancKndCd": pbanc_kind_cd,
                    "bizTyNm": biz_ty_nm,
                }
            )
            notice = {
                "id": stable_notice_id(
                    name,
                    pbanc_no,
                    clean_notice_title(title_link.get_text(" ", strip=True)),
                    cells[3].get_text(" ", strip=True),
                ),
                "source": label,
                "source_name": name,
                "source_id": pbanc_no,
                "title": clean_notice_title(title_link.get_text(" ", strip=True)),
                "region": parts[3],
                "housing_type": parts[1],
                "published_at": published_at.isoformat(),
                "apply_end": format_date(parse_date(parts[5])),
                "status": parts[6],
                "url": f"{detail_url}?{detail_query}",
                "detail_summary": "",
                "eligibility": "",
                "apply_start": "",
            }

            try:
                detail_html = fetch_html(notice["url"], label=f"{label} 상세")
                detail = summarize_gh_detail(detail_html)
                if detail.get("published"):
                    notice["published_at"] = (
                        parse_date(detail["published"]) or published_at
                    ).isoformat()
                if detail.get("status"):
                    notice["status"] = detail["status"]
                if detail.get("housing_type"):
                    notice["housing_type"] = detail["housing_type"]
                if detail.get("location"):
                    notice["region"] = notice["region"] or detail["location"]
                if detail.get("detail_summary"):
                    notice["detail_summary"] = detail["detail_summary"]
                if detail.get("apply_start"):
                    notice["apply_start"] = detail["apply_start"]
                if detail.get("apply_end"):
                    notice["apply_end"] = detail["apply_end"]
            except Exception as exc:
                print(f"[{label}] 상세 보강 실패: {exc}")

            notices.append(notice)

        if page_today_count == 0:
            break

    return notices


def collect_sh_source(source_config: dict[str, Any], today: datetime, config: dict[str, Any]) -> list[dict[str, Any]]:
    label = source_config["label"]
    max_pages = int(source_config.get("max_pages", 5))
    notices: list[dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        url = f"{SH_LIST_URL}?{urllib.parse.urlencode({'cp': page, 'listType': 'list', 'supplyType': 'publicLease'})}"
        html_text = fetch_html(url, label=f"{label} 목록")
        soup = BeautifulSoup(html_text, "html.parser")
        rows = soup.select("tbody tr")
        if not rows:
            break

        page_today_count = 0
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            title = clean_notice_title(cells[2].get_text(" ", strip=True))
            published_at = parse_date(cells[3].get_text(" ", strip=True))
            if not is_today(published_at, today):
                continue

            page_today_count += 1
            link = row.find("a", class_="btn-gray")
            url = link.get("href", "") if link else ""
            region = infer_region_from_text(title, config) or "서울"
            notices.append(
                {
                    "id": stable_notice_id(
                        "sh",
                        title,
                        format_date(published_at),
                        clean_text(cells[1].get_text(" ", strip=True)),
                    ),
                    "source": label,
                    "source_name": "sh",
                    "source_id": stable_notice_id("sh", title, format_date(published_at))[:12],
                    "title": title,
                    "region": region,
                    "housing_type": clean_text(cells[1].get_text(" ", strip=True)),
                    "published_at": published_at.isoformat(),
                    "apply_end": "",
                    "status": "",
                    "url": url,
                    "detail_summary": "",
                    "eligibility": "",
                    "apply_start": "",
                }
            )

        if page_today_count == 0:
            break

    return notices


def collect_lh_source(source_config: dict[str, Any], today: datetime) -> list[dict[str, Any]]:
    label = source_config["label"]
    max_pages = int(source_config.get("max_pages", 5))
    notices: list[dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        html_text = fetch_html(
            LH_LIST_URL,
            method="POST",
            payload={"currPage": str(page)},
            label=f"{label} 목록",
        )
        soup = BeautifulSoup(html_text, "html.parser")
        rows = soup.select("tbody tr")
        if not rows:
            break

        page_today_count = 0
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 8:
                continue

            title_link = row.find("a", class_="wrtancInfoBtn")
            if not title_link:
                continue

            published_at = parse_date(cells[5].get_text(" ", strip=True))
            if not is_today(published_at, today):
                continue

            page_today_count += 1
            detail_query = urllib.parse.urlencode(
                {
                    "ccrCnntSysDsCd": "03",
                    "mi": "1026",
                    "panId": title_link.get("data-id1", ""),
                    "aisTpCd": title_link.get("data-id2", ""),
                    "uppAisTpCd": title_link.get("data-id3", ""),
                }
            )
            notice = {
                "id": stable_notice_id(
                    "lh",
                    title_link.get("data-id1", ""),
                    clean_notice_title(title_link.get_text(" ", strip=True)),
                ),
                "source": label,
                "source_name": "lh",
                "source_id": title_link.get("data-id1", ""),
                "title": clean_notice_title(title_link.get_text(" ", strip=True)),
                "region": clean_text(cells[3].get_text(" ", strip=True)),
                "housing_type": clean_text(cells[1].get_text(" ", strip=True)),
                "published_at": published_at.isoformat(),
                "apply_end": format_date(parse_date(cells[6].get_text(" ", strip=True))),
                "status": clean_text(cells[7].get_text(" ", strip=True)),
                "url": f"{LH_DETAIL_URL}?{detail_query}",
                "detail_summary": "",
                "eligibility": "",
                "apply_start": "",
            }

            try:
                detail_html = fetch_html(notice["url"], label=f"{label} 상세")
                detail = summarize_lh_detail(detail_html)
                if detail.get("published"):
                    parsed = parse_date(detail["published"])
                    if parsed:
                        notice["published_at"] = parsed.isoformat()
                if detail.get("apply_start"):
                    notice["apply_start"] = detail["apply_start"]
                if detail.get("apply_end"):
                    notice["apply_end"] = detail["apply_end"]
                if detail.get("eligibility"):
                    notice["eligibility"] = detail["eligibility"]
                if detail.get("detail_summary"):
                    notice["detail_summary"] = detail["detail_summary"]
            except Exception as exc:
                print(f"[{label}] 상세 보강 실패: {exc}")

            notices.append(notice)

        if page_today_count == 0:
            break

    return notices


def collect_notices(
    today: datetime,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], int, int]:
    notices: list[dict[str, Any]] = []
    errors: list[str] = []
    attempted_sources = 0
    successful_sources = 0
    sources = config.get("sources", [])

    for source in sources:
        if not source.get("enabled", True):
            continue

        name = source["name"]
        attempted_sources += 1
        try:
            if name == "myhome":
                items = collect_myhome_source(source, today, config)
            elif name in {"gh_rent", "gh_buy_rent"}:
                items = collect_gh_source(source, today)
            elif name == "sh":
                items = collect_sh_source(source, today, config)
            elif name == "lh":
                items = collect_lh_source(source, today)
            else:
                print(f"알 수 없는 임대주택 source 건너뜀: {name}")
                continue
            notices.extend(items)
            successful_sources += 1
        except Exception as exc:
            message = f"[{source['label']}] 수집 실패: {exc}"
            print(message)
            errors.append(message)

    return notices, errors, attempted_sources, successful_sources


def dedupe_notices(notices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}

    for item in notices:
        dedupe_key = stable_notice_id(
            clean_notice_title(item.get("title", "")),
            item.get("apply_end", ""),
        )
        existing = deduped.get(dedupe_key)
        if not existing:
            deduped[dedupe_key] = item
            continue

        existing_richness = notice_richness(existing)
        candidate_richness = notice_richness(item)
        if candidate_richness > existing_richness:
            deduped[dedupe_key] = item
            continue
        if candidate_richness == existing_richness and source_rank(item.get("source_name", "")) < source_rank(
            existing.get("source_name", "")
        ):
            deduped[dedupe_key] = item

    return list(deduped.values())


def prepare_notices(notices: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for item in dedupe_notices(notices):
        score_notice(item, config)
        prepared.append(item)
    prepared.sort(
        key=lambda item: (
            -int(item.get("priority_score", 0)),
            item.get("apply_end", ""),
            item.get("title", ""),
        )
    )
    return prepared


def build_message(notices: list[dict[str, Any]], config: dict[str, Any], today: datetime) -> str:
    thresholds = config.get("thresholds", {})
    immediate_threshold = int(thresholds.get("immediate", 70))
    summary_threshold = int(thresholds.get("summary", 50))

    immediate = [item for item in notices if int(item.get("priority_score", 0)) >= immediate_threshold]
    summary = [
        item
        for item in notices
        if summary_threshold <= int(item.get("priority_score", 0)) < immediate_threshold
    ]

    if not immediate and not summary:
        return ""

    lines = [
        f"<b>🏠 임대주택 공고 모니터링</b> ({today.strftime('%Y-%m-%d')})",
        "",
    ]

    def append_section(title: str, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        lines.append(f"<b>{html.escape(title)}</b>")
        lines.append("")
        for item in items:
            region = item.get("region") or "지역 확인 필요"
            housing_type = item.get("housing_type") or "유형 확인 필요"
            published_at = parse_date(item.get("published_at", ""))
            apply_end = item.get("apply_end", "")
            status = item.get("status", "")
            detail_summary = item.get("detail_summary", "")
            lines.append(f"• <b>{html.escape(item['title'])}</b>")
            lines.append(f"  - {html.escape(item['source'])} | {html.escape(housing_type)} | {html.escape(region)}")
            lines.append(
                "  - 게시일: "
                f"{html.escape(format_date(published_at))}"
                + (f" | 마감: {html.escape(apply_end)}" if apply_end and apply_end != "-" else "")
                + (f" | 상태: {html.escape(status)}" if status else "")
            )
            lines.append(f"  - 점수: {int(item.get('priority_score', 0))}점 | {html.escape(item.get('reason', ''))}")
            if detail_summary:
                lines.append(f"  - 메모: {html.escape(detail_summary)}")
            lines.append(f"  - <a href=\"{html.escape(item['url'], quote=True)}\">공고 보기</a>")
            lines.append("")

    append_section("즉시 확인 추천", immediate)
    append_section("오늘의 요약 확인", summary)

    return "\n".join(lines).strip()


def load_state(config: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    state_path = ROOT_DIR / config.get("state_path", "data/housing_monitor/seen_notices.json")
    state = load_json(state_path, {"updated_at": None, "notices": {}})
    state.setdefault("notices", {})
    return state_path, state


def save_state(config: dict[str, Any], state: dict[str, Any]) -> None:
    state_path = ROOT_DIR / config.get("state_path", "data/housing_monitor/seen_notices.json")
    write_json(state_path, state)


def save_latest(config: dict[str, Any], notices: list[dict[str, Any]], errors: list[str]) -> None:
    latest_path = ROOT_DIR / config.get("latest_path", "data/housing_monitor/latest_items.json")
    write_json(
        latest_path,
        {
            "generated_at": datetime.now(tz=KST).isoformat(),
            "items": notices,
            "errors": errors,
        },
    )


def update_seen_state(state: dict[str, Any], notices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = state.setdefault("notices", {})
    new_items: list[dict[str, Any]] = []

    for item in notices:
        key = item["id"]
        if key not in seen:
            new_items.append(item)
            seen[key] = {
                "title": item["title"],
                "source": item["source"],
                "published_at": item.get("published_at", ""),
                "first_seen_at": datetime.now(tz=KST).isoformat(),
                "last_seen_at": datetime.now(tz=KST).isoformat(),
                "url": item["url"],
            }
        else:
            seen[key]["last_seen_at"] = datetime.now(tz=KST).isoformat()

    cutoff = datetime.now(tz=KST) - timedelta(days=180)
    for key, value in list(seen.items()):
        last_seen = parse_date(value.get("published_at")) or parse_date(value.get("last_seen_at"))
        if last_seen and last_seen < cutoff:
            del seen[key]

    state["updated_at"] = datetime.now(tz=KST).isoformat()
    return new_items


def main() -> None:
    config = load_housing_config()
    today = datetime.now(tz=KST)

    print("임대주택 공고 수집 중...")
    collected, errors, attempted_sources, successful_sources = collect_notices(today, config)
    if attempted_sources == 0:
        raise RuntimeError("활성화된 임대주택 수집 source가 없습니다.")
    if successful_sources == 0:
        raise RuntimeError("임대주택 공고 수집이 모두 실패했습니다.")

    prepared = prepare_notices(collected, config)
    save_latest(config, prepared, errors)

    state_path, state = load_state(config)
    new_items = update_seen_state(state, prepared)
    save_state(config, state)

    print(
        f"오늘 수집 공고: {len(prepared)}건 / 신규 공고: {len(new_items)}건 "
        f"/ 성공 source: {successful_sources}/{attempted_sources}"
    )
    if errors:
        print("부분 수집 실패:")
        for error in errors:
            print(f"- {error}")

    message = build_message(new_items, config, today)
    if message:
        send_telegram(message)
        print("임대주택 공고 알림 발송 완료")
    else:
        print("새로운 조건 충족 임대주택 공고 없음")

    print(f"상태 저장 완료: {state_path}")


if __name__ == "__main__":
    main()
