import sqlite3
from pathlib import Path

from sessions.adapters.claude import _message_text, _objects


def claude_speech(root: Path) -> dict[str, tuple[str, ...]]:
    projects = root / "projects"
    if not projects.is_dir():
        return {}
    found: dict[str, list[str]] = {}
    for path in projects.rglob("*.jsonl"):
        lines: list[str] = []
        file_id = path.stem
        for obj in _objects(path):
            if obj.get("isSidechain") is True:
                continue
            session_id = obj.get("sessionId")
            if isinstance(session_id, str) and session_id != file_id:
                continue
            if obj.get("type") not in ("user", "assistant"):
                continue
            text = _utterance(_message_text(obj))
            if text:
                lines.append(text)
        if lines:
            found[file_id] = lines
    return {key: tuple(value) for key, value in found.items()}


def opencode_speech(db_path: Path) -> dict[str, tuple[str, ...]]:
    if not db_path.is_file():
        return {}
    try:
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return {}
    try:
        try:
            rows = connection.execute(
                """
                SELECT p.session_id,
                       json_extract(m.data, '$.role'),
                       json_extract(p.data, '$.text')
                FROM part p
                JOIN message m ON m.id = p.message_id
                WHERE json_extract(p.data, '$.type') = 'text'
                ORDER BY p.session_id, p.time_created
                """
            ).fetchall()
        except sqlite3.Error:
            return {}
    finally:
        connection.close()
    found: dict[str, list[str]] = {}
    for session_id, role, text in rows:
        if role not in ("user", "assistant") or not isinstance(text, str):
            continue
        line = _utterance(text)
        if session_id and line:
            found.setdefault(session_id, []).append(line)
    return {key: tuple(value) for key, value in found.items()}


def agy_speech(db_path: Path) -> dict[str, tuple[str, ...]]:
    if not db_path.is_file():
        return {}
    try:
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return {}
    try:
        try:
            rows = connection.execute(
                """
                SELECT conversation_id, user_body, agent_body
                FROM conversations_fts
                ORDER BY conversation_id, chunk_index
                """
            ).fetchall()
        except sqlite3.Error:
            return {}
    finally:
        connection.close()
    found: dict[str, list[str]] = {}
    for conversation_id, user_body, agent_body in rows:
        if not conversation_id:
            continue
        lines = found.setdefault(conversation_id, [])
        lines.extend(_utterance_lines(user_body))
        lines.extend(_utterance_lines(agent_body))
    return {key: tuple(value) for key, value in found.items() if value}


def search_blob(lines: tuple[str, ...] | list[str]) -> str:
    return " ".join(line.replace("\t", " ") for line in lines)


def _utterance(text: str) -> str:
    return " ".join(text.split())


def _utterance_lines(blob: object) -> list[str]:
    if not isinstance(blob, str):
        return []
    lines = []
    for line in blob.splitlines():
        text = _utterance(line)
        if text:
            lines.append(text)
    return lines
