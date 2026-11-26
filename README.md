# sessions

List recent Claude Code, OpenCode, and agy conversations in one place, grouped by the git repo they belong to.

Each run reads the tools' own files. It does not keep a copy of them.

## Prerequisites

- Python 3.11 or newer
- One or more of [Claude Code](https://code.claude.com/docs/en/overview/), [OpenCode](https://opencode.ai), and [agy](https://antigravity.google/product/antigravity-cli/). A missing tool is skipped. The others still list.
- Git, so a session started in a subdirectory is grouped under the repository root
- [fzf](https://github.com/junegunn/fzf) 0.60 or newer, for `sessions tui` (`--accept-nth`)
- `pbcopy`, for copying a resume command from the picker. That ships with macOS.

## Install

From this directory:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Put the command on your `PATH`. `~/.local/bin` is a common place:

```bash
mkdir -p ~/.local/bin
ln -sfn "$(pwd)/.venv/bin/sessions" ~/.local/bin/sessions
```

Add `~/.local/bin` to your `PATH` if it is not there yet. The script's first line points at this project's virtualenv, so `sessions` works from any directory. The fzf picker calls `sessions` by name, which this link satisfies. If you recreate `.venv`, run the link again.

## List

```bash
sessions
```

Shows conversations touched in the last 7 days. Repos are ordered by the newest conversation in each one. Inside a repo, conversations are newest first.

```
~/src/payments  touched 5m ago
  opencode  11-19 09:55  Checkout retry
            cd ~/src/payments && opencode --session ses_123
  claude    11-18 16:02  Adapter work
            cd ~/src/payments/api && claude --resume 11111111-1111-1111-1111-111111111111
```

The path on the first line is the git toplevel. The `cd` uses the directory the tool actually recorded, which may be a subdirectory. Paste that whole line into a terminal to continue.

A repo you started outside any git work tree is grouped under that directory instead.

Change the window with `--since`. The value is a positive number plus `h` or `d`:

```bash
sessions --since 24h
sessions --since 14d
```

Anything else prints `usage: sessions [--since 7d] [tui]` and exits 1.

If nothing was touched in the window, the command prints `no sessions in the last 7d` (or whatever token you passed).

## Pick and resume

```bash
sessions tui
sessions tui --since 24h
```

The list opens on the recent window: tool, age, when, title, and repo. Type in the same box to search every session the tools still have, including ones older than that window. The search covers the title, the repo, and what you and the assistant wrote. Tool output, diffs, and file contents stay out of it.

The strip under the list shows the matching line, then the resume command. Clearing the box returns to the recent list. `--since` changes which sessions are on screen at the start. It does not limit the search.

| Key | Action |
| --- | --- |
| Enter | Run that command. The shell `cd`s to the recorded directory and resumes that conversation. |
| ctrl-y | Copy the command to the clipboard and stay in the picker. |
| Esc or ctrl-c | Leave the picker. |

Enter replaces this process with the tool, the same way running the printed line would.

If fzf is not installed, `sessions tui` prints the list instead and writes `fzf: command not found` to stderr.

## Where the titles and commands come from

| Tool | Resume command | Title |
| --- | --- | --- |
| Claude Code | `claude --resume <id>` | Custom title, otherwise the first real prompt |
| OpenCode | `opencode --session <id>` | The session title |
| agy | `agy --conversation <id>` | The conversation title |

Files read, all under your home directory:

- Claude: `~/.claude/projects/**/*.jsonl` and `~/.claude/history.jsonl`
- OpenCode: `~/.local/share/opencode/opencode.db` (`session_v2`, archived rows omitted)
- agy: `~/.gemini/antigravity-cli/conversation_summaries.db` (top-level conversations only)

A missing or unreadable store prints one line on stderr, such as `opencode: session store not found` or `opencode: database is locked`, and the other tools still appear. If all three stores fail, the command exits 1.

## Docs

The design is in [docs/superpowers/specs/2026-11-19-sessions-design.md](docs/superpowers/specs/2026-11-19-sessions-design.md). The original build plan sits next to it. [AGENTS.md](AGENTS.md) is the guide for coding agents. [CLAUDE.md](CLAUDE.md) imports that file so Claude Code loads the same instructions.

## Tests

```bash
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

## License

MIT. See [LICENSE](LICENSE).
