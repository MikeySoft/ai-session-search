# flake8: noqa: E501
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sessions.cli import main


NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
OLD = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)


def claude_home(home: Path, when: str = "2026-11-19T11:00:00Z") -> None:
    sid = "11111111-1111-1111-1111-111111111111"
    path = home / ".claude" / "projects" / "demo" / f"{sid}.jsonl"
    path.parent.mkdir(parents=True)
    record = {"type": "user", "sessionId": sid, "cwd": "/work", "timestamp": when, "message": {"content": "ship it"}}
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")


def opencode_db(home: Path) -> None:
    path = home / ".local" / "share" / "opencode" / "opencode.db"
    path.parent.mkdir(parents=True)
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE session_v2 (id text, title text, directory text, time_updated integer, time_archived integer)"
    )
    connection.execute(
        "INSERT INTO session_v2 VALUES ('ses_1', 'live', '/work', ?, NULL)",
        (int(OLD.timestamp() * 1000),),
    )
    connection.commit()
    connection.close()


def test_prints_a_session_and_warns_for_missing_tools(tmp_path: Path, capsys):
    claude_home(tmp_path)
    code = main(["--since", "7d"], now=NOW, home=tmp_path)
    captured = capsys.readouterr()
    assert code == 0
    assert "ship it" in captured.out
    assert "cd /work && claude --resume 11111111-1111-1111-1111-111111111111" in captured.out
    assert "opencode: session store not found" in captured.err
    assert "agy: session store not found" in captured.err


def test_empty_window(tmp_path: Path, capsys):
    claude_home(tmp_path, when="2026-10-01T00:00:00Z")
    opencode_db(tmp_path)
    agy = tmp_path / ".gemini" / "antigravity-cli" / "conversation_summaries.db"
    agy.parent.mkdir(parents=True)
    connection = sqlite3.connect(agy)
    connection.execute(
        """
        CREATE TABLE conversation_summaries (
            conversation_id text, title text, last_modified_time text,
            workspace_uris text, nesting_depth integer
        )
        """
    )
    connection.commit()
    connection.close()
    code = main([], now=NOW, home=tmp_path)
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == "no sessions in the last 7d\n"
    assert captured.err == ""


def test_all_adapters_missing(tmp_path: Path, capsys):
    code = main([], now=NOW, home=tmp_path)
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert "claude: session store not found" in captured.err
    assert "opencode: session store not found" in captured.err
    assert "agy: session store not found" in captured.err


def test_bad_since(tmp_path: Path, capsys):
    code = main(["--since", "7w"], now=NOW, home=tmp_path)
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert "usage: sessions [--since 7d] [tui]" in captured.err


def test_tui_execs_the_accepted_line(tmp_path: Path, capsys):
    claude_home(tmp_path)
    seen = {}

    class Result:
        returncode = 0
        stdout = "cd /work && claude --resume abc\n"

    def runner(argv, input, text, **kwargs):
        seen["argv"] = argv
        seen["input"] = input
        return Result()

    def exec_command(program, args):
        seen["exec"] = (program, args)

    code = main(["tui"], now=NOW, home=tmp_path, runner=runner, exec_command=exec_command)
    assert code == 0
    assert seen["argv"][0] == "fzf"
    assert "claude" in seen["input"]
    assert seen["exec"] == ("sh", ["sh", "-c", "cd /work && claude --resume abc"])
    assert capsys.readouterr().out == ""


def test_tui_without_fzf_prints_the_list(tmp_path: Path, capsys):
    claude_home(tmp_path)

    def runner(argv, input, text, **kwargs):
        raise FileNotFoundError(argv[0])

    code = main(["tui"], now=NOW, home=tmp_path, runner=runner, exec_command=lambda *args: None)
    captured = capsys.readouterr()
    assert code == 0
    assert "ship it" in captured.out
    assert "fzf: command not found" in captured.err


def test_tui_search_list_includes_sessions_outside_the_window(tmp_path: Path):
    claude_home(tmp_path, when="2026-10-01T00:00:00Z")
    seen = {}

    class Result:
        returncode = 0
        stdout = ""

    def runner(argv, input, text, **kwargs):
        seen["input"] = input
        bind = next(arg for arg in argv if arg.startswith("change:transform:"))
        everything = bind.split()[2]
        seen["everything"] = Path(everything).read_text(encoding="utf-8")
        return Result()

    code = main(["tui"], now=NOW, home=tmp_path, runner=runner, exec_command=lambda *args: None)
    assert code == 0
    assert seen["input"] == ""
    assert "ship it" in seen["everything"]


def test_copy_resume_flag(tmp_path: Path, capsys):
    class Result:
        returncode = 0

    def runner(argv, input, text, capture_output):
        assert input == "cd /work && claude --resume abc"
        return Result()

    code = main(
        ["--copy-resume", "cd /work && claude --resume abc"],
        now=NOW,
        home=tmp_path,
        runner=runner,
    )
    assert code == 0
    assert capsys.readouterr().out == ""
