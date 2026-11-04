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
                UNIQUE (source, source_id)
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
                published_at
            ) VALUES (
                :source,
                :source_id,
                :title,
                :url,
                :published_at
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