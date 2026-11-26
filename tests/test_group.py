from datetime import datetime, timedelta, timezone
from pathlib import Path

from sessions.group import RepoGroup, git_toplevel, group_sessions
from sessions.model import Session


NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


def session(tool, sid, directory, hours_ago, title="title"):
    updated = NOW - timedelta(hours=hours_ago)
    return Session(tool, sid, Path(directory), title, updated)


def test_window_git_root_and_sort():
    sessions = [
        session("claude", "old", "/repo/sub", 24 * 8),
        session("agy", "a", "/repo/sub", 2),
        session("opencode", "b", "/repo", 1),
        session("claude", "c", "/scratch", 3),
    ]

    def toplevel(directory: Path) -> Path:
        if str(directory).startswith("/repo"):
            return Path("/repo")
        return directory

    groups = group_sessions(
        sessions,
        cutoff=datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc),
        toplevel=toplevel,
    )
    assert groups == [
        RepoGroup(
            Path("/repo"),
            (
                session("opencode", "b", "/repo", 1),
                session("agy", "a", "/repo/sub", 2),
            ),
        ),
        RepoGroup(Path("/scratch"), (session("claude", "c", "/scratch", 3),)),
    ]


def test_recorded_directory_is_kept_when_toplevel_returns_it():
    lone = session("claude", "c", "/missing", 1)
    groups = group_sessions(
        [lone],
        cutoff=NOW - timedelta(days=7),
        toplevel=lambda directory: directory,
    )
    assert groups[0].repo == Path("/missing")
    assert groups[0].sessions[0].directory == Path("/missing")


def test_git_toplevel_of_a_non_repo_is_the_directory(tmp_path: Path):
    assert git_toplevel(tmp_path) == tmp_path
