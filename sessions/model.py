import re
import shlex
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

_SINCE = re.compile(r"(\d+)([hd])")


@dataclass(frozen=True)
class Session:
    tool: str
    id: str
    directory: Path
    title: str
    updated: datetime


class AdapterError(Exception):
    def __init__(self, tool: str, message: str) -> None:
        super().__init__(message)
        self.tool = tool
        self.message = message


def parse_since(value: str) -> timedelta:
    match = _SINCE.fullmatch(value)
    if match is None:
        raise ValueError(value)
    amount = int(match.group(1))
    if amount < 1:
        raise ValueError(value)
    if match.group(2) == "h":
        return timedelta(hours=amount)
    return timedelta(days=amount)


def one_line(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    line = " ".join(stripped.splitlines()[0].split())
    if not line or line.startswith("/"):
        return ""
    return line[:100]


def resume_line(session: Session) -> str:
    commands = {
        "claude": "claude --resume",
        "opencode": "opencode --session",
        "agy": "agy --conversation",
    }
    command = f"{commands[session.tool]} {shlex.quote(session.id)}"
    return f"cd {shlex.quote(str(session.directory))} && {command}"
