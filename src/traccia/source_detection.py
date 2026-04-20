from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from traccia.models import SourceFamily

GOOGLE_TAKEOUT_MARKERS = (
    "archive_browser.html",
    "takeout/",
    "my activity/",
    "youtube and youtube music/",
    "chrome/",
    "location history/",
)

TWITTER_ARCHIVE_MARKERS = (
    "your archive.html",
    "data/account.js",
    "data/tweet.js",
    "data/tweets.js",
    "data/tweets-part",
    "data/direct-messages.js",
    "data/follower.js",
    "data/following.js",
)

DISCORD_DATA_PACKAGE_MARKERS = (
    "account/user.json",
    "messages/index.json",
    "servers/index.json",
    "messages/",
)

REDDIT_EXPORT_MARKERS = (
    "conversations.json",
    "comments.csv",
    "posts.csv",
    "saved_posts.csv",
    "saved_comments.csv",
    "upvoted_posts.csv",
    "upvoted_comments.csv",
)


@dataclass(slots=True)
class FamilyDetection:
    source_family: SourceFamily
    reason: str


def detect_source_family_from_path(path: Path) -> FamilyDetection:
    return detect_source_family_from_names([path.as_posix()])


def detect_source_family_from_archive(path: Path) -> FamilyDetection:
    with ZipFile(path) as archive:
        return detect_source_family_from_names(info.filename for info in archive.infolist())


def detect_source_family_from_names(names: list[str] | tuple[str, ...] | object) -> FamilyDetection:
    lowered_names = [str(name).lower() for name in names]

    family = _match_markers(lowered_names, GOOGLE_TAKEOUT_MARKERS)
    if family:
        return FamilyDetection(
            source_family=SourceFamily.GOOGLE_TAKEOUT,
            reason=f"matched Google Takeout marker: {family}",
        )

    family = _match_markers(lowered_names, TWITTER_ARCHIVE_MARKERS)
    if family:
        return FamilyDetection(
            source_family=SourceFamily.TWITTER_ARCHIVE,
            reason=f"matched Twitter archive marker: {family}",
        )

    family = _match_markers(lowered_names, DISCORD_DATA_PACKAGE_MARKERS)
    if family:
        return FamilyDetection(
            source_family=SourceFamily.DISCORD_DATA_PACKAGE,
            reason=f"matched Discord data package marker: {family}",
        )

    family = _match_markers(lowered_names, REDDIT_EXPORT_MARKERS)
    if family:
        return FamilyDetection(
            source_family=SourceFamily.REDDIT_EXPORT,
            reason=f"matched Reddit export marker: {family}",
        )

    return FamilyDetection(
        source_family=SourceFamily.GENERIC,
        reason="no export-family marker matched; using generic ingest path",
    )


def _match_markers(names: list[str], markers: tuple[str, ...]) -> str | None:
    for marker in markers:
        for name in names:
            if marker in name:
                return marker
    return None
