from datetime import datetime, tzinfo

from sessions.group import RepoGroup
from sessions.model import resume_line


def age_label(then: datetime, now: datetime) -> str:
    seconds = int((now - then).total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def render(
    groups: list[RepoGroup],
    *,
    now: datetime,
    since_label: str,
    zone: tzinfo | None = None,
) -> str:
    if not groups:
        return f"no sessions in the last {since_label}\n"
    if zone is None:
        zone = datetime.now().astimezone().tzinfo
    blocks = []
    for group in groups:
        touched = age_label(group.sessions[0].updated, now)
        lines = [f"{group.repo}  touched {touched}"]
        for session in group.sessions:
            stamp = session.updated.astimezone(zone).strftime("%m-%d %H:%M")
            lines.append(f"  {session.tool:<8}  {stamp}  {session.title}")
            lines.append(f"            {resume_line(session)}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"
