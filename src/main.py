import requests
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urlparse
from src.db import init_db, save_notices, save_run
from time import perf_counter
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

def parse_published_at(text: str | None) -> str | None:
    if text is None or text == "":
        return None


    try:
        published_at = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M:%S")
    
    except ValueError:
        return None

    return published_at.replace(tzinfo=KST).isoformat()
    

def parse_notices(xml_bytes: bytes) -> tuple[list[dict], list[dict]]:
    notices = []
    rejected = []

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

        if list_id != "FA1" or seq is None:
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
            "source": "uos_general",
            "source_id": seq,
            "title": title,
            "description": item.findtext("description") or "",
            "url": link,
            "published_at": parse_published_at(item.findtext("pubDate")),
        })

    if not notices:
        raise ValueError("공지가 없습니다.")
    

    return notices, rejected

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
        "error": None,
    }

    try:
        response = requests.get(
            "https://www.uos.ac.kr/rss/gBoard.do",
            headers={
                "User-Agent": "NoticeFlow/0.1",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
            timeout=10,
        )
        response.raise_for_status()
        notices, rejected = parse_notices(response.content) 
        inserted_count = save_notices(db_path, notices)

        run["fetched_count"] = len(notices)
        run["rejected_count"] = len(rejected)
        run["inserted_count"] = inserted_count
        run["status"] = "SUCCESS"       

        print("수집 건수:", len(notices))
        print("제외 건수:", len(rejected))
        print("신규 저장 건수:", inserted_count)  

    except Exception as error:
        run["error"] = f"{type(error).__name__}: {error}"
        raise

    finally:
        run["duration_ms"] = round((perf_counter() - started_at) * 1000)
        save_run(db_path, run)                         
        print(f"실행시간: {run['duration_ms']}ms")


if __name__ == "__main__":
    main()











    
