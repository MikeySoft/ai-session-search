import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sessions.model import AdapterError, Session, one_line


def load_opencode(db_path: Path) -> list[Session]:
    if not db_path.is_file():
        raise AdapterError("opencode", "session store not found")
    try:
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise _db_error(exc) from exc
    try:
        try:
            rows = connection.execute(
                """
                SELECT id, title, directory, time_updated
                FROM session_v2
                WHERE time_archived IS NULL
                """
            ).fetchall()
        except sqlite3.Error as exc:
            raise _db_error(exc) from exc
    finally:
        connection.close()
    sessions = []
    for session_id, title, directory, updated_ms in rows:
        if updated_ms is None or directory is None:
            continue
        text = one_line(title or "") or "untitled"
        updated = datetime.fromtimestamp(updated_ms / 1000, timezone.utc)
        sessions.append(
            Session("opencode", session_id, Path(directory), text, updated)
        )
    return sessions


def _db_error(exc: sqlite3.Error) -> AdapterError:
    if "locked" in str(exc).lower():
        return AdapterError("opencode", "database is locked")
    return AdapterError("opencode", "unreadable database")
