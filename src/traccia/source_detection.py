from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from traccia.models import SourceFamily

GOOGLE_TAKEOUT_MARKERS = (
    "google/",
    "archive_browser.html",
    "takeout/",
    "my activity/",
    "youtube and youtube music/",
    "chrome/",
    "location history/",
)

TWITTER_ARCHIVE_MARKERS = (
    "twitter/",
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
    "discord/",
    "account/user.json",
    "messages/index.json",
    "servers/index.json",
)

REDDIT_EXPORT_MARKERS = (
    "reddit/",
    "conversations.json",
    "comments.csv",
    "posts.csv",
    "saved_posts.csv",
    "saved_comments.csv",
    "upvoted_posts.csv",
    "upvoted_comments.csv",
)

INSTAGRAM_EXPORT_MARKERS = (
    "instagram/",
    "followers_and_following/",
    "your_instagram_activity/",
    "photos_and_videos/",
)

FACEBOOK_EXPORT_MARKERS = (
    "facebook/",
    "your_facebook_activity/",
)

GOOGLE_SUBPRODUCT_MARKERS = (
    ("my activity/", "my-activity"),
    ("youtube and youtube music/", "youtube-and-youtube-music"),
    ("chrome/", "chrome"),
    ("location history/", "location-history"),
)

TWITTER_SUBPRODUCT_MARKERS = (
    ("data/account.js", "account"),
    ("data/tweet.js", "tweets"),
    ("data/tweets.js", "tweets"),
    ("data/tweets-part", "tweets"),
    ("data/direct-messages.js", "direct-messages"),
    ("data/follower.js", "followers"),
    ("data/following.js", "following"),
)

DISCORD_SUBPRODUCT_MARKERS = (
    ("account/user.json", "account"),
    ("messages/index.json", "messages"),
    ("messages/", "messages"),
    ("servers/index.json", "servers"),
)

REDDIT_SUBPRODUCT_MARKERS = (
    ("conversations.json", "conversations"),
    ("comments.csv", "comments"),
    ("posts.csv", "posts"),
    ("saved_posts.csv", "saved-posts"),
    ("saved_comments.csv", "saved-comments"),
    ("upvoted_posts.csv", "upvoted-posts"),
    ("upvoted_comments.csv", "upvoted-comments"),
    ("messages_archive.csv", "messages-archive"),
    ("chat_history.csv", "chat-history"),
)

INSTAGRAM_SUBPRODUCT_MARKERS = (
    ("profile_information/", "profile-information"),
    ("followers_and_following/", "followers-and-following"),
    ("your_instagram_activity/", "your-instagram-activity"),
    ("photos_and_videos/", "photos-and-videos"),
    ("messages/", "messages"),
)

FACEBOOK_SUBPRODUCT_MARKERS = (
    ("your_facebook_activity/", "your-facebook-activity"),
    ("profile_information/", "profile-information"),
    ("friends/", "friends"),
    ("groups/", "groups"),
    ("messages/", "messages"),
)


@dataclass(slots=True)
class FamilyRule:
    source_family: SourceFamily
    display_name: str
    markers: tuple[str, ...]
    subproduct_markers: tuple[tuple[str, str], ...]


FAMILY_RULES = (
    FamilyRule(
        source_family=SourceFamily.GOOGLE_TAKEOUT,
        display_name="Google Takeout",
        markers=GOOGLE_TAKEOUT_MARKERS,
        subproduct_markers=GOOGLE_SUBPRODUCT_MARKERS,
    ),
    FamilyRule(
        source_family=SourceFamily.TWITTER_ARCHIVE,
        display_name="Twitter archive",
        markers=TWITTER_ARCHIVE_MARKERS,
        subproduct_markers=TWITTER_SUBPRODUCT_MARKERS,
    ),
    FamilyRule(
        source_family=SourceFamily.DISCORD_DATA_PACKAGE,
        display_name="Discord data package",
        markers=DISCORD_DATA_PACKAGE_MARKERS,
        subproduct_markers=DISCORD_SUBPRODUCT_MARKERS,
    ),
    FamilyRule(
        source_family=SourceFamily.REDDIT_EXPORT,
        display_name="Reddit export",
        markers=REDDIT_EXPORT_MARKERS,
        subproduct_markers=REDDIT_SUBPRODUCT_MARKERS,
    ),
    FamilyRule(
        source_family=SourceFamily.INSTAGRAM_EXPORT,
        display_name="Instagram export",
        markers=INSTAGRAM_EXPORT_MARKERS,
        subproduct_markers=INSTAGRAM_SUBPRODUCT_MARKERS,
    ),
    FamilyRule(
        source_family=SourceFamily.FACEBOOK_EXPORT,
        display_name="Facebook export",
        markers=FACEBOOK_EXPORT_MARKERS,
        subproduct_markers=FACEBOOK_SUBPRODUCT_MARKERS,
    ),
)


@dataclass(slots=True)
class FamilyDetection:
    source_family: SourceFamily
    reason: str
    subproduct: str | None = None


def detect_source_family_from_path(path: Path) -> FamilyDetection:
    return detect_source_family_from_names([path.as_posix()])


def detect_source_family_from_archive(path: Path) -> FamilyDetection:
    with ZipFile(path) as archive:
        return detect_source_family_from_names(info.filename for info in archive.infolist())


def detect_source_family_from_names(names: list[str] | tuple[str, ...] | object) -> FamilyDetection:
    lowered_names = [str(name).lower() for name in names]

    for rule in FAMILY_RULES:
        marker = _match_markers(lowered_names, rule.markers)
        if not marker:
            continue
        subproduct = _match_subproduct(lowered_names, rule.subproduct_markers)
        return FamilyDetection(
            source_family=rule.source_family,
            reason=f"matched {rule.display_name} marker: {marker}",
            subproduct=subproduct,
        )

    return FamilyDetection(
        source_family=SourceFamily.GENERIC,
        reason="no export-family marker matched; using generic ingest path",
    )


def refine_archive_member_detection(*, archive_detection: FamilyDetection, member_path: Path) -> FamilyDetection:
    member_detection = detect_source_family_from_path(member_path)
    if archive_detection.source_family == SourceFamily.GENERIC:
        return member_detection
    if member_detection.source_family == archive_detection.source_family:
        return FamilyDetection(
            source_family=archive_detection.source_family,
            reason=member_detection.reason,
            subproduct=member_detection.subproduct or archive_detection.subproduct,
        )
    return FamilyDetection(
        source_family=archive_detection.source_family,
        reason=archive_detection.reason,
        subproduct=_match_subproduct_for_family(
            source_family=archive_detection.source_family,
            names=[member_path.as_posix().lower()],
        )
        or archive_detection.subproduct,
    )


def _match_markers(names: list[str], markers: tuple[str, ...]) -> str | None:
    for marker in markers:
        for name in names:
            if _marker_matches_name(name=name, marker=marker):
                return marker
    return None


def _match_subproduct(names: list[str], markers: tuple[tuple[str, str], ...]) -> str | None:
    for marker, subproduct in markers:
        for name in names:
            if _marker_matches_name(name=name, marker=marker):
                return subproduct
    return None


def _match_subproduct_for_family(*, source_family: SourceFamily, names: list[str]) -> str | None:
    for rule in FAMILY_RULES:
        if rule.source_family != source_family:
            continue
        return _match_subproduct(names, rule.subproduct_markers)
    return None


def _marker_matches_name(*, name: str, marker: str) -> bool:
    normalized_name = name.strip("/")
    normalized_marker = marker.strip("/")
    if marker.endswith("/"):
        return (
            normalized_name == normalized_marker
            or normalized_name.startswith(f"{normalized_marker}/")
            or f"/{normalized_marker}/" in normalized_name
        )
    return marker in name
