import os
import requests
import xml.etree.ElementTree as ET
import time
from urllib.parse import parse_qs, urlparse
from src.db import (
    init_db, 
    save_notices, 
    save_run, 
    get_notices_to_notify,
    mark_notify_failed,
    mark_notify_sent
)
from time import perf_counter
from datetime import datetime, timedelta, timezone
from src.notify import decide_notify_status, build_discord_payload, send_discord
from dotenv import load_dotenv
from src.classifier import classify_notice, load_keywords
from src.sources import SOURCES

KST = timezone(timedelta(hours=9))

def parse_published_at(text: str | None) -> str | None:
    if text is None or text == "":
        return None


    try:
        published_at = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M:%S")
    
    except ValueError:
        return None

    return published_at.replace(tzinfo=KST).isoformat()
    

def parse_notices(xml_bytes: bytes, source: str) -> tuple[list[dict], list[dict]]:
    notices = []
    rejected = []
    config = SOURCES[source]

    root = ET.fromstring(xml_bytes)

    items = root.findall("./channel/item")
    if not items:
        raise ValueError("RSS에서 공지 항목을 찾을 수 없습니다")

    for item in items:
        link = item.findtext("link") or ""
        query = parse_qs(urlparse(link).query)
        title = (item.findtext("title") or "").strip()
        list_id = query.get("list_id", [None])[0]
        seq = query.get("seq", [None])[0]

        if list_id != config["list_id"] or seq is None:
            rejected.append({
                "title": title,
                "url": link,
                "reason": "일반공지 링크 형식이 아닙니다."
            })
            continue

        if not title:
            rejected.append({
                "title": title,
                "url": link,
                "reason": "공지 제목이 없습니다."
            })
            continue
        
        notices.append({
            "source": source,
            "source_id": seq,
            "title": title,
            "description": item.findtext("description") or "",
            "url": link,
            "published_at": parse_published_at(item.findtext("pubDate")),
        })

    if not notices:
        raise ValueError("공지가 없습니다.")
    

    return notices, rejected


def describe_error(error: requests.RequestException) -> str:
    if error.response is not None:
        return f'HTTP {error.response.status_code}'
    else:
        return type(error).__name__


def collect_source(db_path: str, source: str, keywords: list[str], now: datetime) -> dict:
    response = requests.get(
        SOURCES[source]["rss_url"],
        headers={
            "User-Agent": "NoticeFlow/0.1",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
        timeout=10,
    )
    response.raise_for_status()
    notices, rejected = parse_notices(response.content, source)

    for notice in notices:
        classified = classify_notice(notice, keywords)
        notice["is_relevant"] = classified["is_relevant"]
        notice["matched_keywords"] = ",".join(classified["matched_keywords"]) or None
        notice["notify_status"] = decide_notify_status(
            notice["published_at"], now, notice["is_relevant"]
        )

    inserted_count = save_notices(db_path, notices)
    return {"fetched": len(notices), "rejected": len(rejected), "inserted": inserted_count}


def main() -> None:
    db_path = "noticeflow.db"
    init_db(db_path)

    started_at = perf_counter()

    run = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "FAILED",
        "fetched_count": None,
        "rejected_count": None,
        "inserted_count": None,
        "duration_ms": None,
        "notify_sent_count": None,
        "notify_failed_count": None,
        "error": None,
    }

    try:
        load_dotenv()
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            raise RuntimeError("DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")

        keywords = load_keywords("config/keywords.json")
        now = datetime.now(timezone.utc)

        totals = {"fetched": 0, "rejected": 0, "inserted": 0}
        source_errors = []
        for source in SOURCES:
            try:
                result = collect_source(db_path, source, keywords, now)
            except Exception as error:
                source_errors.append(f"{source}: {type(error).__name__}: {error}")
                print(f"[{SOURCES[source]['name']}] 수집 실패: {type(error).__name__}")
                continue
            for key in totals:
                totals[key] += result[key]
            print(f"[{SOURCES[source]['name']}] 수집 {result['fetched']} / 제외 {result['rejected']} / 신규 {result['inserted']}")

        sent_count = 0
        failed_count = 0
        for notice in get_notices_to_notify(db_path):
            try:
                send_discord(webhook_url, build_discord_payload(notice))
                mark_notify_sent(db_path, notice["id"])
                sent_count += 1
            except requests.RequestException as error:
                mark_notify_failed(db_path, notice["id"], describe_error(error))
                failed_count += 1
            time.sleep(1)

        run["fetched_count"] = totals["fetched"]
        run["rejected_count"] = totals["rejected"]
        run["inserted_count"] = totals["inserted"]
        run["notify_sent_count"] = sent_count
        run["notify_failed_count"] = failed_count
        print("알림 발송:", sent_count, "/ 실패:", failed_count)

        if source_errors:
            run["status"] = "PARTIAL" if len(source_errors) < len(SOURCES) else "FAILED"
            raise RuntimeError("출처 수집 실패 - " + "; ".join(source_errors))

        run["status"] = "SUCCESS"

    except Exception as error:
        run["error"] = f"{type(error).__name__}: {error}"
        raise

    finally:
        run["duration_ms"] = round((perf_counter() - started_at) * 1000)
        save_run(db_path, run)                         
        print(f"실행시간: {run['duration_ms']}ms")


if __name__ == "__main__":
    main()











    
