from datetime import datetime, timedelta

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
