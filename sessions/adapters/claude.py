import json
from datetime import datetime, timezone
from pathlib import Path

from sessions.model import AdapterError, Session, one_line


def load_claude(root: Path) -> list[Session]:
    projects = root / "projects"
    if not projects.is_dir():
        raise AdapterError("claude", "session store not found")
    history = _history_titles(root / "history.jsonl")
    sessions = []
    for path in sorted(projects.rglob("*.jsonl")):
        session = _session_from_transcript(path, history)
        if session is not None:
            sessions.append(session)
    return sessions


def _history_titles(path: Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    if not path.is_file():
        return titles
    for obj in _objects(path):
        session_id = obj.get("sessionId")
        if not isinstance(session_id, str) or session_id in titles:
            continue
        title = one_line(str(obj.get("display") or ""))
        if title:
            titles[session_id] = title
    return titles


def _session_from_transcript(
    path: Path, history: dict[str, str]
) -> Session | None:
    file_id = path.stem
    cwd = ""
    updated: datetime | None = None
    custom = ""
    user_title = ""
    for obj in _objects(path):
        if obj.get("isSidechain") is True:
            continue
        session_id = obj.get("sessionId")
        if isinstance(session_id, str) and session_id != file_id:
            continue
        if not cwd and isinstance(obj.get("cwd"), str):
            cwd = obj["cwd"]
        parsed = _parse_time(obj.get("timestamp"))
        if parsed is not None and (updated is None or parsed > updated):
            updated = parsed
        if obj.get("type") == "custom-title":
            title = one_line(str(obj.get("customTitle") or ""))
            if title:
                custom = title
        if obj.get("type") == "user" and not user_title:
            user_title = one_line(_message_text(obj))
    if not cwd or updated is None:
        return None
    title = custom or history.get(file_id) or user_title or "untitled"
    return Session("claude", file_id, Path(cwd), title[:100], updated)


def _message_text(obj: dict) -> str:
    message = obj.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for part in content:
            if (
                isinstance(part, dict)
                and part.get("type") == "text"
                and isinstance(part.get("text"), str)
            ):
                chunks.append(part["text"])
        return "\n".join(chunks)
    return ""


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _objects(path: Path) -> list[dict]:
    objects = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return objects
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            objects.append(obj)
    return objects
