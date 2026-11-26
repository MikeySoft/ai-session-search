# flake8: noqa: E501
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from sessions.adapters.agy import load_agy
from sessions.model import AdapterError


def build_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE conversation_summaries (
            conversation_id text PRIMARY KEY,
            title text NOT NULL DEFAULT '',
            last_modified_time text NOT NULL,
            workspace_uris text NOT NULL,
            nesting_depth integer NOT NULL DEFAULT 0
        )
        """
    )
    connection.executemany(
        """
        INSERT INTO conversation_summaries
            (conversation_id, title, last_modified_time, workspace_uris, nesting_depth)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                "top",
                "GCP deploy",
                "2026-11-18 07:41:43.588206+00:00",
                '["file:///src/payments"]',
                0,
            ),
            (
                "child",
                "",
                "2026-11-18 07:31:37.234668+00:00",
                '["file:///src/payments"]',
                1,
            ),
            (
                "empty-title",
                "",
                "2026-11-18 07:00:00+00:00",
                '["file:///work/app"]',
                0,
            ),
            (
                "no-uri",
                "skip me",
                "2026-11-18 07:00:00+00:00",
                "[]",
                0,
            ),
        ],
    )
    connection.commit()
    connection.close()


def test_top_level_file_uri_and_untitled(tmp_path: Path):
    db_path = tmp_path / "conversation_summaries.db"
    build_db(db_path)
    sessions = {session.id: session for session in load_agy(db_path)}
    assert set(sessions) == {"top", "empty-title"}
    assert sessions["top"].tool == "agy"
    assert sessions["top"].title == "GCP deploy"
    assert sessions["top"].directory == Path("/src/payments")
    assert sessions["top"].updated == datetime.fromisoformat("2026-11-18 07:41:43.588206+00:00")
    assert sessions["empty-title"].title == "untitled"


def test_missing_database(tmp_path: Path):
    with pytest.raises(AdapterError) as caught:
        load_agy(tmp_path / "missing.db")
    assert str(caught.value) == "session store not found"
