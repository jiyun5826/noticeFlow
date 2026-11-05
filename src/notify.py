from datetime import datetime, timedelta
import requests

RECENT_DAYS = 3

def decide_notify_status(
    published_at: str | None,
    now: datetime,
    recent_days: int = RECENT_DAYS
) -> str:
    if published_at is None:
        return "PENDING"

    normalizd_published_at = datetime.fromisoformat(published_at)

    if now - normalizd_published_at <= timedelta(days=recent_days):
        return "PENDING"

    return "SKIPPED"

UOS_NOTICE_URL = "https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&seq={seq}"

def build_discord_payload(notice: dict) -> dict:
    embed = {
        "title": notice["title"][:256],
        "url": UOS_NOTICE_URL.format(seq=notice["source_id"]),
        "color": 0x1E5BA8,
        "footer": {"text": "서울시립대 일반공지"},
    }

    if notice["published_at"] is not None:
        embed["timestamp"] = notice["published_at"]
    else:
        embed["footer"]["text"] = "서울시립대 일반공지 · 게시일 미확인"

    return {"username": "학교 공지사항", "embeds": [embed]}


def send_discord(webhook_url: str, payload: dict) -> None:
    response = requests.post(webhook_url, json=payload, timeout=10)
    response.raise_for_status()

