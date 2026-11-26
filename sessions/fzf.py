import subprocess
import sys
from datetime import datetime, tzinfo
from pathlib import Path

from sessions.group import RepoGroup
from sessions.model import Session, resume_line
from sessions.print import age_label
from sessions.speech import search_blob

_TOOL = 8
_AGE = 8
_WHEN = 11
_TITLE = 40
_PAD = 1000

SWITCH_SH = r"""#!/bin/sh
set -eu
marker=$1
everything=$2
recent=$3
mode=recent
if [ -n "${FZF_QUERY:-}" ]; then
  mode=all
fi
prev=$(cat "$marker")
if [ "$prev" = "$mode" ]; then
  exit 0
fi
printf '%s\n' "$mode" > "$marker"
if [ "$mode" = all ]; then
  printf 'reload-sync(cat %s)\n' "$everything"
else
  printf 'reload-sync(cat %s)\n' "$recent"
fi
"""

PREVIEW_AWK = r"""BEGIN {
    if (query == "" || file == "") {
        print cmd
        exit
    }
    q = tolower(query)
    n = split(q, raw, /[[:space:]]+/)
    nt = 0
    for (i = 1; i <= n; i++) {
        if (raw[i] != "") {
            nt++
            terms[nt] = raw[i]
        }
    }
    found = ""
    while ((getline line < file) > 0) {
        low = tolower(line)
        ok = 1
        for (i = 1; i <= nt; i++) {
            if (index(low, terms[i]) == 0) {
                ok = 0
                break
            }
        }
        if (ok) {
            found = line
            break
        }
    }
    close(file)
    if (found != "") {
        if (length(found) > 240) {
            found = substr(found, 1, 239) "..."
        }
        print found
    }
    print cmd
}
"""


def list_header() -> str:
    return (
        f"{'tool':<{_TOOL}}  "
        f"{'age':<{_AGE}}  "
        f"{'when':<{_WHEN}}  "
        f"{'title':<{_TITLE}}  "
        "repo"
    )


def fzf_command(
    *,
    switch: Path,
    preview: Path,
    marker: Path,
    recent: Path,
    everything: Path,
) -> list[str]:
    switch_args = f"{switch} {marker} {everything} {recent}"
    preview_cmd = (
        'awk -v query="$FZF_QUERY" -v file={3} -v cmd={2} -f ' + str(preview)
    )
    return [
        "fzf",
        "--delimiter",
        "\t",
        "--with-nth",
        "1",
        "--accept-nth",
        "2",
        "--layout",
        "reverse",
        "--tiebreak",
        "index",
        "--no-hscroll",
        "--ghost",
        "search every session",
        "--header",
        list_header(),
        "--header-border",
        "line",
        # fzf quotes placeholders, so they must not be wrapped in quotes.
        "--preview",
        preview_cmd,
        "--preview-window",
        "down,4,wrap,wrap-word,border-line,noinfo",
        "--bind",
        "ctrl-y:execute-silent(sessions --copy-resume {2})",
        "--bind",
        f"change:transform:{switch_args}",
    ]


def fzf_rows(
    groups: list[RepoGroup],
    *,
    now: datetime,
    zone: tzinfo | None = None,
    speech: dict[tuple[str, str], tuple[str, ...]] | None = None,
    body_dir: Path | None = None,
) -> str:
    if zone is None:
        zone = datetime.now().astimezone().tzinfo
    spoken = speech or {}
    lines = []
    for group in groups:
        repo = _plain(str(group.repo))
        for session in group.sessions:
            lines.append(
                _row(session, now, zone, repo, spoken, body_dir)
            )
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def copy_resume(text: str, runner=subprocess.run) -> int:
    try:
        result = runner(["pbcopy"], input=text, text=True, capture_output=True)
    except FileNotFoundError:
        print(text, file=sys.stderr)
        return 0
    if result.returncode != 0:
        print(text, file=sys.stderr)
    return 0


def _row(
    session: Session,
    now: datetime,
    zone: tzinfo,
    repo: str,
    speech: dict[tuple[str, str], tuple[str, ...]],
    body_dir: Path | None,
) -> str:
    visible = _display(session, now, zone, repo)
    lines = speech.get((session.tool, session.id), ())
    blob = search_blob(lines)
    if len(visible) < _PAD:
        searchable = visible.ljust(_PAD) + blob
    else:
        searchable = visible + "  " + blob
    body = ""
    if body_dir is not None and lines:
        path = _body_file(body_dir, session)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        body = str(path)
    return f"{searchable}\t{resume_line(session)}\t{body}"


def _body_file(body_dir: Path, session: Session) -> Path:
    safe = "".join(
        char if char.isalnum() or char in "-_" else "_" for char in session.id
    )
    return body_dir / f"{session.tool}-{safe}.txt"


def _display(session: Session, now: datetime, zone: tzinfo, repo: str) -> str:
    stamp = session.updated.astimezone(zone).strftime("%m-%d %H:%M")
    return (
        f"{_cell(session.tool, _TOOL)}  "
        f"{_cell(age_label(session.updated, now), _AGE)}  "
        f"{_cell(stamp, _WHEN)}  "
        f"{_cell(session.title, _TITLE)}  "
        f"{repo}"
    )


def _cell(text: str, width: int) -> str:
    cleaned = _plain(text)
    if len(cleaned) <= width:
        return cleaned.ljust(width)
    if width <= 1:
        return cleaned[:width]
    return cleaned[: width - 1] + "…"


def _plain(text: str) -> str:
    return " ".join(text.replace("\t", " ").splitlines())
