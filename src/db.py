import sqlite3
from datetime import timezone, datetime

def init_db(db_path: str) -> None:
    connection = sqlite3.connect(db_path)

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                published_at TEXT,
                first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notify_status TEXT NOT NULL DEFAULT 'SKIPPED',
                notify_attempts INTEGER NOT NULL DEFAULT 0,
                notify_last_error TEXT,
                notified_at TEXT,
                UNIQUE (source, source_id)
            )
        """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS collection_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                status TEXT NOT NULL,
                fetched_count INTEGER,
                rejected_count INTEGER,
                inserted_count INTEGER,
                duration_ms INTEGER,
                error TEXT
            )
        """
        )
        connection.commit()
    finally:
        connection.close()


def save_notices(db_path: str, notices: list[dict]) -> int:
    connection = sqlite3.connect(db_path)

    try:
        before = connection.total_changes
        connection.executemany(
            """
            INSERT INTO notices (
                source,
                source_id,
                title,
                url,
                published_at,
                notify_status
            ) VALUES (
                :source,
                :source_id,
                :title,
                :url,
                :published_at,
                :notify_status
            )
            ON CONFLICT(source, source_id) DO NOTHING
        """,
        notices
        )
        connection.commit()
        inserted_count = connection.total_changes - before

    finally:
        connection.close()

    return inserted_count

def save_run(db_path: str, run: dict) -> None:
    connection = sqlite3.connect(db_path)

    try:
        connection.execute(
            """
            INSERT INTO collection_runs(
                started_at,
                status,
                fetched_count,
                rejected_count,
                inserted_count,
                duration_ms,
                error
            ) VALUES (
                :started_at,
                :status,
                :fetched_count,
                :rejected_count,
                :inserted_count,
                :duration_ms,
                :error
            )
        """, 
        run
        )
        connection.commit()
    finally:
        connection.close()

def get_notices_to_notify(db_path: str, max_attemts: int = 3) -> list[dict]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            """
            SELECT id, source_id, title, url, published_at
            FROM notices
            WHERE notify_status IN ('PENDING', 'FAILED')
            AND notify_attempts < ?
            ORDER BY published_at
        """,
        (max_attemts,)
        ).fetchall()
        connection.commit()
    finally:
        connection.close()

    return [dict(row) for row in rows]

def mark_notify_sent(db_path: str, notice_id: int) -> None:
    connection = sqlite3.connect(db_path)

    try:
        connection.execute(
            """
            UPDATE notices
            SET notify_status = 'SENT',
                notify_attempts = notify_attempts + 1,
                notified_at = ?
            WHERE id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), notice_id),   
        )
        connection.commit()      
    finally:
        connection.close()

def mark_notify_failed(db_path: str, notice_id: int, error: str) -> None:
    connection = sqlite3.connect(db_path)

    try:
        connection.execute(
            """
            UPDATE notices
            SET notify_status = 'FAILED',
                notify_attempts = notify_attempts + 1,
                notify_last_error = ?
            WHERE id = ?
            """,
            (error, notice_id),   
        )
        connection.commit()      
    finally:
        connection.close()