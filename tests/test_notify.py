from datetime import datetime, timezone, timedelta
from src.notify import decide_notify_status

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