"""Date, time, and timestamp formatting utilities."""

from datetime import datetime, timezone


def get_current_utc_timestamp() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def format_filename_timestamp(dt: datetime = None) -> str:
    """Format datetime into filename safe string YYYY-MM-DD_HHMMSS."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d_%H%M%S")


def format_date_dir(dt: datetime = None) -> str:
    """Format datetime into date folder string YYYY-MM-DD."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d")
