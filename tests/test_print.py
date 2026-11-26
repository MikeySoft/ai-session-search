# flake8: noqa: E501
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sessions.group import RepoGroup
from sessions.model import Session
from sessions.print import age_label, render


NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


def test_age_labels():
    assert age_label(NOW - timedelta(seconds=30), NOW) == "just now"
    assert age_label(NOW - timedelta(minutes=5), NOW) == "5m ago"
    assert age_label(NOW - timedelta(hours=2), NOW) == "2h ago"
    assert age_label(NOW - timedelta(days=3), NOW) == "3d ago"


def test_render_sections_and_empty_window():
    older = Session("agy", "c1", Path("/repo/sub"), "GCP deploy", NOW - timedelta(hours=2))
    newer = Session("opencode", "ses 1", Path("/repo"), "ESB work", NOW - timedelta(minutes=5))
    text = render(
        [RepoGroup(Path("/repo"), (newer, older))],
        now=NOW,
        since_label="7d",
        zone=timezone.utc,
    )
    assert text == (
        "/repo  touched 5m ago\n"
        "  opencode  11-19 11:55  ESB work\n"
        "            cd /repo && opencode --session 'ses 1'\n"
        "  agy       11-19 10:00  GCP deploy\n"
        "            cd /repo/sub && agy --conversation c1\n"
    )
    assert render([], now=NOW, since_label="24h") == "no sessions in the last 24h\n"
