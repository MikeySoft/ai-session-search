# Sessions command

`sessions` prints the Claude Code, OpenCode, and agy conversations touched in a recent window, grouped by git repo. `sessions tui` opens on that same list. Typing in the picker searches every session the tools still have, including ones outside the window. The search covers titles, repos, and what the user and the assistant wrote.

## Command

```
sessions [--since 7d] [tui]
```

`--since` takes a positive integer plus `h` or `d`, for example `24h` or `7d`. The default is `7d`. Any other value prints `usage: sessions [--since 7d] [tui]` to stderr and exits 1. Nothing is read.

The program is Python. Runtime imports are the standard library. pytest runs the tests. setuptools installs the `sessions` console script.

Each run reads the three CLIs and keeps nothing of its own.

## Record

Every adapter produces the same record:

| Field | Meaning |
| --- | --- |
| tool | `claude`, `opencode`, or `agy` |
| id | The id the CLI resumes |
| directory | The directory the CLI recorded. The resume command uses this path, not the git toplevel |
| title | One line, at most 100 characters, internal whitespace collapsed to single spaces |
| updated | Timezone-aware UTC datetime |

A title that is empty or starts with `/` is discarded. The fallback is the next title source, then the literal `untitled`.

The pasteable continue command is one line:

```
cd <quoted directory> && <tool command>
```

Tool commands:

- Claude: `claude --resume <id>`
- OpenCode: `opencode --session <id>`
- agy: `agy --conversation <id>`

`shlex.quote` quotes the directory and the id.

## Stores

Paths are under the current user's home.

**Claude.** `~/.claude/projects/**/*.jsonl` and `~/.claude/history.jsonl`.

- The session id is the transcript filename stem.
- Records with `isSidechain: true` are ignored.
- Records whose `sessionId` is present and different from the filename stem are ignored.
- `directory` is the `cwd` of the first remaining record that has one.
- `updated` is the latest `timestamp` among remaining records. Timestamps look like `2026-11-10T08:18:11.712Z`.
- Title, in order: the last non-empty `customTitle` on a `custom-title` record, the first non-slash `display` for that `sessionId` in `history.jsonl`, the first user message text. User `content` may be a string or a list of `{type: text, text}` parts.
- A JSON line that does not parse is skipped. The rest of the file is kept.
- A transcript with no cwd or no parsed timestamp produces no session.
- If `~/.claude/projects` is missing, the adapter fails. A missing `history.jsonl` only means titles fall back to the transcript.

**OpenCode.** `~/.local/share/opencode/opencode.db`, opened `file:…?mode=ro`.

```sql
SELECT id, title, directory, time_updated
FROM session_v2
WHERE time_archived IS NULL
```

`time_updated` is Unix milliseconds. An empty title becomes `untitled`.

**agy.** `~/.gemini/antigravity-cli/conversation_summaries.db`, opened read-only.

```sql
SELECT conversation_id, title, last_modified_time, workspace_uris
FROM conversation_summaries
WHERE nesting_depth = 0
```

`nesting_depth > 0` rows are child agent runs and are omitted. `last_modified_time` is an ISO datetime. `workspace_uris` is a JSON list of `file://` URIs. The directory is the path of the first URI. A row with no file URI produces no session. An empty title becomes `untitled`.

## Grouping

Keep sessions whose `updated` is greater than or equal to now minus the window.

The repo key is `git -C <directory> rev-parse --show-toplevel`. Git runs once per distinct directory. If git fails, or the directory is not a work tree, the recorded directory is the group.

Repos are ordered by their newest session, newest first. Equal repos are ordered by path. Sessions inside a repo are ordered newest first, then by tool name, then by id.

A directory that no longer exists still appears. The resume line still `cd`s there.

## Printed list

Warnings go to stderr. The list goes to stdout.

One section per repo, a blank line between sections:

```
/path/to/repo  touched 2h ago
  opencode  11-19 09:55  ESB to GIA pattern session
            cd /path/to/repo && opencode --session ses_123
```

The repo age is the age of that repo's newest session: `just now` under 60 seconds, otherwise `Nm ago`, `Nh ago`, or `Nd ago`. The session stamp is the local time `MM-DD HH:MM` of `updated`. The tool name is padded to 8 characters. The command is indented 12 spaces.

An empty window prints `no sessions in the last <token>` and exits 0. `<token>` is the `--since` value, default `7d`.

## Failures

An adapter that cannot read its store appends one stderr line and no rows. The other tools still print. The process exits 0.

| Condition | stderr |
| --- | --- |
| Claude projects directory missing | `claude: session store not found` |
| OpenCode database missing | `opencode: session store not found` |
| OpenCode database locked | `opencode: database is locked` |
| OpenCode database unreadable for another reason | `opencode: unreadable database` |
| agy summary database missing | `agy: session store not found` |
| agy summary database unreadable | `agy: unreadable database` |

If all three adapters fail, the process exits 1 and does not print the empty-window line.

Enter runs the pasteable line with `sh -c`. If that directory is gone, or the CLI rejects the id, the error belongs to that CLI.

## fzf

`sessions tui` opens on the printed window. An empty query shows that window. The first non-empty query reloads every session, including ones older than the window. Clearing the query returns to the window. `--since` changes only the opening list.

Each row is tab-separated: a padded display line, the pasteable command, and a path to a temp file of utterances. fzf searches the display field (`--with-nth 1`). Conversation text is appended after the visible columns and padded so it stays off screen (`--no-hscroll`). The accepted field is the command (`--accept-nth 2`). Tabs inside a title or repo are replaced with spaces.

Speech is what the user typed and what the assistant replied. Tool output, diffs, file contents, and reasoning are left out. Those bodies live in a temp directory and are deleted before the process is replaced by the resume command.

The preview is a short strip under the list. It prints the first utterance that contains every whitespace-separated query term, then the resume command. Enter runs that command with `sh -c`. `ctrl-y` runs `sessions --copy-resume <command>`, which copies it with `pbcopy` and leaves fzf open. If `pbcopy` is missing or returns non-zero, the command is printed to stderr and fzf stays open. `--copy-resume` is the fzf hook, and it exits 0.

If there are no sessions at all, fzf does not open. An empty window still opens the picker when older sessions exist. If fzf is not on `PATH` and there are rows, stdout gets the printed list, stderr gets `fzf: command not found`, and the process exits 0. Esc or ctrl-c in fzf exits 0.

## Tests

Tests use temporary transcripts, a temporary history file, and tiny sqlite databases. They do not read `~/.claude`, the OpenCode database, or the agy database, and they do not launch Claude, OpenCode, agy, or fzf.

Cover the window filter, git toplevel and git failure, sort order, Claude title order, a skipped JSON line, a skipped sidechain record, OpenCode archived rows, agy nested rows, the pasteable command, the printed section, `--since` parsing, the empty window, one adapter failing, all adapters failing, the fzf argv, speech limited to prompts and replies, a query that reloads sessions outside the window, and clipboard failure.

fzf keys and actually resuming a session are a manual pass: open the picker, copy a line with `ctrl-y`, and enter one known session.
