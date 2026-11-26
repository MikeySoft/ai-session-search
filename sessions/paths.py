from pathlib import Path


def default_paths(home: Path | None = None) -> dict[str, Path]:
    root = home or Path.home()
    return {
        "claude": root / ".claude",
        "opencode": root / ".local" / "share" / "opencode" / "opencode.db",
        "agy": (
            root / ".gemini" / "antigravity-cli" / "conversation_summaries.db"
        ),
    }
