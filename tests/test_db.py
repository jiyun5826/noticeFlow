import sqlite3
from src.db import init_db, save_notices, save_run

def test_save_notices_ignores_duplicates(tmp_path):
    db_path = tmp_path / "test.db"
    notices = [
        {
            "source": "uos_general",
            "source_id": "100",
            "title": "테스트 공지 1",
            "url": "https://example.com/100",
            "published_at": "2026-11-04 10:00:00",
        },
        {
            "source": "uos_general",
            "source_id": "101",
            "title": "테스트 공지 2",
            "url": "https://example.com/101",
            "published_at": "2026-11-04 11:00:00",
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