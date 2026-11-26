# flake8: noqa: E501
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sessions.adapters.claude import load_claude
from sessions.model import AdapterError


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def test_title_order_cwd_and_latest_timestamp(tmp_path: Path):
    root = tmp_path / ".claude"
    sid = "11111111-1111-1111-1111-111111111111"
    write_jsonl(
        root / "projects" / "demo" / f"{sid}.jsonl",
        [
            {"type": "user", "sessionId": sid, "cwd": "/work/demo", "timestamp": "2026-11-18T10:00:00.000Z", "isSidechain": False, "message": {"role": "user", "content": "/exit"}},
            {"type": "user", "sessionId": sid, "cwd": "/work/demo", "timestamp": "2026-11-19T09:00:00.000Z", "isSidechain": False, "message": {"role": "user", "content": "fix the adapter"}},
            {"type": "custom-title", "sessionId": sid, "customTitle": "Adapter work"},
            {"type": "user", "sessionId": sid, "isSidechain": True, "cwd": "/elsewhere", "timestamp": "2026-11-19T11:00:00.000Z", "message": {"role": "user", "content": "side"}},
        ],
    )
    transcript = root / "projects" / "demo" / f"{sid}.jsonl"
    transcript.write_text(transcript.read_text(encoding="utf-8") + "not json\n", encoding="utf-8")
    write_jsonl(
        root / "history.jsonl",
        [{"display": "/exit", "sessionId": sid}, {"display": "history title", "sessionId": sid}],
    )
    sessions = load_claude(root)
    assert len(sessions) == 1
    session = sessions[0]
    assert session.tool == "claude"
    assert session.id == sid
    assert session.directory == Path("/work/demo")
    assert session.title == "Adapter work"
    assert session.updated == datetime(2026, 11, 19, 9, 0, tzinfo=timezone.utc)


def test_history_then_user_text_then_untitled(tmp_path: Path):
    root = tmp_path / ".claude"
    history_id = "22222222-2222-2222-2222-222222222222"
    user_id = "33333333-3333-3333-3333-333333333333"
    empty_id = "44444444-4444-4444-4444-444444444444"
    write_jsonl(root / "history.jsonl", [{"display": "from history", "sessionId": history_id}])
    write_jsonl(
        root / "projects" / "demo" / f"{history_id}.jsonl",
        [{"type": "user", "sessionId": history_id, "cwd": "/work", "timestamp": "2026-11-19T08:00:00Z", "message": {"content": "prompt"}}],
    )
    write_jsonl(
        root / "projects" / "demo" / f"{user_id}.jsonl",
        [{"type": "user", "sessionId": user_id, "cwd": "/work", "timestamp": "2026-11-19T08:00:00Z", "message": {"content": [{"type": "text", "text": "block text"}]}}],
    )
    write_jsonl(
        root / "projects" / "demo" / f"{empty_id}.jsonl",
        [{"type": "user", "sessionId": empty_id, "cwd": "/work", "timestamp": "2026-11-19T08:00:00Z", "message": {"content": "/exit"}}],
    )
    titles = {session.id: session.title for session in load_claude(root)}
    assert titles == {history_id: "from history", user_id: "block text", empty_id: "untitled"}


def test_missing_projects_directory(tmp_path: Path):
    with pytest.raises(AdapterError) as caught:
        load_claude(tmp_path / ".claude")
    assert caught.value.tool == "claude"
    assert str(caught.value) == "session store not found"
