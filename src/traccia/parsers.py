from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from pypdf import PdfReader

from traccia.models import (
    ParsedDocument,
    ParsedSpan,
    Sensitivity,
    SourceCategory,
    SourceDocument,
    SourceStatus,
    SourceType,
)
from traccia.utils import file_sha256, now_utc, short_hash, source_id_for_relative_path

SUPPORTED_EXTENSIONS = {
    ".md": SourceType.MARKDOWN,
    ".markdown": SourceType.MARKDOWN,
    ".txt": SourceType.TEXT,
    ".py": SourceType.CODE,
    ".js": SourceType.CODE,
    ".ts": SourceType.CODE,
    ".tsx": SourceType.CODE,
    ".rs": SourceType.CODE,
    ".go": SourceType.CODE,
    ".sql": SourceType.CODE,
    ".json": SourceType.JSON,
    ".csv": SourceType.CSV,
    ".pdf": SourceType.PDF,
    ".docx": SourceType.DOCX,
}


@dataclass(slots=True)
class SourceMaterial:
    path: Path
    relative_import_path: Path


@dataclass(slots=True)
class ParsedSourceContent:
    text: str
    spans: list[ParsedSpan]
    source_type: SourceType
    source_category: SourceCategory
    parser: str
    title: str | None
    created_at: datetime | None
    metadata: dict[str, Any]


def supported_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def detect_source_type(path: Path) -> SourceType:
    return SUPPORTED_EXTENSIONS[path.suffix.lower()]


def parse_document(path: Path, *, project_relative_path: Path) -> ParsedDocument:
    source_id = source_id_for_relative_path(project_relative_path)
    parsed_source = _parse_source_content(
        path=path,
        project_relative_path=project_relative_path,
        source_id=source_id,
    )
    source = SourceDocument(
        source_id=source_id,
        uri=path.resolve().as_uri(),
        source_type=parsed_source.source_type,
        source_category=parsed_source.source_category,
        parser=parsed_source.parser,
        sha256=file_sha256(path),
        created_at=parsed_source.created_at or datetime_or_none(path.stat().st_mtime),
        ingested_at=now_utc(),
        title=parsed_source.title or path.stem.replace("-", " ").replace("_", " ").title(),
        language=_guess_language(path),
        sensitivity=Sensitivity.PRIVATE,
        metadata={
            "relative_import_path": project_relative_path.as_posix(),
            "filename": path.name,
            **parsed_source.metadata,
            "classification_reason": _classification_reason(
                path=path,
                project_relative_path=project_relative_path,
                source_category=parsed_source.source_category,
            ),
        },
        status=SourceStatus.ACTIVE,
    )
    return ParsedDocument(source=source, text=parsed_source.text, spans=parsed_source.spans)


def _parse_source_content(
    *,
    path: Path,
    project_relative_path: Path,
    source_id: str,
) -> ParsedSourceContent:
    source_type = detect_source_type(path)
    if source_type == SourceType.JSON:
        payload = json.loads(path.read_text(encoding="utf-8"))
        structured = _parse_structured_json_source(
            payload=payload,
            path=path,
            project_relative_path=project_relative_path,
            source_id=source_id,
        )
        if structured:
            return structured
        text = json.dumps(payload, indent=2, sort_keys=True)
    else:
        text = _read_text(path, source_type)

    source_category = _classify_source_category(
        path=path,
        project_relative_path=project_relative_path,
        source_type=source_type,
        text=text,
    )
    return ParsedSourceContent(
        text=text,
        spans=_segment_text(text=text, source_id=source_id),
        source_type=source_type,
        source_category=source_category,
        parser=_parser_name(source_type),
        title=None,
        created_at=None,
        metadata={},
    )


def _read_text(path: Path, source_type: SourceType) -> str:
    if source_type in {SourceType.MARKDOWN, SourceType.TEXT, SourceType.CODE}:
        return path.read_text(encoding="utf-8")
    if source_type == SourceType.JSON:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return json.dumps(payload, indent=2, sort_keys=True)
    if source_type == SourceType.CSV:
        rows: list[str] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append(", ".join(f"{key}={value}" for key, value in row.items()))
        return "\n".join(rows)
    if source_type == SourceType.PDF:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if source_type == SourceType.DOCX:
        document = DocxDocument(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError(f"Unsupported source type: {source_type}")


def _parser_name(source_type: SourceType) -> str:
    return {
        SourceType.MARKDOWN: "markdown",
        SourceType.TEXT: "text",
        SourceType.CODE: "code",
        SourceType.JSON: "json",
        SourceType.CSV: "csv",
        SourceType.PDF: "pypdf",
        SourceType.DOCX: "python-docx",
        SourceType.CHAT: "chat",
        SourceType.BOOKMARKS: "bookmarks",
        SourceType.CALENDAR: "calendar",
        SourceType.ISSUE_TRACKER: "issue-tracker",
        SourceType.PORTFOLIO: "portfolio",
        SourceType.SLIDES: "slides",
        SourceType.IMAGE: "image",
    }[source_type]


def _guess_language(path: Path) -> str | None:
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".rs": "rust",
        ".go": "go",
        ".sql": "sql",
        ".md": "markdown",
        ".markdown": "markdown",
        ".json": "json",
        ".csv": "csv",
    }.get(path.suffix.lower())


def _segment_text(*, text: str, source_id: str) -> list[ParsedSpan]:
    spans: list[ParsedSpan] = []
    if not text.strip():
        return spans

    cursor = 0
    for block in [segment.strip() for segment in text.split("\n\n") if segment.strip()]:
        block_start = text.find(block, cursor)
        block_heading = block.splitlines()[0].lstrip("# ").strip() if block.startswith("#") else None
        inner_cursor = block_start
        for line in [item.strip() for item in block.splitlines() if item.strip()]:
            start = text.find(line, inner_cursor)
            end = start + len(line)
            line_start = text[:start].count("\n") + 1
            line_end = line_start + line.count("\n")
            heading = line.lstrip("# ").strip() if line.startswith("#") else block_heading
            spans.append(
                ParsedSpan(
                    span_id=f"span_{short_hash(f'{source_id}:{start}:{end}', length=10)}",
                    source_id=source_id,
                    segment_kind="line",
                    heading=heading or None,
                    text=line,
                    span_start=start,
                    span_end=end,
                    line_start=line_start,
                    line_end=line_end,
                )
            )
            inner_cursor = end
        cursor = block_start + len(block)

    return spans


def datetime_or_none(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return now_utc().fromtimestamp(timestamp, tz=now_utc().tzinfo).isoformat()


def _parse_structured_json_source(
    *,
    payload: object,
    path: Path,
    project_relative_path: Path,
    source_id: str,
) -> ParsedSourceContent | None:
    lowered_path = project_relative_path.as_posix().lower()
    filename = path.name.lower()

    if _looks_like_ai_conversation_export(payload=payload, lowered_path=lowered_path, filename=filename):
        return _parse_ai_conversation_export(payload=payload, source_id=source_id)
    if _looks_like_reddit_export(payload=payload, lowered_path=lowered_path, filename=filename):
        return _parse_reddit_export(payload=payload, source_id=source_id)
    if _looks_like_google_activity_export(payload=payload, lowered_path=lowered_path, filename=filename):
        return _parse_google_activity_export(payload=payload, source_id=source_id)
    return None


def _looks_like_ai_conversation_export(*, payload: object, lowered_path: str, filename: str) -> bool:
    if any(token in lowered_path or token in filename for token in ("chatgpt", "claude", "gemini", "assistant", "conversation")):
        if isinstance(payload, dict) and isinstance(payload.get("messages"), list):
            return True
    if isinstance(payload, dict) and isinstance(payload.get("messages"), list):
        return any(_coerce_message_text(message.get("content")) for message in payload["messages"] if isinstance(message, dict))
    return False


def _looks_like_reddit_export(*, payload: object, lowered_path: str, filename: str) -> bool:
    if any(token in lowered_path or token in filename for token in ("reddit", "subreddit")):
        if isinstance(payload, dict) and any(isinstance(payload.get(key), list) for key in ("posts", "comments")):
            return True
    if not isinstance(payload, dict):
        return False
    posts = payload.get("posts")
    comments = payload.get("comments")
    return any(
        isinstance(item, dict) and item.get("subreddit") and (item.get("title") or item.get("body"))
        for collection in (posts, comments)
        if isinstance(collection, list)
        for item in collection
    )


def _looks_like_google_activity_export(*, payload: object, lowered_path: str, filename: str) -> bool:
    if any(token in lowered_path or token in filename for token in ("google", "takeout", "activity", "search-history")):
        if isinstance(payload, list):
            return any(isinstance(item, dict) and (item.get("header") or item.get("titleUrl")) for item in payload)
    return isinstance(payload, list) and any(
        isinstance(item, dict) and item.get("time") and (item.get("header") or item.get("titleUrl"))
        for item in payload
    )


def _parse_ai_conversation_export(*, payload: object, source_id: str) -> ParsedSourceContent:
    if not isinstance(payload, dict):
        raise ValueError("AI conversation payload must be an object")
    messages = payload.get("messages")
    if not isinstance(messages, list):
        raise ValueError("AI conversation payload must contain a messages list")

    entries: list[dict[str, str]] = []
    timestamps: list[datetime] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = _coerce_message_text(message.get("content"))
        if not content:
            continue
        role = str(message.get("role") or message.get("author") or "unknown").strip().lower()
        entries.append(
            {
                "heading": role,
                "text": f"{role.title()}: {content}",
            }
        )
        parsed_timestamp = _coerce_datetime(message.get("created_at") or message.get("timestamp"))
        if parsed_timestamp:
            timestamps.append(parsed_timestamp)

    text, spans = _build_structured_spans(entries=entries, source_id=source_id)
    return ParsedSourceContent(
        text=text,
        spans=spans,
        source_type=SourceType.CHAT,
        source_category=SourceCategory.AI_DIALOGUE,
        parser="ai-conversation-json",
        title=str(payload.get("title") or "AI Conversation").strip(),
        created_at=max(timestamps) if timestamps else None,
        metadata={
            "structured_export_kind": "ai_conversation",
            "message_count": len(entries),
        },
    )


def _parse_reddit_export(*, payload: object, source_id: str) -> ParsedSourceContent:
    if not isinstance(payload, dict):
        raise ValueError("Reddit export payload must be an object")

    entries: list[dict[str, str]] = []
    timestamps: list[datetime] = []
    post_count = 0
    comment_count = 0

    for post in payload.get("posts", []):
        if not isinstance(post, dict):
            continue
        subreddit = str(post.get("subreddit") or "unknown").strip()
        title = str(post.get("title") or "").strip()
        body = str(post.get("selftext") or post.get("body") or "").strip()
        if not title and not body:
            continue
        entries.append(
            {
                "heading": f"r/{subreddit}",
                "text": _join_parts(
                    [
                        f"Reddit post in r/{subreddit}",
                        title,
                        body,
                    ]
                ),
            }
        )
        post_count += 1
        parsed_timestamp = _coerce_datetime(post.get("created_at")) or _coerce_unix_datetime(post.get("created_utc"))
        if parsed_timestamp:
            timestamps.append(parsed_timestamp)

    for comment in payload.get("comments", []):
        if not isinstance(comment, dict):
            continue
        subreddit = str(comment.get("subreddit") or "unknown").strip()
        body = str(comment.get("body") or "").strip()
        if not body:
            continue
        entries.append(
            {
                "heading": f"r/{subreddit}",
                "text": _join_parts(
                    [
                        f"Reddit comment in r/{subreddit}",
                        body,
                    ]
                ),
            }
        )
        comment_count += 1
        parsed_timestamp = _coerce_datetime(comment.get("created_at")) or _coerce_unix_datetime(comment.get("created_utc"))
        if parsed_timestamp:
            timestamps.append(parsed_timestamp)

    text, spans = _build_structured_spans(entries=entries, source_id=source_id)
    return ParsedSourceContent(
        text=text,
        spans=spans,
        source_type=SourceType.JSON,
        source_category=SourceCategory.SOCIAL_OR_COMMUNITY_TRACE,
        parser="reddit-export-json",
        title="Reddit Export",
        created_at=max(timestamps) if timestamps else None,
        metadata={
            "structured_export_kind": "reddit_activity",
            "post_count": post_count,
            "comment_count": comment_count,
        },
    )


def _parse_google_activity_export(*, payload: object, source_id: str) -> ParsedSourceContent:
    if not isinstance(payload, list):
        raise ValueError("Google activity payload must be a list")

    entries: list[dict[str, str]] = []
    timestamps: list[datetime] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        header = str(item.get("header") or "activity").strip()
        title = str(item.get("title") or "").strip()
        url = str(item.get("titleUrl") or item.get("url") or "").strip()
        if not title and not url:
            continue
        entries.append(
            {
                "heading": header.lower(),
                "text": _join_parts([header, title, url]),
            }
        )
        parsed_timestamp = _coerce_datetime(item.get("time"))
        if parsed_timestamp:
            timestamps.append(parsed_timestamp)

    text, spans = _build_structured_spans(entries=entries, source_id=source_id)
    return ParsedSourceContent(
        text=text,
        spans=spans,
        source_type=SourceType.JSON,
        source_category=SourceCategory.PLATFORM_EXPORT_ACTIVITY,
        parser="google-activity-json",
        title="Google Activity Export",
        created_at=max(timestamps) if timestamps else None,
        metadata={
            "structured_export_kind": "google_activity",
            "activity_count": len(entries),
        },
    )


def _build_structured_spans(*, entries: list[dict[str, str]], source_id: str) -> tuple[str, list[ParsedSpan]]:
    text = "\n\n".join(entry["text"] for entry in entries)
    spans: list[ParsedSpan] = []
    cursor = 0
    for index, entry in enumerate(entries):
        if not entry["text"]:
            continue
        start = text.find(entry["text"], cursor)
        end = start + len(entry["text"])
        line_start = text[:start].count("\n") + 1
        line_end = line_start + entry["text"].count("\n")
        spans.append(
            ParsedSpan(
                span_id=f"span_{short_hash(f'{source_id}:structured:{index}:{start}:{end}', length=10)}",
                source_id=source_id,
                segment_kind="structured_entry",
                heading=entry.get("heading") or None,
                text=entry["text"],
                span_start=start,
                span_end=end,
                line_start=line_start,
                line_end=line_end,
            )
        )
        cursor = end
    return text, spans


def _coerce_message_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                text_value = item.get("text") or item.get("content")
                if isinstance(text_value, str) and text_value.strip():
                    parts.append(text_value.strip())
        return " ".join(parts).strip()
    if isinstance(content, dict):
        for key in ("text", "content", "body", "value"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if isinstance(content.get("parts"), list):
            return _coerce_message_text(content["parts"])
    return ""


def _coerce_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw_value = value.strip()
    if raw_value.endswith("Z"):
        raw_value = raw_value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw_value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _coerce_unix_datetime(value: object) -> datetime | None:
    if isinstance(value, str) and value.isdigit():
        value = int(value)
    if not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(float(value), tz=UTC)


def _join_parts(parts: list[str]) -> str:
    return ". ".join(part.strip() for part in parts if part and part.strip())


def _classify_source_category(
    *,
    path: Path,
    project_relative_path: Path,
    source_type: SourceType,
    text: str,
) -> SourceCategory:
    del text
    lowered_path = project_relative_path.as_posix().lower()
    filename = path.name.lower()

    if any(token in lowered_path or token in filename for token in ("chatgpt", "claude", "gemini", "assistant", "ai-chat", "conversation")):
        return SourceCategory.AI_DIALOGUE
    if any(token in lowered_path or token in filename for token in ("reddit", "twitter", "tweet", "x-", "mastodon", "forum", "discord", "slack", "social", "profile", "linkedin")):
        return SourceCategory.SOCIAL_OR_COMMUNITY_TRACE
    if any(token in lowered_path or token in filename for token in ("takeout", "export", "search", "history", "activity", "browser", "watch-history", "bookmarks")):
        return SourceCategory.PLATFORM_EXPORT_ACTIVITY
    if any(token in lowered_path or token in filename for token in ("issue", "ticket", "review", "pull-request", "pr-", "standup", "retro", "meeting")):
        return SourceCategory.COLLABORATION_TRACE
    if source_type == SourceType.CODE:
        return SourceCategory.PRODUCED_ARTIFACT
    if source_type in {SourceType.JSON, SourceType.CSV}:
        return SourceCategory.METADATA_ONLY_ACTIVITY
    if source_type in {SourceType.MARKDOWN, SourceType.TEXT, SourceType.DOCX, SourceType.PDF}:
        return SourceCategory.AUTHORED_CONTENT
    return SourceCategory.AUTHORED_CONTENT


def _classification_reason(
    *,
    path: Path,
    project_relative_path: Path,
    source_category: SourceCategory,
) -> str:
    return (
        f"classified_as={source_category.value} "
        f"from path={project_relative_path.as_posix()} filename={path.name}"
    )
