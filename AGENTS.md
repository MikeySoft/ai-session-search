# sessions

`sessions` lists recent Claude Code, OpenCode, and agy conversations grouped by git repo. `sessions tui` is an fzf picker. An empty query shows the recent window. Any query searches titles, repos, and what the user and the assistant wrote, including sessions older than that window.

The design is `docs/superpowers/specs/2026-11-19-sessions-design.md`. The original build plan is `docs/superpowers/plans/2026-11-19-sessions.md`. When they disagree, the code and the spec's fzf section win. The plan is the history of the first build.

## Layout

- `sessions/adapters/` reads each tool's own files. One adapter failure warns on stderr and the others continue. All three failing exits 1.
- `sessions/speech.py` loads prompts and replies for the picker only. Tool output, diffs, file contents, and reasoning stay out.
- `sessions/group.py` rolls a directory up to `git rev-parse --show-toplevel`. The resume line still `cd`s to the directory the tool recorded.
- `sessions/fzf.py` builds the picker. fzf placeholders such as `{2}` are already shell-quoted. Do not wrap them in extra quotes.
- `tests/` uses fixtures. Tests do not read `~/.claude`, the OpenCode database, or the agy database, and they do not launch those CLIs or fzf.

## Commands

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

Runtime imports are the Python standard library. pytest and setuptools are for install and tests. flake8's line length is 79.

The installed script's first line points at this virtualenv. `~/.local/bin/sessions` is a symlink to `.venv/bin/sessions`. Recreate that link after recreating `.venv`. The picker calls `sessions` by name for ctrl-y.

## Boundaries

Each run reads the three stores and keeps nothing of its own. Picker bodies go in a temp directory and are deleted before the process is replaced by the resume command. Do not add a local index, and do not commit `.venv`, caches, or conversation text.
