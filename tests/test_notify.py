from datetime import datetime, timezone, timedelta
from src.notify import decide_notify_status, build_discord_payload
KST = timezone(timedelta(hours=9))
NOW = datetime(2026, 11, 5, 18, 0, 0,tzinfo=KST)

def test_recent_notice_is_pending():
    assert decide_notify_status("2026-11-04T18:00:00+09:00", NOW) == "PENDING"


def test_notice_exactly_three_days_old_is_pending():
    assert decide_notify_status("2026-11-02T18:00:00+09:00", NOW) == "PENDING"


def test_old_notice_is_skipped():
    assert decide_notify_status("2026-10-26T13:07:06+09:00", NOW) == "SKIPPED"


def test_notice_without_date_is_pending():
    assert decide_notify_status(None, NOW) == "PENDING"

def test_payload_uses_title_as_link_without_sort_param():
    notice = {
        "source_id": "31802",
        "title": "AI 해커톤 참가자 모집",
        "url": "https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&seq=31802&sort=1",
        "published_at": "2026-11-05T18:00:51+09:00",
    }

    embed = build_discord_payload(notice)["embeds"][0]

    assert embed["title"] == "AI 해커톤 참가자 모집"
    assert embed["url"] == "https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&seq=31802"
    assert embed["timestamp"] == "2026-11-05T18:00:51+09:00"


def test_payload_without_date_has_no_timestamp():
    notice = {"source_id": "1", "title": "날짜 없는 공지", "url": "https://example.com/1", "published_at": None}

    embed = build_discord_payload(notice)["embeds"][0]

    assert "timestamp" not in embed
    assert "미확인" in embed["footer"]["text"]


def test_payload_truncates_long_title():
    notice = {"source_id": "1", "title": "가" * 300, "url": "https://example.com/1", "published_at": None}

    embed = build_discord_payload(notice)["embeds"][0]

    assert len(embed["title"]) <= 256