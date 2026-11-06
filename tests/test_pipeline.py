import sqlite3

import pytest
import requests

from src.db import init_db, save_notices
from src.main import collect_all, send_pending_notices


def _notice(source_id):
    return {
        "source": "uos_general",
        "source_id": source_id,
        "title": f"공지 {source_id}",
        "url": f"https://example.com/{source_id}",
        "published_at": "2026-11-06T10:00:00+09:00",
        "notify_status": "PENDING",
        "is_relevant": True,
        "matched_keywords": "인턴",
    }


def _http_error(status_code):
    response = requests.Response()
    response.status_code = status_code
    return requests.HTTPError(response=response)


def _status(db_path, source_id):
    connection = sqlite3.connect(db_path)
    try:
        return connection.execute(
            "SELECT notify_status, notify_attempts, notify_last_error FROM notices WHERE source_id = ?",
            (source_id,),
        ).fetchone()
    finally:
        connection.close()


def _no_sleep(seconds):
    pass


def test_discord_429_marks_only_that_notice_failed(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    save_notices(db_path, [_notice("1"), _notice("2")])

    def sender(webhook_url, payload):
        if payload["embeds"][0]["title"] == "공지 1":
            raise _http_error(429)

    sent, failed = send_pending_notices(db_path, "fake", sender=sender, sleep=_no_sleep)

    assert (sent, failed) == (1, 1)
    assert _status(db_path, "1") == ("FAILED", 1, "HTTP 429")
    assert _status(db_path, "2")[0] == "SENT"


def test_discord_timeout_is_recorded(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    save_notices(db_path, [_notice("1")])

    def sender(webhook_url, payload):
        raise requests.Timeout()

    send_pending_notices(db_path, "fake", sender=sender, sleep=_no_sleep)

    assert _status(db_path, "1") == ("FAILED", 1, "Timeout")


def test_failed_notice_is_sent_on_next_run(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    save_notices(db_path, [_notice("1")])

    def failing(webhook_url, payload):
        raise _http_error(500)

    def working(webhook_url, payload):
        pass

    send_pending_notices(db_path, "fake", sender=failing, sleep=_no_sleep)
    send_pending_notices(db_path, "fake", sender=working, sleep=_no_sleep)

    assert _status(db_path, "1")[:2] == ("SENT", 2)


def test_one_source_failure_does_not_stop_others(tmp_path):
    db_path = str(tmp_path / "test.db")

    def collect(db_path, source, keywords, now):
        if source == "uos_haksa":
            raise _http_error(500)
        return {"fetched": 24, "rejected": 0, "inserted": 3}

    totals, errors = collect_all(db_path, [], None, collect=collect)

    assert totals == {"fetched": 24, "rejected": 0, "inserted": 3}
    assert len(errors) == 1
    assert errors[0].startswith("uos_haksa: HTTPError")