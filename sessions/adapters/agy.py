import json
import sqlite3
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from sessions.model import AdapterError, Session, one_line


def load_agy(db_path: Path) -> list[Session]:
    if not db_path.is_file():
        raise AdapterError("agy", "session store not found")
    try:
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise AdapterError("agy", "unreadable database") from exc
    try:
        try:
            rows = connection.execute(
                """
                SELECT conversation_id, title, last_modified_time,
                       workspace_uris
                FROM conversation_summaries
                WHERE nesting_depth = 0
                """
            ).fetchall()
        except sqlite3.Error as exc:
            raise AdapterError("agy", "unreadable database") from exc
    finally:
        connection.close()
    sessions = []
    for conversation_id, title, modified, workspace_uris in rows:
        directory = _first_directory(workspace_uris)
        if directory is None:
            continue
        text = one_line(title or "") or "untitled"
        try:
            updated = datetime.fromisoformat(modified).astimezone(timezone.utc)
        except ValueError:
            continue
        sessions.append(
            Session("agy", conversation_id, directory, text, updated)
        )
    return sessions


def _first_directory(workspace_uris: str) -> Path | None:
    try:
        values = json.loads(workspace_uris)
    except json.JSONDecodeError:
        return None
    if not isinstance(values, list):
        return None
    for value in values:
        if not isinstance(value, str) or not value.startswith("file://"):
            continue
        parsed = urllib.parse.urlparse(value)
        if parsed.path:
            return Path(urllib.parse.unquote(parsed.path))
    return None
