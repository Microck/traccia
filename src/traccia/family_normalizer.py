from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

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

    if source_type == SourceType.TEXT and path.suffix.lower() in {".html", ".htm"}:
        if source_family in _HTML_EXPORT_FAMILIES:
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

    if source_family == SourceFamily.GOOGLE_TAKEOUT and source_type == SourceType.TEXT:
        return _normalize_google_text(
            path=path,
            project_relative_path=project_relative_path,
            source_family_subproduct=source_family_subproduct,
        )

    return None


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
    for record in records:
        summary = _summarize_record(record)
        if not summary:
            continue
        record_blocks.append(summary)
        created_value = _extract_created_at(record)
        if created_value:
            created_values.append(created_value)
        record_count += 1

    if not record_blocks:
        return None

    kind = source_family_subproduct or match.group("kind")
    header_lines = [
        "# Twitter archive",
        f"relative path: {project_relative_path.as_posix()}",
        f"subproduct: {kind}",
        "",
    ]
    return FamilyNormalizedContent(
        text="\n".join(header_lines + record_blocks).strip(),
        parser="twitter-ytd-json",
        metadata={
            "family_normalizer": "twitter-ytd-js",
            "family_normalizer_record_count": record_count,
            "family_normalizer_kind": kind,
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
    for index, row in enumerate(reader, start=1):
        block = _format_reddit_row(row=row, index=index)
        if not block:
            continue
        record_blocks.append(block)
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
        },
        title=f"Reddit export {source_family_subproduct or path.stem}".strip(),
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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered_tag = tag.lower()
        if lowered_tag in {"head", "script", "style", "noscript"}:
            self._ignored_tag_stack.append(lowered_tag)
            return
        if self._ignored_tag_stack:
            return
        if lowered_tag == "a":
            href = dict(attrs).get("href")
            if href and not href.startswith("#"):
                self._pieces.append(f"\n{href}\n")
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
    if value in {None, ""}:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        cleaned = _normalize_inline_text(value)
        return cleaned or None
    return None
