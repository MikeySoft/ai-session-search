import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sessions.model import Session


@dataclass(frozen=True)
class RepoGroup:
    repo: Path
    sessions: tuple[Session, ...]


def git_toplevel(directory: Path) -> Path:
    try:
        output = subprocess.check_output(
            ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return directory
    return Path(output.strip())


def group_sessions(
    sessions: list[Session],
    *,
    cutoff: datetime,
    toplevel: Callable[[Path], Path] = git_toplevel,
) -> list[RepoGroup]:
    kept = [session for session in sessions if session.updated >= cutoff]
    cache: dict[Path, Path] = {}

    def repo_of(session: Session) -> Path:
        if session.directory not in cache:
            cache[session.directory] = toplevel(session.directory)
        return cache[session.directory]

    buckets: dict[Path, list[Session]] = {}
    for session in kept:
        buckets.setdefault(repo_of(session), []).append(session)

    def session_order(item: Session) -> tuple:
        return (-item.updated.timestamp(), item.tool, item.id)

    def group_order(group: RepoGroup) -> tuple:
        return (-group.sessions[0].updated.timestamp(), str(group.repo))

    groups = []
    for repo, items in buckets.items():
        ordered = tuple(sorted(items, key=session_order))
        groups.append(RepoGroup(repo, ordered))
    groups.sort(key=group_order)
    return groups


def clip_groups(groups: list[RepoGroup], cutoff: datetime) -> list[RepoGroup]:
    clipped = []
    for group in groups:
        kept = tuple(
            session for session in group.sessions if session.updated >= cutoff
        )
        if kept:
            clipped.append(RepoGroup(group.repo, kept))
    clipped.sort(
        key=lambda group: (
            -group.sessions[0].updated.timestamp(),
            str(group.repo),
        )
    )
    return clipped
