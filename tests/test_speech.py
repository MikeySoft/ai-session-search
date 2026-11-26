# flake8: noqa: E501
import json
import sqlite3
import subprocess
from pathlib import Path

from sessions.fzf import PREVIEW_AWK, SWITCH_SH
from sessions.speech import agy_speech, claude_speech, opencode_speech


def test_claude_speech_keeps_prompts_and_replies(tmp_path: Path):
    sid = "11111111-1111-1111-1111-111111111111"
    path = tmp_path / "projects" / "demo" / f"{sid}.jsonl"
    path.parent.mkdir(parents=True)
    records = [
        {
            "type": "user",
            "sessionId": sid,
            "message": {
                "content": [
                    {"type": "text", "text": "cherry pick this"},
                    {"type": "tool_result", "content": "SECRET TOOL OUTPUT"},
                ]
            },
        },
        {
            "type": "assistant",
            "sessionId": sid,
            "message": {
                "content": [
                    {"type": "text", "text": "the promote branch is ready"},
                    {"type": "thinking", "thinking": "hidden reasoning"},
                ]
            },
        },
    ]
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    assert claude_speech(tmp_path) == {
        sid: ("cherry pick this", "the promote branch is ready")
    }


def test_opencode_speech_skips_tool_parts(tmp_path: Path):
    path = tmp_path / "opencode.db"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE message (id text, data text)")
    connection.execute(
        "CREATE TABLE part (id text, message_id text, session_id text, time_created integer, data text)"
    )
    connection.execute(
        "INSERT INTO message VALUES ('m1', ?)",
        (json.dumps({"role": "user"}),),
    )
    connection.execute(
        "INSERT INTO message VALUES ('m2', ?)",
        (json.dumps({"role": "assistant"}),),
    )
    connection.execute(
        "INSERT INTO part VALUES ('p1', 'm1', 'ses_1', 1, ?)",
        (json.dumps({"type": "text", "text": "selective promotion"}),),
    )
    connection.execute(
        "INSERT INTO part VALUES ('p2', 'm2', 'ses_1', 2, ?)",
        (json.dumps({"type": "text", "text": "cherry-pick the commit"}),),
    )
    connection.execute(
        "INSERT INTO part VALUES ('p3', 'm2', 'ses_1', 3, ?)",
        (json.dumps({"type": "tool", "text": "deploy.yaml contents"}),),
    )
    connection.commit()
    connection.close()
    assert opencode_speech(path) == {
        "ses_1": ("selective promotion", "cherry-pick the commit")
    }


def test_agy_speech_reads_the_full_text_index(tmp_path: Path):
    path = tmp_path / "conversation_summaries.db"
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE conversations_fts (
            conversation_id text, chunk_index integer, user_body text, agent_body text
        )
        """
    )
    connection.execute(
        "INSERT INTO conversations_fts VALUES ('conv', 0, ?, ?)",
        ("promote the branch\n", "cherry-pick is in place"),
    )
    connection.commit()
    connection.close()
    assert agy_speech(path) == {"conv": ("promote the branch", "cherry-pick is in place")}


def test_missing_speech_tables_are_empty(tmp_path: Path):
    db = tmp_path / "empty.db"
    sqlite3.connect(db).close()
    assert opencode_speech(db) == {}
    assert agy_speech(db) == {}
    assert claude_speech(tmp_path) == {}


def test_preview_prints_the_matching_line_then_the_command(tmp_path: Path):
    body = tmp_path / "body.txt"
    body.write_text("planning the story\ncherry-pick the commit\n", encoding="utf-8")
    script = tmp_path / "preview.awk"
    script.write_text(PREVIEW_AWK, encoding="utf-8")
    result = subprocess.run(
        [
            "awk",
            "-v",
            "query=Cherry",
            "-v",
            f"file={body}",
            "-v",
            "cmd=cd /work && opencode --session ses_1",
            "-f",
            str(script),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "cherry-pick the commit\ncd /work && opencode --session ses_1\n"


def test_switch_reloads_every_session_only_when_the_query_starts(tmp_path: Path):
    marker = tmp_path / "mode"
    recent = tmp_path / "recent.tsv"
    everything = tmp_path / "all.tsv"
    script = tmp_path / "switch.sh"
    marker.write_text("recent\n", encoding="utf-8")
    script.write_text(SWITCH_SH, encoding="utf-8")
    script.chmod(0o755)
    started = subprocess.run(
        [str(script), str(marker), str(everything), str(recent)],
        check=False,
        capture_output=True,
        text=True,
        env={"FZF_QUERY": "cherry"},
    )
    assert started.stdout == f"reload-sync(cat {everything})\n"
    again = subprocess.run(
        [str(script), str(marker), str(everything), str(recent)],
        check=False,
        capture_output=True,
        text=True,
        env={"FZF_QUERY": "cherry-pick"},
    )
    assert again.stdout == ""
    cleared = subprocess.run(
        [str(script), str(marker), str(everything), str(recent)],
        check=False,
        capture_output=True,
        text=True,
        env={"FZF_QUERY": ""},
    )
    assert cleared.stdout == f"reload-sync(cat {recent})\n"
