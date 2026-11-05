import sqlite3

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