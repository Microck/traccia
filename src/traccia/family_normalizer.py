from __future__ import annotations

import csv
import io
import json
import mailbox
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from traccia.models import SourceFamily, SourceType

_META_FAMILY_NAMES = {
    SourceFamily.GOOGLE_TAKEOUT: "Google Takeout",
    SourceFamily.INSTAGRAM_EXPORT: "Instagram export",
    SourceFamily.FACEBOOK_EXPORT: "Facebook export",
    SourceFamily.REDDIT_EXPORT: "Reddit export",
    SourceFamily.TWITTER_ARCHIVE: "Twitter archive",
}

_HTML_EXPORT_FAMILIES = {
    SourceFamily.GOOGLE_TAKEOUT,
    SourceFamily.INSTAGRAM_EXPORT,
    SourceFamily.FACEBOOK_EXPORT,
}

_TWITTER_YTD_ASSIGNMENT = re.compile(
    r"^\s*window\.YTD\.(?P<kind>[a-zA-Z0-9_]+)\.part\d+\s*=\s*",
    re.DOTALL,
)

_SCALAR_FIELD_PRIORITY = (
    "created_at",
    "createdAt",
    "timestamp",
    "time",
    "username",
    "screen_name",
    "name",
    "title",
    "full_text",
    "text",
    "body",
    "selftext",
    "description",
    "url",
    "expanded_url",
    "email",
    "accountId",
)

_WRAPPER_KEYS = (
    "account",
    "tweet",
    "dmConversation",
    "dmMessage",
    "follower",
    "following",
    "like",
    "noteTweet",
)

_MEDIA_SUFFIX_TO_KIND = {
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".webp": "image",
    ".bmp": "image",
    ".svg": "image",
    ".avif": "image",
    ".heic": "image",
    ".heif": "image",
    ".mp4": "video",
    ".mov": "video",
    ".mkv": "video",
    ".webm": "video",
    ".avi": "video",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
    ".ogg": "audio",
    ".flac": "audio",
    ".aac": "audio",
    ".pdf": "document",
}

_ATTACHMENT_LIKE_KEYS = (
    "image",
    "img",
    "photo",
    "video",
    "audio",
    "media",
    "thumbnail",
    "thumb",
    "preview",
    "poster",
    "attachment",
    "asset",
    "icon",
    "cover",
    "banner",
    "src",
)


@dataclass(slots=True)
class FamilyNormalizedContent:
    text: str
    parser: str
    metadata: dict[str, Any]
    title: str | None = None
    created_at: datetime | None = None


def normalize_family_content(
    *,
    path: Path,
    project_relative_path: Path,
    source_type: SourceType,
    source_family: SourceFamily | None,
    source_family_subproduct: str | None,
) -> FamilyNormalizedContent | None:
    if not source_family or source_family == SourceFamily.GENERIC:
        return None

    if (
        source_type == SourceType.TEXT
        and path.suffix.lower() in {".html", ".htm"}
        and source_family in _HTML_EXPORT_FAMILIES
    ):
        return _normalize_export_html(
            path=path,
            project_relative_path=project_relative_path,
            source_family=source_family,
            source_family_subproduct=source_family_subproduct,
        )

    if source_family == SourceFamily.TWITTER_ARCHIVE and path.suffix.lower() == ".js":
        return _normalize_twitter_archive_js(
            path=path,
            project_relative_path=project_relative_path,
            source_family_subproduct=source_family_subproduct,
        )

    if source_family == SourceFamily.REDDIT_EXPORT and source_type == SourceType.CSV:
        return _normalize_reddit_csv(
            path=path,
            project_relative_path=project_relative_path,
            source_family_subproduct=source_family_subproduct,
        )

    if source_family == SourceFamily.GOOGLE_TAKEOUT and source_type == SourceType.CSV:
        return _normalize_google_csv(
            path=path,
            project_relative_path=project_relative_path,
            source_family_subproduct=source_family_subproduct,
        )

    if source_family == SourceFamily.GOOGLE_TAKEOUT and source_type == SourceType.JSON:
        return _normalize_google_json(
            path=path,
            project_relative_path=project_relative_path,
            source_family_subproduct=source_family_subproduct,
        )

    if source_family == SourceFamily.GOOGLE_TAKEOUT and source_type == SourceType.CALENDAR:
        return _normalize_google_calendar(
            path=path,
            project_relative_path=project_relative_path,
            source_family_subproduct=source_family_subproduct,
        )

    if source_family == SourceFamily.GOOGLE_TAKEOUT and source_type == SourceType.TEXT:
        if path.suffix.lower() == ".mbox":
            return _normalize_google_mbox(
                path=path,
                project_relative_path=project_relative_path,
                source_family_subproduct=source_family_subproduct,
            )
        return _normalize_google_text(
            path=path,
            project_relative_path=project_relative_path,
            source_family_subproduct=source_family_subproduct,
        )

    return None


def collect_attachment_references_from_html(raw_html: str) -> list[dict[str, Any]]:
    parser = _StructuredHtmlTextExtractor()
    parser.feed(raw_html)
    return parser.attachment_references()


def _normalize_export_html(
    *,
    path: Path,
    project_relative_path: Path,
    source_family: SourceFamily,
    source_family_subproduct: str | None,
) -> FamilyNormalizedContent:
    parser = _StructuredHtmlTextExtractor()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    body_text = parser.rendered_text()
    header_lines = [
        f"# {_META_FAMILY_NAMES[source_family]}",
        f"relative path: {project_relative_path.as_posix()}",
    ]
    if source_family_subproduct:
        header_lines.append(f"subproduct: {source_family_subproduct}")
    text = "\n".join(header_lines + ["", body_text]).strip()
    metadata = {
        "family_normalizer": "html-export",
        "family_normalizer_record_count": max(1, body_text.count("\n\n") + 1) if body_text else 0,
        "attachment_references": parser.attachment_references(),
    }
    title = next((line for line in body_text.splitlines() if line.strip()), path.stem)
    return FamilyNormalizedContent(
        text=text,
        parser=f"{source_family.value}-html",
        metadata=metadata,
        title=title[:160] if title else None,
    )


def _normalize_twitter_archive_js(
    *,
    path: Path,
    project_relative_path: Path,
    source_family_subproduct: str | None,
) -> FamilyNormalizedContent | None:
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    match = _TWITTER_YTD_ASSIGNMENT.match(raw_text)
    if not match:
        return None

    payload = raw_text[match.end() :].strip().rstrip(";")
    records = json.loads(payload)
    if not isinstance(records, list):
        records = [records]

    record_blocks: list[str] = []
    created_values: list[datetime] = []
    record_count = 0
    attachment_references: list[dict[str, Any]] = []
    for record in records:
        summary = _summarize_record(record)
        if not summary:
            continue
        record_blocks.append(summary)
        attachment_references.extend(_collect_attachment_references_from_object(record))
        created_value = _extract_created_at(record)
        if created_value:
            created_values.append(created_value)
        record_count += 1

    kind = source_family_subproduct or match.group("kind")
    header_lines = [
        "# Twitter archive",
        f"relative path: {project_relative_path.as_posix()}",
        f"subproduct: {kind}",
        "",
    ]
    if not record_blocks:
        record_blocks.append("No records in this archive module.")
    return FamilyNormalizedContent(
        text="\n".join(header_lines + record_blocks).strip(),
        parser="twitter-ytd-json",
        metadata={
            "family_normalizer": "twitter-ytd-js",
            "family_normalizer_record_count": record_count,
            "family_normalizer_kind": kind,
            "attachment_references": _dedupe_attachment_references(attachment_references),
        },
        title=f"Twitter archive {kind}".strip(),
        created_at=min(created_values) if created_values else None,
    )


def _normalize_reddit_csv(
    *,
    path: Path,
    project_relative_path: Path,
    source_family_subproduct: str | None,
) -> FamilyNormalizedContent:
    csv_text = path.read_text(encoding="utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(csv_text))
    record_blocks: list[str] = []
    created_values: list[datetime] = []
    attachment_references: list[dict[str, Any]] = []
    for index, row in enumerate(reader, start=1):
        block = _format_reddit_row(row=row, index=index)
        if not block:
            continue
        record_blocks.append(block)
        attachment_references.extend(
            reference
            for key, value in row.items()
            if (
                reference := _attachment_reference_from_value(
                    value,
                    label=_clean_scalar(row.get("title") or row.get("subject")),
                    contextual_hint=key,
                )
            )
        )
        created_value = _parse_datetime_candidate(
            row.get("created_at") or row.get("created_utc") or row.get("date")
        )
        if created_value:
            created_values.append(created_value)

    header_lines = [
        "# Reddit export",
        f"relative path: {project_relative_path.as_posix()}",
    ]
    if source_family_subproduct:
        header_lines.append(f"subproduct: {source_family_subproduct}")
    text = "\n".join(header_lines + [""] + record_blocks).strip()
    return FamilyNormalizedContent(
        text=text,
        parser="reddit-csv",
        metadata={
            "family_normalizer": "reddit-csv",
            "family_normalizer_record_count": len(record_blocks),
            "attachment_references": _dedupe_attachment_references(attachment_references),
        },
        title=f"Reddit export {source_family_subproduct or path.stem}".strip(),
        created_at=min(created_values) if created_values else None,
    )


def _normalize_google_csv(
    *,
    path: Path,
    project_relative_path: Path,
    source_family_subproduct: str | None,
) -> FamilyNormalizedContent:
    csv_text = path.read_text(encoding="utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(csv_text))
    record_blocks: list[str] = []
    created_values: list[datetime] = []
    attachment_references: list[dict[str, Any]] = []

    for index, row in enumerate(reader, start=1):
        block = _format_google_csv_row(
            row=row,
            index=index,
            project_relative_path=project_relative_path,
        )
        if not block:
            continue
        record_blocks.append(block)
        for key, value in row.items():
            reference = _attachment_reference_from_value(
                value,
                label=_google_csv_row_label(row),
                contextual_hint=key,
            )
            if reference:
                attachment_references.append(reference)
            created_value = _parse_datetime_candidate(value)
            if created_value:
                created_values.append(created_value)

    header_lines = [
        "# Google Takeout",
        f"relative path: {project_relative_path.as_posix()}",
    ]
    if source_family_subproduct:
        header_lines.append(f"subproduct: {source_family_subproduct}")
    text = "\n".join(header_lines + [""] + record_blocks).strip()
    return FamilyNormalizedContent(
        text=text,
        parser="google-takeout-csv",
        metadata={
            "family_normalizer": "google-takeout-csv",
            "family_normalizer_record_count": len(record_blocks),
            "attachment_references": _dedupe_attachment_references(attachment_references),
        },
        title=f"Google Takeout {project_relative_path.stem}".strip(),
        created_at=min(created_values) if created_values else None,
    )


def _normalize_google_json(
    *,
    path: Path,
    project_relative_path: Path,
    source_family_subproduct: str | None,
) -> FamilyNormalizedContent:
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    record_blocks = _format_google_json_blocks(
        payload=payload,
        project_relative_path=project_relative_path,
    )
    created_values = _collect_google_json_created_values(payload)
    attachment_references = _collect_attachment_references_from_object(payload)

    header_lines = [
        "# Google Takeout",
        f"relative path: {project_relative_path.as_posix()}",
    ]
    if source_family_subproduct:
        header_lines.append(f"subproduct: {source_family_subproduct}")
    text = "\n".join(header_lines + [""] + record_blocks).strip()
    return FamilyNormalizedContent(
        text=text,
        parser="google-takeout-json",
        metadata={
            "family_normalizer": "google-takeout-json",
            "family_normalizer_record_count": len(record_blocks),
            "attachment_references": _dedupe_attachment_references(attachment_references),
        },
        title=f"Google Takeout {project_relative_path.stem}".strip(),
        created_at=min(created_values) if created_values else None,
    )


def _normalize_google_calendar(
    *,
    path: Path,
    project_relative_path: Path,
    source_family_subproduct: str | None,
) -> FamilyNormalizedContent:
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    events = _parse_ics_events(raw_text)
    event_blocks: list[str] = []
    created_values: list[datetime] = []
    for index, event in enumerate(events, start=1):
        block = _format_google_calendar_event(event=event, index=index)
        if block:
            event_blocks.append(block)
        for key in ("DTSTART", "CREATED", "LAST-MODIFIED", "DTSTAMP"):
            created_value = _parse_ical_datetime(event.get(key))
            if created_value:
                created_values.append(created_value)

    header_lines = [
        "# Google Takeout",
        f"relative path: {project_relative_path.as_posix()}",
    ]
    if source_family_subproduct:
        header_lines.append(f"subproduct: {source_family_subproduct}")
    text = "\n".join(header_lines + [""] + event_blocks).strip()
    return FamilyNormalizedContent(
        text=text,
        parser="google-takeout-calendar",
        metadata={
            "family_normalizer": "google-takeout-calendar",
            "family_normalizer_record_count": len(event_blocks),
        },
        title=f"Google Takeout {project_relative_path.stem}".strip(),
        created_at=min(created_values) if created_values else None,
    )


def _normalize_google_mbox(
    *,
    path: Path,
    project_relative_path: Path,
    source_family_subproduct: str | None,
) -> FamilyNormalizedContent:
    mbox = mailbox.mbox(path)
    message_blocks: list[str] = []
    created_values: list[datetime] = []

    for index, message in enumerate(mbox, start=1):
        block = _format_google_mbox_message(message=message, index=index)
        if block:
            message_blocks.append(block)
        created_value = _parse_datetime_candidate(message.get("date"))
        if created_value:
            created_values.append(created_value)

    header_lines = [
        "# Google Takeout",
        f"relative path: {project_relative_path.as_posix()}",
    ]
    if source_family_subproduct:
        header_lines.append(f"subproduct: {source_family_subproduct}")
    text = "\n".join(header_lines + [""] + message_blocks).strip()
    return FamilyNormalizedContent(
        text=text,
        parser="google-takeout-mbox",
        metadata={
            "family_normalizer": "google-takeout-mbox",
            "family_normalizer_record_count": len(message_blocks),
        },
        title=f"Google Takeout {project_relative_path.stem}".strip(),
        created_at=min(created_values) if created_values else None,
    )


def _normalize_google_text(
    *,
    path: Path,
    project_relative_path: Path,
    source_family_subproduct: str | None,
) -> FamilyNormalizedContent:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    header_lines = [
        "# Google Takeout",
        f"relative path: {project_relative_path.as_posix()}",
    ]
    if source_family_subproduct:
        header_lines.append(f"subproduct: {source_family_subproduct}")
    normalized_text = "\n".join(header_lines + ["", text]).strip()
    return FamilyNormalizedContent(
        text=normalized_text,
        parser="google-takeout-text",
        metadata={
            "family_normalizer": "google-text",
            "family_normalizer_record_count": 1 if text else 0,
        },
        title=f"Google Takeout {project_relative_path.stem}".strip(),
    )


class _StructuredHtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_tag_stack: list[str] = []
        self._pieces: list[str] = []
        self._attachment_references: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered_tag = tag.lower()
        attr_map = dict(attrs)
        if lowered_tag in {"head", "script", "style", "noscript"}:
            self._ignored_tag_stack.append(lowered_tag)
            return
        if self._ignored_tag_stack:
            return
        if lowered_tag == "img":
            reference = _attachment_reference_from_value(
                attr_map.get("src"),
                label=_clean_scalar(attr_map.get("alt")),
                contextual_hint="img",
            )
            if reference:
                self._attachment_references.append(reference)
        if lowered_tag in {"video", "audio", "source"}:
            reference = _attachment_reference_from_value(
                attr_map.get("src"),
                label=_clean_scalar(attr_map.get("title") or attr_map.get("aria-label")),
                contextual_hint=lowered_tag,
            )
            if reference:
                self._attachment_references.append(reference)
        if lowered_tag == "a":
            href = attr_map.get("href")
            if href and not href.startswith("#"):
                self._pieces.append(f"\n{href}\n")
                reference = _attachment_reference_from_value(
                    href,
                    label=_clean_scalar(attr_map.get("title") or attr_map.get("aria-label")),
                    contextual_hint="a",
                )
                if reference:
                    self._attachment_references.append(reference)
        if lowered_tag in {"br", "div", "p", "li", "tr", "td", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._pieces.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered_tag = tag.lower()
        if self._ignored_tag_stack and self._ignored_tag_stack[-1] == lowered_tag:
            self._ignored_tag_stack.pop()
            return
        if self._ignored_tag_stack:
            return
        if lowered_tag in {"div", "p", "li", "tr", "td", "section", "article"}:
            self._pieces.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_tag_stack:
            return
        cleaned = _normalize_inline_text(data)
        if cleaned:
            self._pieces.append(cleaned)

    def rendered_text(self) -> str:
        rendered = "".join(self._pieces)
        normalized_lines: list[str] = []
        last_line: str | None = None
        for raw_line in rendered.splitlines():
            line = _normalize_inline_text(raw_line)
            if not line:
                if normalized_lines and normalized_lines[-1] != "":
                    normalized_lines.append("")
                last_line = None
                continue
            if line == last_line:
                continue
            normalized_lines.append(line)
            last_line = line
        while normalized_lines and normalized_lines[-1] == "":
            normalized_lines.pop()
        return "\n".join(normalized_lines)

    def attachment_references(self) -> list[dict[str, Any]]:
        return _dedupe_attachment_references(self._attachment_references)


def _format_reddit_row(*, row: dict[str, str | None], index: int) -> str:
    parts: list[str] = [f"record {index}"]
    for key in ("subreddit", "author", "permalink", "created_at", "created_utc"):
        value = _clean_scalar(row.get(key))
        if value:
            parts.append(f"{key}: {value}")
    for key in ("title", "body", "selftext", "message", "subject"):
        value = _clean_scalar(row.get(key))
        if value:
            parts.append(value)
    if len(parts) == 1:
        for key, value in row.items():
            cleaned = _clean_scalar(value)
            if cleaned:
                parts.append(f"{key}: {cleaned}")
    return "\n".join(parts) if len(parts) > 1 else ""


def _format_google_csv_row(
    *,
    row: dict[str, str | None],
    index: int,
    project_relative_path: Path,
) -> str:
    lowered_path = project_relative_path.as_posix().lower()
    if "youtube" in lowered_path:
        return _format_google_youtube_csv_row(row=row, index=index)

    parts = [f"record {index}"]
    for key, value in row.items():
        cleaned = _clean_scalar(value)
        if cleaned:
            parts.append(f"{key}: {cleaned}")
    return "\n".join(parts) if len(parts) > 1 else ""


def _format_google_youtube_csv_row(*, row: dict[str, str | None], index: int) -> str:
    parts = [f"record {index}"]

    channel_title = _row_value_by_aliases(row, "titulo del canal", "channel title")
    channel_url = _row_value_by_aliases(row, "url del canal", "channel url")
    video_title = _row_value_by_aliases(row, "titulo del video original", "video title original")
    video_id = _row_value_by_aliases(row, "id de video", "video id")
    comment_text = _row_value_by_aliases(row, "texto del comentario", "comment text")

    if channel_title:
        parts.append(f"channel: {channel_title}")
    if channel_url:
        parts.append(f"channel_url: {channel_url}")
    if video_title:
        parts.append(f"video_title: {video_title}")
    if video_id:
        parts.append(f"video_id: {video_id}")

    for alias, label in (
        ("marca de tiempo de creacion del comentario", "created_at"),
        ("marca de tiempo de creacion del video", "created_at"),
        ("marca de tiempo de publicacion del video", "published_at"),
        ("categoria del video", "category"),
        ("privacidad", "privacy"),
        ("estado del video", "status"),
        ("id del canal", "channel_id"),
    ):
        value = _row_value_by_aliases(row, alias)
        if value:
            parts.append(f"{label}: {value}")

    if comment_text:
        parts.append(comment_text)

    if len(parts) == 1:
        for key, value in row.items():
            cleaned = _clean_scalar(value)
            if cleaned:
                parts.append(f"{key}: {cleaned}")
    return "\n".join(parts) if len(parts) > 1 else ""


def _google_csv_row_label(row: dict[str, str | None]) -> str | None:
    return (
        _row_value_by_aliases(row, "titulo del canal", "channel title")
        or _row_value_by_aliases(row, "titulo del video original", "video title original")
        or _row_value_by_aliases(row, "id de video", "video id")
        or _row_value_by_aliases(row, "id de comentario", "comment id")
    )


def _row_value_by_aliases(row: dict[str, str | None], *aliases: str) -> str | None:
    alias_set = {_normalize_key(alias) for alias in aliases}
    for key, value in row.items():
        if _normalize_key(key) in alias_set:
            return _clean_scalar(value)
    return None


def _normalize_key(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(character for character in normalized if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).strip()


def _format_google_json_blocks(*, payload: object, project_relative_path: Path) -> list[str]:
    if isinstance(payload, list):
        blocks = [_summarize_record(item) for item in payload[:200]]
        return [block for block in blocks if block]

    if not isinstance(payload, dict):
        return [_clean_scalar(payload) or ""]

    scalar_lines = _collect_scalar_lines(payload)
    list_blocks: list[str] = []
    for key, value in payload.items():
        if isinstance(value, list):
            lines = [f"{key}: {len(value)} items"]
            for item in value[:5]:
                summary = _summarize_record(item)
                if summary:
                    lines.append(summary)
            list_blocks.append("\n".join(lines))
        elif isinstance(value, dict) and key not in {"name", "gender"}:
            nested_lines = _collect_scalar_lines(value, prefix=key)
            if nested_lines:
                list_blocks.append("\n".join(nested_lines))

    blocks = []
    if scalar_lines:
        blocks.append("\n".join(scalar_lines))
    blocks.extend(block for block in list_blocks if block)
    if not blocks:
        blocks.append(f"path: {project_relative_path.as_posix()}")
    return blocks


def _collect_google_json_created_values(payload: object) -> list[datetime]:
    values: list[datetime] = []
    if isinstance(payload, dict):
        created_value = _extract_created_at(payload)
        if created_value:
            values.append(created_value)
        for item in payload.values():
            values.extend(_collect_google_json_created_values(item))
    elif isinstance(payload, list):
        for item in payload[:200]:
            values.extend(_collect_google_json_created_values(item))
    return values


def _parse_ics_events(raw_text: str) -> list[dict[str, str]]:
    unfolded_lines: list[str] = []
    for raw_line in raw_text.splitlines():
        if raw_line.startswith((" ", "\t")) and unfolded_lines:
            unfolded_lines[-1] += raw_line[1:]
        else:
            unfolded_lines.append(raw_line)

    events: list[dict[str, str]] = []
    current_event: dict[str, str] | None = None
    for line in unfolded_lines:
        if line == "BEGIN:VEVENT":
            current_event = {}
            continue
        if line == "END:VEVENT":
            if current_event:
                events.append(current_event)
            current_event = None
            continue
        if current_event is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_event[key.split(";", 1)[0]] = value.strip()
    return events


def _format_google_calendar_event(*, event: dict[str, str], index: int) -> str:
    parts = [f"event {index}"]
    for key, label in (
        ("SUMMARY", "summary"),
        ("DTSTART", "start"),
        ("DTEND", "end"),
        ("DESCRIPTION", "description"),
        ("LOCATION", "location"),
        ("STATUS", "status"),
        ("RRULE", "rrule"),
    ):
        value = _clean_scalar(event.get(key))
        if value:
            parts.append(f"{label}: {value}")
    return "\n".join(parts) if len(parts) > 1 else ""


def _parse_ical_datetime(value: str | None) -> datetime | None:
    cleaned = _clean_scalar(value)
    if not cleaned:
        return None
    if re.fullmatch(r"\d{8}", cleaned):
        return datetime.strptime(cleaned, "%Y%m%d").replace(tzinfo=UTC)
    if cleaned.endswith("Z") and re.fullmatch(r"\d{8}T\d{6}Z", cleaned):
        return datetime.strptime(cleaned, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    return _parse_datetime_candidate(cleaned)


def _format_google_mbox_message(*, message: mailbox.mboxMessage, index: int) -> str:
    parts = [f"message {index}"]
    for header, label in (
        ("date", "date"),
        ("from", "from"),
        ("to", "to"),
        ("subject", "subject"),
    ):
        value = _clean_scalar(message.get(header))
        if value:
            parts.append(f"{label}: {value}")

    snippet = _mbox_body_snippet(message)
    if snippet:
        parts.append(snippet)
    return "\n".join(parts) if len(parts) > 1 else ""


def _mbox_body_snippet(message: mailbox.mboxMessage) -> str | None:
    body = _extract_email_body(message)
    if not body:
        return None
    lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip() and not line.strip().startswith(">")
    ]
    if not lines:
        return None
    return " ".join(lines)[:400]


def _extract_email_body(message: mailbox.mboxMessage) -> str:
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type != "text/plain":
                continue
            try:
                payload = part.get_payload(decode=True)
            except (LookupError, ValueError):
                payload = None
            charset = part.get_content_charset() or "utf-8"
            if isinstance(payload, bytes):
                return payload.decode(charset, errors="replace")
            raw_payload = part.get_payload()
            if isinstance(raw_payload, str):
                return raw_payload
        return ""

    try:
        payload = message.get_payload(decode=True)
    except (LookupError, ValueError):
        payload = None
    charset = message.get_content_charset() or "utf-8"
    if isinstance(payload, bytes):
        return payload.decode(charset, errors="replace")
    raw_payload = message.get_payload()
    return raw_payload if isinstance(raw_payload, str) else ""


def _summarize_record(record: object) -> str:
    candidate = record
    if isinstance(candidate, dict):
        for wrapper_key in _WRAPPER_KEYS:
            nested = candidate.get(wrapper_key)
            if isinstance(nested, dict):
                candidate = nested
                break

    scalar_lines = _collect_scalar_lines(candidate)
    return "\n".join(scalar_lines)


def _collect_scalar_lines(value: object, *, prefix: str | None = None, depth: int = 0) -> list[str]:
    if depth > 3:
        return []
    if isinstance(value, dict):
        preferred_lines: list[str] = []
        used_keys: set[str] = set()
        for key in _SCALAR_FIELD_PRIORITY:
            if key in value:
                cleaned = _clean_scalar(value[key])
                if cleaned:
                    preferred_lines.append(_format_scalar_line(prefix=prefix, key=key, value=cleaned))
                    used_keys.add(key)
        nested_lines: list[str] = []
        for key, nested_value in value.items():
            if key in used_keys:
                continue
            next_prefix = f"{prefix}.{key}" if prefix else key
            nested_lines.extend(_collect_scalar_lines(nested_value, prefix=next_prefix, depth=depth + 1))
            if len(nested_lines) >= 12:
                break
        return preferred_lines + nested_lines
    if isinstance(value, list):
        lines: list[str] = []
        for item in value[:8]:
            lines.extend(_collect_scalar_lines(item, prefix=prefix, depth=depth + 1))
            if len(lines) >= 12:
                break
        return lines
    cleaned = _clean_scalar(value)
    if not cleaned:
        return []
    return [_format_scalar_line(prefix=prefix, key=None, value=cleaned)]


def _format_scalar_line(*, prefix: str | None, key: str | None, value: str) -> str:
    if prefix and key:
        return f"{prefix}.{key}: {value}"
    if prefix:
        return f"{prefix}: {value}"
    if key:
        return f"{key}: {value}"
    return value


def _extract_created_at(record: object) -> datetime | None:
    if isinstance(record, dict):
        for key in ("created_at", "createdAt", "timestamp", "time"):
            created_value = _parse_datetime_candidate(record.get(key))
            if created_value:
                return created_value
        for nested_value in record.values():
            created_value = _extract_created_at(nested_value)
            if created_value:
                return created_value
    if isinstance(record, list):
        for item in record:
            created_value = _extract_created_at(item)
            if created_value:
                return created_value
    return None


def _parse_datetime_candidate(value: object) -> datetime | None:
    if value in {None, ""}:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=UTC)
    raw_value = str(value).strip()
    if not raw_value:
        return None
    if raw_value.isdigit():
        return datetime.fromtimestamp(float(raw_value), tz=UTC)
    normalized = raw_value.replace("Z", "+00:00") if raw_value.endswith("Z") else raw_value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _normalize_inline_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _clean_scalar(value: object) -> str | None:
    if value is None:
        return None
    if value == "":
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        cleaned = _normalize_inline_text(value)
        return cleaned or None
    return None


def _collect_attachment_references_from_object(value: object, *, key_hint: str | None = None) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            references.extend(
                _collect_attachment_references_from_object(nested_value, key_hint=str(key))
            )
        return references
    if isinstance(value, list):
        for item in value:
            references.extend(_collect_attachment_references_from_object(item, key_hint=key_hint))
        return references

    contextual_hint = key_hint.lower() if key_hint else None
    if contextual_hint and not any(token in contextual_hint for token in _ATTACHMENT_LIKE_KEYS):
        return []

    reference = _attachment_reference_from_value(value, contextual_hint=contextual_hint)
    return [reference] if reference else []


def _attachment_reference_from_value(
    value: object,
    *,
    label: str | None = None,
    contextual_hint: str | None = None,
) -> dict[str, Any] | None:
    cleaned = _clean_scalar(value)
    if not cleaned:
        return None

    parsed = urlparse(cleaned)
    candidate_path = parsed.path or cleaned
    suffix = Path(candidate_path).suffix.lower()
    kind = _MEDIA_SUFFIX_TO_KIND.get(suffix)
    if not kind:
        return None

    payload: dict[str, Any] = {
        "reference": cleaned,
        "kind": kind,
    }
    if label:
        payload["label"] = label
    if contextual_hint:
        payload["contextual_hint"] = contextual_hint
    return payload


def _dedupe_attachment_references(references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for reference in references:
        reference_value = str(reference.get("reference") or "")
        kind = str(reference.get("kind") or "")
        if not reference_value or not kind:
            continue
        key = (kind, reference_value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(reference)
    return deduped
