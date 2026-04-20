from __future__ import annotations

import zipfile
from pathlib import Path

from traccia.models import SourceFamily
from traccia.source_detection import (
    detect_source_family_from_archive,
    detect_source_family_from_path,
)


def test_detect_source_family_from_path_matches_google_takeout() -> None:
    detection = detect_source_family_from_path(
        Path("Takeout/My Activity/Chrome/MyActivity.html")
    )

    assert detection.source_family == SourceFamily.GOOGLE_TAKEOUT
    assert "Google Takeout" in detection.reason
    assert detection.subproduct == "my-activity"


def test_detect_source_family_from_path_matches_provider_root_folder() -> None:
    detection = detect_source_family_from_path(Path("Google/localizacion.txt"))

    assert detection.source_family == SourceFamily.GOOGLE_TAKEOUT
    assert "Google Takeout" in detection.reason


def test_detect_source_family_from_path_falls_back_to_generic() -> None:
    detection = detect_source_family_from_path(Path("notes/random-export.txt"))

    assert detection.source_family == SourceFamily.GENERIC
    assert "generic ingest path" in detection.reason


def test_detect_source_family_from_archive_matches_twitter_archive(tmp_path: Path) -> None:
    archive_path = tmp_path / "twitter-export.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("data/account.js", 'window.YTD.account.part0 = [{"account": {}}];\n')

    detection = detect_source_family_from_archive(archive_path)

    assert detection.source_family == SourceFamily.TWITTER_ARCHIVE
    assert "data/account.js" in detection.reason
    assert detection.subproduct == "account"


def test_detect_source_family_from_path_matches_instagram_export() -> None:
    detection = detect_source_family_from_path(
        Path("Instagram/messages/inbox/thread_1/message_1.json")
    )

    assert detection.source_family == SourceFamily.INSTAGRAM_EXPORT
    assert "Instagram export" in detection.reason
    assert detection.subproduct == "messages"


def test_detect_source_family_from_path_matches_facebook_export() -> None:
    detection = detect_source_family_from_path(
        Path("Facebook/your_facebook_activity/posts/your_posts_1.json")
    )

    assert detection.source_family == SourceFamily.FACEBOOK_EXPORT
    assert "Facebook export" in detection.reason
    assert detection.subproduct == "your-facebook-activity"
