from datetime import datetime, timedelta
from src.sources import SOURCES
import requests

RECENT_DAYS = 3
UOS_NOTICE_URL = "https://www.uos.ac.kr/korNotice/view.do?list_id={list_id}&seq={seq}"

def decide_notify_status(
    published_at: str | None,
    now: datetime,
    is_relevant: bool,
    recent_days: int = RECENT_DAYS
) -> str:
    if not is_relevant:
        return "SKIPPED"
    if published_at is None:
        return "PENDING"

    normalizd_published_at = datetime.fromisoformat(published_at)

    if now - normalizd_published_at <= timedelta(days=recent_days):
        return "PENDING"

    return "SKIPPED"


def build_discord_payload(notice: dict) -> dict:
    config = SOURCES[notice["source"]]
    footer = f"서울시립대 {config['name']}공지"
                            
    embed = {
        "title": notice["title"][:256],
        "url": UOS_NOTICE_URL.format(list_id=config["list_id"], seq=notice["source_id"]),
        "color": 0xD40202,
        "footer": {"text": footer},
    }

    if notice["published_at"] is not None:
        embed["timestamp"] = notice["published_at"]
    else:
        embed["footer"]["text"] = f"{footer} · 게시일 미확인"

    return {"username": "학교 공지사항", "embeds": [embed]}


def send_discord(webhook_url: str, payload: dict) -> None:
    response = requests.post(webhook_url, json=payload, timeout=10)
    response.raise_for_status()
