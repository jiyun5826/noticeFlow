import requests
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urlparse
from src.db import init_db, save_notices

def parse_notices(xml_bytes: bytes) -> list[dict]:
    notices = []

    root = ET.fromstring(xml_bytes)

    items = root.findall("./channel/item")

    for item in items:
        link = item.findtext("link") or ""
        query = parse_qs(urlparse(link).query)

        list_id = query.get("list_id", [None])[0]
        seq = query.get("seq", [None])[0]

        if list_id != "FA1" or seq is None:
            raise ValueError(f"일반공지 링크 형식이 올바르지 않습니다: {link}")
        
        notices.append({
            "source": "uos_general",
            "source_id": seq,
            "title": item.findtext("title"),
            "url": item.findtext("link"),
            "published_at": item.findtext("pubDate"),
        })

    return notices

def main() -> None:
    response = requests.get(
        "https://www.uos.ac.kr/rss/gBoard.do",
        headers={
            "User-Agent": "NoticeFlow/0.1",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
        timeout=10,
    )

    print(response.status_code)
    print(len(response.text))

    print(response.url)
    print(response.history)
    print(response.headers.get("Content-Type"))
    print(response.encoding)

    response.raise_for_status()
    notices = parse_notices(response.content)

    db_path = "noticeflow.db"
    init_db(db_path)

    inserted_count = save_notices(db_path, notices)

    print("수집 건수:", len(notices))
    print("신규 저장 건수:", inserted_count)


if __name__ == "__main__":
    main()











    
