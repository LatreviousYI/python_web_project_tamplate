import json
from collections import Counter
from collections.abc import Iterable

from vorm import Session, col

from apps.model.post import Post
from apps.model.project_center import Project


def count_tags(tag_lists: Iterable) -> list[dict]:
    """Count each normalized tag once per content item, preserving a display name."""
    counts: Counter[str] = Counter()
    names: dict[str, str] = {}
    for tags in tag_lists:
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except (ValueError, TypeError):
                continue
        if not isinstance(tags, list):
            continue
        seen: set[str] = set()
        for value in tags:
            if not isinstance(value, str) or not value.strip():
                continue
            name = value.strip()
            key = name.casefold()
            names.setdefault(key, name)
            seen.add(key)
        counts.update(seen)
    return [
        {"tag": names[key], "count": count}
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


async def tag_suggestions(session: Session, keyword: str | None = None, limit: int = 20) -> list[dict]:
    posts = await session.query(Post).filter(Post.status == "published").order_by(col(Post.id).asc()).select(col(Post.tags)).all()
    projects = await (
        session.query(Project)
        .filter(Project.is_deleted == False)  # noqa: E712
        .order_by(col(Project.id).asc())
        .select(col(Project.tags))
        .all()
    )
    topics = count_tags(row["tags"] for row in [*posts, *projects])
    search = (keyword or "").strip().casefold()
    if search:
        topics = [topic for topic in topics if search in topic["tag"].casefold()]
        topics.sort(key=lambda topic: (
            topic["tag"].casefold() != search,
            not topic["tag"].casefold().startswith(search),
            -topic["count"],
            topic["tag"].casefold(),
        ))
    return topics[:limit]
