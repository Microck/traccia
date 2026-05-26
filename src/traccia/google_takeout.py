from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from traccia.models import SourceFamily

GOOGLE_PHOTOS_IMAGE_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".heic",
    ".heif",
}

GOOGLE_TAKEOUT_DRIVE_ACCEPT_SUFFIXES = {
    ".csv",
    ".docx",
    ".html",
    ".htm",
    ".ics",
    ".ipynb",
    ".json",
    ".md",
    ".pdf",
    ".py",
    ".sh",
    ".sql",
    ".ts",
    ".txt",
    ".xlsx",
    ".yaml",
    ".yml",
}

GOOGLE_TAKEOUT_DRIVE_SKIP_SUFFIXES = {
    ".7z",
    ".arw",
    ".jar",
    ".mca",
    ".mp4",
    ".osz",
    ".psd",
    ".rar",
    ".zip",
}

LOW_SIGNAL_GOOGLE_TAKEOUT_PATH_MARKERS = (
    "/actividad de registro de accesos/",
    "/alertas/",
    "/aplicacion home/",
    "/contactos/",
    "/cuenta de google/",
    "/encuestas sobre productos de google/",
    "/google finance/",
    "/google play peliculas/",
    "/google play store/",
    "/google shopping/",
    "/google wallet/",
    "/google workspace marketplace/",
    "/google pay/",
    "/google store/",
    "/notificaciones de busqueda/",
    "/perfil/",
    "/perfil de empresa en google/",
    "/servicio de configuracion de dispositivo android/",
    "/correo/configuracion de usuario/",
    "/mi actividad/publicidad/",
    "/mi actividad/takeout/",
)

LOW_SIGNAL_GOOGLE_TAKEOUT_FILE_MARKERS = (
    "/chrome/ajustes del sistema operativo.json",
    "/chrome/configuracion.json",
    "/chrome/direcciones y mas.json",
    "/chrome/informacion de tus dispositivos.json",
)

LOW_SIGNAL_GOOGLE_TAKEOUT_FILENAMES = {
    "archive_browser.html",
    "no-data.txt",
    "no_data.txt",
}

LOW_SIGNAL_GOOGLE_TAKEOUT_PREFIXES = ("weakpass_",)

LOW_SIGNAL_GOOGLE_TAKEOUT_EMPTY_PRODUCTS = (
    "/noticias/",
    "/workspace studio/",
)

GOOGLE_TAKEOUT_BULK_DRIVE_MARKERS = (
    "/drive/.minecraft/",
    "/drive/floppasmp_backup/",
    "/drive/mods/",
    "/drive/world/",
)


def normalize_takeout_path(value: str | Path) -> str:
    normalized = unicodedata.normalize("NFKD", str(value).lower().replace("\xa0", " "))
    without_marks = "".join(character for character in normalized if not unicodedata.combining(character))
    return without_marks.replace("\\", "/")


def google_takeout_skip_reason(
    *,
    relative_import_path: str | Path,
    source_family: str | SourceFamily,
    file_size: int | None = None,
    relevance_mode: str = "skill_relevant",
    gmail_mode: str = "metadata_plus_sent",
    photos_mode: str = "fast_vision",
    drive_mode: str = "selective_docs",
) -> str | None:
    source_family_value = source_family.value if isinstance(source_family, SourceFamily) else str(source_family)
    if source_family_value != SourceFamily.GOOGLE_TAKEOUT.value:
        return None

    normalized_path = normalize_takeout_path(relative_import_path)
    filename = Path(normalized_path).name
    suffix = Path(normalized_path).suffix

    if relevance_mode == "off":
        return "google takeout ingestion disabled by config"
    if filename in LOW_SIGNAL_GOOGLE_TAKEOUT_FILENAMES:
        return "low-signal google takeout export index"
    if file_size == 0:
        return "empty google takeout export file"
    if any(filename.startswith(prefix) for prefix in LOW_SIGNAL_GOOGLE_TAKEOUT_PREFIXES):
        return "low-signal google takeout external wordlist"
    if ("/correo/" in normalized_path or "/mail/" in normalized_path) and gmail_mode == "off":
        return "google takeout gmail disabled by config"
    if any(marker in normalized_path for marker in LOW_SIGNAL_GOOGLE_TAKEOUT_PATH_MARKERS):
        return "low-signal google takeout account/payment/device metadata"
    if any(marker in normalized_path for marker in LOW_SIGNAL_GOOGLE_TAKEOUT_FILE_MARKERS):
        return "low-signal google takeout browser settings metadata"
    if any(marker in normalized_path for marker in LOW_SIGNAL_GOOGLE_TAKEOUT_EMPTY_PRODUCTS):
        return "empty or low-signal google takeout product export"

    if "/google fotos/" in normalized_path or "/google photos/" in normalized_path:
        if photos_mode == "off":
            return "google photos disabled by config"
        if _is_google_photos_sidecar(filename):
            return "google photos sidecar metadata is paired with sampled image material"
        if suffix not in GOOGLE_PHOTOS_IMAGE_SUFFIXES:
            return "google photos non-image bulk media is skipped by fast vision mode"

    if "/youtube y youtube music/videos/" in normalized_path or "/youtube and youtube music/videos/" in normalized_path:
        return "youtube raw video binaries are skipped; metadata and urls are ingested"

    if "/drive/" in normalized_path:
        if drive_mode == "off":
            return "google takeout drive disabled by config"
        if any(marker in normalized_path for marker in GOOGLE_TAKEOUT_BULK_DRIVE_MARKERS):
            return "google takeout drive bulk runtime/game data"
        if drive_mode == "selective_docs":
            if suffix in GOOGLE_TAKEOUT_DRIVE_SKIP_SUFFIXES:
                return "google takeout drive binary/archive/media file"
            if suffix and suffix not in GOOGLE_TAKEOUT_DRIVE_ACCEPT_SUFFIXES:
                return "google takeout drive unsupported selective-docs file"

    return None


def google_takeout_photo_sample_key(relative_import_path: Path) -> tuple[str, int] | None:
    normalized_path = normalize_takeout_path(relative_import_path)
    if "/google fotos/" not in normalized_path and "/google photos/" not in normalized_path:
        return None
    path = Path(normalized_path)
    if path.suffix not in GOOGLE_PHOTOS_IMAGE_SUFFIXES:
        return None
    return (str(path.parent), _stable_photo_index(path.name))


def is_google_takeout_photo_image(relative_import_path: Path) -> bool:
    return google_takeout_photo_sample_key(relative_import_path) is not None


def _stable_photo_index(filename: str) -> int:
    # Keep sampling deterministic across platforms without relying on Python's
    # randomized hash seed.
    return sum((index + 1) * ord(character) for index, character in enumerate(filename))


def _is_google_photos_sidecar(filename: str) -> bool:
    return bool(
        filename.endswith(".json")
        and re.search(r"\.(jpe?g|png|webp|gif|heic|heif|mp4|mov)\.", filename)
    )
