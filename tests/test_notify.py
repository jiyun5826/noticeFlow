from datetime import datetime, timezone, timedelta
from src.notify import decide_notify_status, format_message

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

def test_format_message_includes_title_date_and_link():
    notice = {
        "title": "AI 해커톤 참가자 모집",
        "url": "https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&seq=31802",
        "published_at": "2026-11-05T18:00:51+09:00",
    }

    message = format_message(notice)

    assert "AI 해커톤 참가자 모집" in message
    assert "2026-11-05 18:00" in message
    assert "https://www.uos.ac.kr/korNotice/view.do?list_id=FA1&seq=31802" in message


def test_format_message_marks_unknown_date():
    notice = {
        "title": "날짜 없는 공지", 
        "url": "https://example.com/1", 
        "published_at": None
    }

    assert "미확인" in format_message(notice)