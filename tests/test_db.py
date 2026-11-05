import sqlite3
from src.db import (
    init_db, 
    save_notices, 
    save_run, 
    get_notices_to_notify,
    mark_notify_sent,
    mark_notify_failed,
)

def test_save_notices_ignores_duplicates(tmp_path):
    db_path = tmp_path / "test.db"
    notices = [
        {
            "source": "uos_general",
            "source_id": "100",
            "title": "테스트 공지 1",
            "url": "https://example.com/100",
            "published_at": "2026-11-04 10:00:00",
            "notify_status": "PENDING",   
        },
        {
            "source": "uos_general",
            "source_id": "101",
            "title": "테스트 공지 2",
            "url": "https://example.com/101",
            "published_at": "2026-11-04 11:00:00",
            "notify_status": "PENDING",   
        },
    ]

    init_db(str(db_path))

    assert save_notices(str(db_path), notices) == 2
    assert save_notices(str(db_path), notices) == 0

    connection = sqlite3.connect(db_path)
    try:
        saved_count = connection.execute(
            "SELECT COUNT(*) FROM notices"
        ).fetchone()[0]
    finally:
        connection.close()

    assert saved_count == 2


def test_save_run_records_one_row(tmp_path):
    db_path = str(tmp_path/"test.db")
    init_db(db_path)

    save_run(db_path, {
        "started_at": "2026-11-05T09:00:00+00:00",
        "status": "SUCCESS",
        "fetched_count": 24,
        "rejected_count": 0,
        "inserted_count": 3,
        "duration_ms": 512,
        "error": None,
    })

    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT status, fetched_count, inserted_count, error FROM collection_runs"
        ).fetchall()
    finally:
        connection.close()

    assert rows == [("SUCCESS", 24, 3, None)]

def test_save_notices_keeps_existing_notify_status(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    notice = {
        "source": "uos_general",
        "source_id": "200",
        "title": "이미 알린 공지",
        "url": "https://example.com/200",
        "published_at": "2026-11-05T10:00:00+09:00",
        "notify_status": "PENDING",
    }
    save_notices(db_path, [notice])

    # 발송에 성공했다고 가정하고 상태를 SENT로 바꿈
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "UPDATE notices SET notify_status = 'SENT' WHERE source_id = '200'"
        )
        connection.commit()
    finally:
        connection.close()

    # 같은 공지가 다음 실행에서 PENDING으로 다시 들어옴
    assert save_notices(db_path, [notice]) == 0

    connection = sqlite3.connect(db_path)
    try:
        status = connection.execute(
            "SELECT notify_status FROM notices WHERE source_id = '200'"
        ).fetchone()[0]
    finally:
        connection.close()

    assert status == "SENT"

def _notice(source_id, notify_status):
    return {
        "source": "uos_general",
        "source_id": source_id,
        "title": f"공지 {source_id}",
        "url": f"https://example.com/{source_id}",
        "published_at": "2026-11-05T10:00:00+09:00",
        "notify_status": notify_status,
    }


def test_get_notices_to_notify_returns_only_pending(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    save_notices(db_path, [_notice("1", "PENDING"), _notice("2", "SKIPPED")])

    targets = get_notices_to_notify(db_path)

    assert [n["source_id"] for n in targets] == ["1"]


def test_sent_notice_is_not_returned_again(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    save_notices(db_path, [_notice("1", "PENDING")])
    notice_id = get_notices_to_notify(db_path)[0]["id"]

    mark_notify_sent(db_path, notice_id)

    assert get_notices_to_notify(db_path) == []


def test_failed_notice_is_retried_until_three_attempts(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    save_notices(db_path, [_notice("1", "PENDING")])
    notice_id = get_notices_to_notify(db_path)[0]["id"]

    mark_notify_failed(db_path, notice_id, "timeout")
    mark_notify_failed(db_path, notice_id, "timeout")
    assert len(get_notices_to_notify(db_path)) == 1   # 2번 실패 → 아직 재시도 대상

    mark_notify_failed(db_path, notice_id, "HTTP 500")
    assert get_notices_to_notify(db_path) == []       # 3번 실패 → 더 이상 시도 안 함