from datetime import timedelta, timezone, datetime
from pathlib import Path

import pytest

from sessions.model import (
    AdapterError,
    Session,
    one_line,
    parse_since,
    resume_line,
)


def test_parse_since_hours_and_days():
    assert parse_since("24h") == timedelta(hours=24)
    assert parse_since("7d") == timedelta(days=7)


@pytest.mark.parametrize("value", ["", "7", "7w", "0d", "-1h", "7.5d"])
def test_parse_since_rejects(value):
    with pytest.raises(ValueError):
        parse_since(value)


def test_one_line_collapses_and_discards_slash_commands():
    assert one_line("  fix\tthe   bug\nmore") == "fix the bug"
    assert one_line("/exit") == ""
    assert one_line("   ") == ""
    assert len(one_line("x" * 120)) == 100


def test_resume_line_quotes_directory_and_id():
    session = Session(
        tool="claude",
        id="abc def",
        directory=Path("/tmp/my repo"),
        title="untitled",
        updated=datetime(2026, 11, 19, tzinfo=timezone.utc),
    )
    expected = "cd '/tmp/my repo' && claude --resume 'abc def'"
    assert resume_line(session) == expected


def test_resume_line_for_each_tool():
    updated = datetime(2026, 11, 19, tzinfo=timezone.utc)
    opencode = Session("opencode", "ses_1", Path("/work"), "t", updated)
    agy = Session("agy", "conv_1", Path("/work"), "t", updated)
    assert resume_line(opencode) == "cd /work && opencode --session ses_1"
    assert resume_line(agy) == "cd /work && agy --conversation conv_1"


def test_adapter_error_string_is_the_message():
    err = AdapterError("opencode", "database is locked")
    assert err.tool == "opencode"
    assert str(err) == "database is locked"
