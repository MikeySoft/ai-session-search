# flake8: noqa: E501
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sessions.fzf import PREVIEW_AWK, SWITCH_SH, copy_resume, fzf_command, fzf_rows
from sessions.group import RepoGroup
from sessions.model import Session


NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


def test_fzf_command_puts_the_command_in_a_short_strip_under_the_list(tmp_path: Path):
    command = fzf_command(
        switch=tmp_path / "switch.sh",
        preview=tmp_path / "preview.awk",
        marker=tmp_path / "mode",
        recent=tmp_path / "recent.tsv",
        everything=tmp_path / "all.tsv",
    )
    assert command[:5] == ["fzf", "--delimiter", "\t", "--with-nth", "1"]
    assert command[command.index("--accept-nth") + 1] == "2"
    assert command[command.index("--layout") + 1] == "reverse"
    assert command[command.index("--no-hscroll") + 1] == "--ghost"
    assert command[command.index("--preview-window") + 1] == (
        "down,4,wrap,wrap-word,border-line,noinfo"
    )
    assert "awk -v query=" in command[command.index("--preview") + 1]
    assert "{3}" in command[command.index("--preview") + 1]
    assert "ctrl-y:execute-silent(sessions --copy-resume {2})" in command
    assert "change:transform:" in command[-1]


def test_fzf_rows_align_the_list_and_keep_the_resume_line():
    short = Session(
        "claude",
        "abc",
        Path("/work/my repo"),
        "fix\tbug",
        NOW - timedelta(minutes=5),
    )
    long = Session(
        "opencode",
        "ses_1",
        Path("/work/other"),
        "x" * 80,
        NOW - timedelta(hours=2),
    )
    text = fzf_rows(
        [
            RepoGroup(Path("/repo"), (short,)),
            RepoGroup(Path("/repo/much-longer"), (long,)),
        ],
        now=NOW,
        zone=timezone.utc,
    )
    first, second = (line.split("\t") for line in text.rstrip("\n").split("\n"))
    header = command_header()
    display, resume, _body = first
    assert resume == "cd '/work/my repo' && claude --resume abc"
    assert second[1] == "cd /work/other && opencode --session ses_1"
    assert display.index("claude") == header.index("tool")
    assert display.index("5m ago") == header.index("age")
    assert display.index("11-19 11:55") == header.index("when")
    assert display.index("fix bug") == header.index("title")
    assert display.index("/repo") == header.index("repo")
    assert second[0].index("/repo/much-longer") == header.index("repo")
    assert "…" in second[0]
    assert "x" * 40 not in second[0]


def command_header() -> str:
    command = fzf_command(
        switch=Path("switch.sh"),
        preview=Path("preview.awk"),
        marker=Path("mode"),
        recent=Path("recent.tsv"),
        everything=Path("all.tsv"),
    )
    return command[command.index("--header") + 1]


def test_fzf_rows_keep_conversation_text_past_the_table(tmp_path: Path):
    session = Session("opencode", "ses_1", Path("/work"), "planning", NOW)
    text = fzf_rows(
        [RepoGroup(Path("/repo"), (session,))],
        now=NOW,
        zone=timezone.utc,
        speech={("opencode", "ses_1"): ("cherry-pick the commit",)},
        body_dir=tmp_path,
    )
    display, _resume, body = text.rstrip("\n").split("\t")
    assert display.index("cherry-pick the commit") >= 1000
    assert "cherry-pick" not in display[:200]
    written = Path(body).read_text(encoding="utf-8")
    assert written == "cherry-pick the commit\n"


def test_copy_resume_prints_when_pbcopy_fails(capsys):
    class Result:
        returncode = 1

    def runner(argv, input, text, capture_output):
        assert argv == ["pbcopy"]
        assert input == "cd /work && claude --resume abc"
        return Result()

    assert copy_resume("cd /work && claude --resume abc", runner=runner) == 0
    assert capsys.readouterr().err == "cd /work && claude --resume abc\n"
