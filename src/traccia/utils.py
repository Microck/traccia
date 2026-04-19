from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def iso_now() -> str:
    return now_utc().isoformat()


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "item"


def short_hash(value: str, *, length: int = 8) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_id_for_relative_path(relative_path: Path) -> str:
    slug = slugify(relative_path.stem)
    return f"src_{slug}_{short_hash(relative_path.as_posix(), length=6)}"


def skill_id(kind: str, name: str) -> str:
    return f"{kind}.{slugify(name)}"


def sentence_case_summary(lines: list[str]) -> str:
    compact = " ".join(line.strip() for line in lines if line.strip())
    return compact[:320].rstrip()
