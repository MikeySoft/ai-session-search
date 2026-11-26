import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sessions.adapters.agy import load_agy
from sessions.adapters.claude import load_claude
from sessions.adapters.opencode import load_opencode
from sessions.fzf import (
    PREVIEW_AWK,
    SWITCH_SH,
    copy_resume,
    fzf_command,
    fzf_rows,
)
from sessions.group import clip_groups, group_sessions
from sessions.model import AdapterError, parse_since
from sessions.paths import default_paths
from sessions.print import render
from sessions.speech import agy_speech, claude_speech, opencode_speech

USAGE = "usage: sessions [--since 7d] [tui]"


def main(
    argv: list[str] | None = None,
    *,
    now: datetime | None = None,
    home: Path | None = None,
    runner=subprocess.run,
    exec_command=os.execvp,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--copy-resume":
        return copy_resume(" ".join(args[1:]), runner=runner)
    since = "7d"
    mode = ""
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--since":
            if index + 1 >= len(args):
                print(USAGE, file=sys.stderr)
                return 1
            since = args[index + 1]
            index += 2
            continue
        if arg == "tui" and mode == "":
            mode = "tui"
            index += 1
            continue
        print(USAGE, file=sys.stderr)
        return 1
    try:
        window = parse_since(since)
    except ValueError:
        print(USAGE, file=sys.stderr)
        return 1
    current = now or datetime.now(timezone.utc)
    paths = default_paths(home)
    sessions, warnings, failures = _collect(paths)
    for warning in warnings:
        print(warning, file=sys.stderr)
    if failures == 3:
        return 1
    cutoff = current - window
    if mode == "tui":
        everything = group_sessions(
            sessions, cutoff=datetime.fromtimestamp(0, timezone.utc)
        )
        if not everything:
            sys.stdout.write(render([], now=current, since_label=since))
            return 0
        return _tui(
            recent=clip_groups(everything, cutoff),
            everything=everything,
            now=current,
            since=since,
            paths=paths,
            runner=runner,
            exec_command=exec_command,
        )
    groups = group_sessions(sessions, cutoff=cutoff)
    sys.stdout.write(render(groups, now=current, since_label=since))
    return 0


def _tui(
    *,
    recent,
    everything,
    now: datetime,
    since: str,
    paths: dict[str, Path],
    runner,
    exec_command,
) -> int:
    speech = _speech(paths)
    root = Path(tempfile.mkdtemp(prefix="sessions-"))
    try:
        recent_path = root / "recent.tsv"
        everything_path = root / "all.tsv"
        marker = root / "mode"
        preview = root / "preview.awk"
        switch = root / "switch.sh"
        bodies = root / "bodies"
        bodies.mkdir()
        recent_path.write_text(
            fzf_rows(recent, now=now, speech=speech, body_dir=bodies),
            encoding="utf-8",
        )
        everything_path.write_text(
            fzf_rows(everything, now=now, speech=speech, body_dir=bodies),
            encoding="utf-8",
        )
        marker.write_text("recent\n", encoding="utf-8")
        preview.write_text(PREVIEW_AWK, encoding="utf-8")
        switch.write_text(SWITCH_SH, encoding="utf-8")
        switch.chmod(0o755)
        command = fzf_command(
            switch=switch,
            preview=preview,
            marker=marker,
            recent=recent_path,
            everything=everything_path,
        )
        try:
            completed = runner(
                command,
                input=recent_path.read_text(encoding="utf-8"),
                text=True,
                stdout=subprocess.PIPE,
            )
        except FileNotFoundError:
            sys.stdout.write(render(recent, now=now, since_label=since))
            print("fzf: command not found", file=sys.stderr)
            return 0
        if completed.returncode == 0 and completed.stdout:
            if completed.stdout.endswith("\n"):
                line = completed.stdout[:-1]
            else:
                line = completed.stdout
            shutil.rmtree(root, ignore_errors=True)
            exec_command("sh", ["sh", "-c", line])
            return 0
        if completed.returncode in (0, 1, 130):
            return 0
        return completed.returncode
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _speech(paths: dict[str, Path]) -> dict[tuple[str, str], tuple[str, ...]]:
    found: dict[tuple[str, str], tuple[str, ...]] = {}
    loaders = (
        ("claude", lambda: claude_speech(paths["claude"])),
        ("opencode", lambda: opencode_speech(paths["opencode"])),
        ("agy", lambda: agy_speech(paths["agy"])),
    )
    for tool, loader in loaders:
        try:
            spoken = loader()
        except OSError:
            spoken = {}
        for session_id, lines in spoken.items():
            found[(tool, session_id)] = lines
    return found


def _collect(paths: dict[str, Path]) -> tuple[list, list[str], int]:
    loaders = (
        ("claude", lambda: load_claude(paths["claude"])),
        ("opencode", lambda: load_opencode(paths["opencode"])),
        ("agy", lambda: load_agy(paths["agy"])),
    )
    sessions = []
    warnings = []
    failures = 0
    for _name, loader in loaders:
        try:
            sessions.extend(loader())
        except AdapterError as err:
            failures += 1
            warnings.append(f"{err.tool}: {err.message}")
    return sessions, warnings, failures
