# flake8: noqa: E501
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sessions.adapters.opencode import load_opencode
from sessions.model import AdapterError


def build_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE session_v2 (
            id text PRIMARY KEY,
            title text,
            directory text NOT NULL,
            time_updated integer NOT NULL,
            time_archived integer
        )
        """
    )
    connection.executemany(
        "INSERT INTO session_v2 (id, title, directory, time_updated, time_archived) VALUES (?, ?, ?, ?, ?)",
        [
            ("ses_live", "ESB work", "/work/gia", 1795078525587, None),
            ("ses_old", "", "/work/gia", 1795000000000, None),
            ("ses_arch", "archived", "/work/gia", 1795078525587, 1795070000000),
        ],
    )
    connection.commit()
    connection.close()


def test_reads_unarchived_rows(tmp_path: Path):
    db_path = tmp_path / "opencode.db"
    build_db(db_path)
    sessions = {session.id: session for session in load_opencode(db_path)}
    assert set(sessions) == {"ses_live", "ses_old"}
    assert sessions["ses_live"].tool == "opencode"
    assert sessions["ses_live"].title == "ESB work"
    assert sessions["ses_live"].directory == Path("/work/gia")
    assert sessions["ses_live"].updated == datetime.fromtimestamp(1795078525587 / 1000, timezone.utc)
    assert sessions["ses_old"].title == "untitled"


def test_missing_database(tmp_path: Path):
    with pytest.raises(AdapterError) as caught:
        load_opencode(tmp_path / "missing.db")
    assert str(caught.value) == "session store not found"
