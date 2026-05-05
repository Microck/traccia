from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import unicodedata
import zipfile
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from traccia.config import load_config
from traccia.llm import (
    BackendError,
    CanonicalizationRequest,
    CanonicalSkillDecision,
    LLMBackend,
    ScorePayload,
    ScoringRequest,
    backend_from_config,
    load_prompt,
)
from traccia.models import (
    EvidenceItem,
    FreshnessState,
    IngestManifest,
    IngestManifestEntry,
    IngestMaterialStatus,
    IngestRunState,
    NodeStatus,
    ParsedDocument,
    ParsedSpan,
    PersonSkillState,
    PersonSkillStatus,
    ReviewItem,
    ReviewRiskLevel,
    SkillEdge,
    SkillKind,
    SkillNode,
    SourceFamily,
)
from traccia.parsers import ingestable_file, parse_document, sniff_text_bytes
from traccia.pipeline_support import build_skill_node, support_score
from traccia.rendering import render_project
from traccia.source_detection import (
    FamilyDetection,
    detect_source_family_from_archive,
    detect_source_family_from_path,
    refine_archive_member_detection,
)
from traccia.storage import Storage
from traccia.taxonomy import DOMAINS
from traccia.utils import (
    file_sha256,
    iso_now,
    short_hash,
    skill_id,
    slugify,
    source_id_for_relative_path,
)

DISCOVERY_PROGRESS_EVERY_MATERIALS = 25
DISCOVERY_PROGRESS_MIN_INTERVAL_SECONDS = 2.0
DISCOVERY_LOG_EVERY_MATERIALS = 250
OVERSIZED_SPAN_TARGET_CHARACTERS = 4_000
EMPTY_ROOT_BLOCK_THRESHOLD = 25

LOW_SIGNAL_INSTAGRAM_PATH_MARKERS = (
    "/ads_information/",
    "/apps_and_websites_off_of_instagram/",
    "/connections/followers_and_following/",
    "/logged_information/",
    "/monetization/",
    "/other_activity/surveys.html",
    "/personal_information/",
    "/security_and_login_information/login_and_profile_creation/",
    "/subscriptions/show_exclusive_story_promo_setting.html",
    "/subscriptions/your_muted_story_teaser_creators.html",
)

LOW_SIGNAL_INSTAGRAM_FILENAMES = {
    "start_here.html",
}

LOW_SIGNAL_TWITTER_SUBPRODUCTS = {
    "account",
    "followers",
    "following",
}

LOW_SIGNAL_TWITTER_PATH_MARKERS = ("/assets/",)

LOW_SIGNAL_TWITTER_FILENAMES = {
    "account-creation-ip.js",
    "account-label.js",
    "account-suspension.js",
    "account-timezone.js",
    "ad-engagements.js",
    "ad-impressions.js",
    "ad-mobile-conversions-attributed.js",
    "ad-mobile-conversions-unattributed.js",
    "ad-online-conversions-attributed.js",
    "ad-online-conversions-unattributed.js",
    "ads-revenue-sharing.js",
    "ageinfo.js",
    "app.js",
    "article-metadata.js",
    "audio-video-calls-in-dm-recipient-sessions.js",
    "audio-video-calls-in-dm.js",
    "branch-links.js",
    "catalog-item.js",
    "commerce-catalog.js",
    "connected-application.js",
    "contact.js",
    "deleted-tweet-headers.js",
    "device-token.js",
    "direct-message-group-headers.js",
    "direct-message-headers.js",
    "direct-message-mute.js",
    "email-address-change.js",
    "ip-audit.js",
    "key-registry.js",
    "manifest.js",
    "message-event.js",
    "ni-devices.js",
    "periscope-account-information.js",
    "periscope-ban-information.js",
    "phone-number.js",
    "protected-history.js",
    "readme.txt",
    "reply-prompt.js",
    "screen-name-change.js",
    "shop-module.js",
    "sso.js",
    "tweet-headers.js",
    "verified-organization.js",
    "verified.js",
    "your archive.html",
}

LOW_SIGNAL_REDDIT_FILENAMES = {
    "account_gender.csv",
    "announcements.csv",
    "birthdate.csv",
    "checkfile.csv",
    "comment_headers.csv",
    "ip_logs.csv",
    "linked_phone_number.csv",
    "messages_archive_headers.csv",
    "payouts.csv",
    "post_headers.csv",
    "purchases.csv",
    "sensitive_ads_preferences.csv",
    "statistics.csv",
    "stripe.csv",
    "twitter.csv",
    "user_preferences.csv",
}

LOW_SIGNAL_DISCORD_SUBPRODUCTS = {
    "account",
    "servers",
}

LOW_SIGNAL_DISCORD_FILENAMES = {
    "channel.json",
    "index.json",
}

LOW_SIGNAL_DISCORD_PATH_MARKERS = (
    "/account/",
    "/activity/",
    "/servers/",
)

NO_DATA_FILENAMES = {
    "no-data.txt",
    "no_data.txt",
}

LOW_SIGNAL_GOOGLE_TAKEOUT_PATH_MARKERS = (
    "/actividad de registro de accesos/",
    "/alertas/",
    "/cuenta de google/",
    "/encuestas sobre productos de google/",
    "/google play peliculas/",
    "/google play store/",
    "/google shopping/",
    "/google wallet/",
    "/google workspace marketplace/",
    "/google pay/",
    "/google store/",
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
}

LOW_SIGNAL_GOOGLE_TAKEOUT_PREFIXES = ("weakpass_",)

GOOGLE_TAKEOUT_DRIVE_ARCHIVE_SUFFIXES = {
    ".7z",
    ".rar",
    ".zip",
}

LOW_SIGNAL_DIRECTORY_NAMES = {
    ".cache",
    ".archive-unpack",
    ".config",
    ".fabric",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".ssh",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "libraries",
    "mods",
    "node_modules",
    "world",
}

LOW_SIGNAL_DIRECTORY_PREFIXES = ("python-",)

LOW_SIGNAL_FILE_SUFFIXES = {
    ".bak",
    ".old",
    ".orig",
    ".tiny",
    ".tmp",
}


@dataclass(slots=True)
class BatchResult:
    discovered: int = 0
    processed: int = 0
    skipped: int = 0
    imported: int = 0
    deleted: int = 0
    failed: int = 0


@dataclass(slots=True)
class DiscoverySummary:
    total_materials: int = 0
    direct_files: int = 0
    archive_members: int = 0
    by_root: dict[str, int] = field(default_factory=dict)
    by_family: dict[str, int] = field(default_factory=dict)
    by_family_subproduct: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class ImportMaterial:
    source_path: Path
    relative_import_path: Path
    source_family: SourceFamily
    source_family_subproduct: str | None
    detection_reason: str
    archive_member: str | None = None


ARCHIVE_SUFFIXES = {".zip"}
# Keep chunks below both a token-ish character budget and a span budget. The span
# cap prevents huge prompt lists, but it must stay high enough that dense JSON
# exports do not turn a few kilobytes of settings into dozens of LLM calls.
MAX_EXTRACTION_SPANS = 64
MAX_EXTRACTION_CHARACTERS = 12_000
MAX_CONSECUTIVE_BACKEND_FAILURES = 3
GRAPH_PROGRESSIVE_RENDER_MIN_INTERVAL_SECONDS = 15.0


class Pipeline:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.storage = Storage(self.project_root)
        self.config = load_config(self.project_root / "config" / "config.yaml")
        self._backend: LLMBackend | None = None

    @property
    def backend(self) -> LLMBackend:
        if self._backend is None:
            self._backend = backend_from_config(self.config)
        return self._backend

    @backend.setter
    def backend(self, value: LLMBackend) -> None:
        self._backend = value

    def add_file(self, path: Path) -> Path:
        materials = self._materials_for_path(path=path, root=path.parent)
        if not materials:
            raise ValueError(f"No ingestable material found in {path}")
        imported_paths = [self._import_material(material) for material in materials]
        if len(imported_paths) == 1:
            return imported_paths[0]
        return imported_paths[0].parent

    def add_directory(self, root: Path) -> int:
        materials = self._discover_materials(root)
        for material in materials:
            self._import_material(material)
        return len(materials)

    def discover_directory(self, root: Path) -> DiscoverySummary:
        materials = self._discover_materials(root)
        return self._summarize_materials(materials)

    def ingest_file(
        self, path: Path, *, root: Path | None = None, force: bool = False
    ) -> tuple[str, bool]:
        materials = self._materials_for_path(path=path, root=root or path.parent)
        if not materials:
            raise ValueError(f"No ingestable material found in {path}")

        processed_any = False
        first_source_id: str | None = None
        manifest_entries: list[IngestManifestEntry] = []
        for material in materials:
            source_id, processed = self._ingest_material(material, force=force)
            if first_source_id is None:
                first_source_id = source_id
            processed_any = processed_any or processed
            manifest_entries.append(
                IngestManifestEntry(
                    relative_import_path=material.relative_import_path.as_posix(),
                    source_path=_absolute_path_text(material.source_path),
                    archive_member=material.archive_member,
                    source_family=material.source_family,
                    source_family_subproduct=material.source_family_subproduct,
                    detection_reason=material.detection_reason,
                    status=IngestMaterialStatus.PROCESSED
                    if processed
                    else IngestMaterialStatus.SKIPPED,
                    source_id=source_id,
                    source_sha256=self.storage.fetch_source(source_id)["sha256"],
                )
            )
        self._write_ingest_manifest(root=root or path.parent, entries=manifest_entries)
        fallback_source_id = source_id_for_relative_path(
            self._relative_import_path_for(path=path, root=root or path.parent)
        )
        return first_source_id or fallback_source_id, processed_any

    def ingest_directory(self, root: Path, *, force: bool = False) -> BatchResult:
        result = BatchResult()
        manifest_entries: dict[str, IngestManifestEntry] = {}
        previous_run_state = self._load_ingest_run_state(root)
        self._append_log(f"- {iso_now()}: ingest-discovering root={root.resolve()}")
        self._write_progress(
            status="discovering",
            root=root,
            result=result,
            discovery=DiscoverySummary(),
            total_materials=None,
            resume_completed=_resume_completed_count(previous_run_state.materials)
            if previous_run_state
            else 0,
        )

        last_discovery_log_count = 0

        def on_discovery_progress(
            summary: DiscoverySummary, material: ImportMaterial | None
        ) -> None:
            nonlocal last_discovery_log_count
            if (
                material
                and summary.total_materials
                and summary.total_materials - last_discovery_log_count
                >= DISCOVERY_LOG_EVERY_MATERIALS
            ):
                self._append_log(
                    " ".join(
                        [
                            f"- {iso_now()}: ingest-discovering-progress",
                            f"discovered={summary.total_materials}",
                            f"direct_files={summary.direct_files}",
                            f"archive_members={summary.archive_members}",
                            f"latest={material.relative_import_path.as_posix()}",
                        ]
                    )
                )
                last_discovery_log_count = summary.total_materials
            self._write_progress(
                status="discovering",
                root=root,
                result=result,
                discovery=summary,
                total_materials=None,
                current_material=material,
                resume_completed=_resume_completed_count(previous_run_state.materials)
                if previous_run_state
                else 0,
            )

        cached_materials = self._resume_cached_materials(previous_run_state)
        if cached_materials is not None:
            current_materials = cached_materials
            self._append_log(
                f"- {iso_now()}: ingest-discovery-cache-reused "
                f"root={root.resolve()} materials={len(current_materials)}"
            )
            on_discovery_progress(
                self._summarize_materials(current_materials), current_materials[-1]
            )
        else:
            current_materials = self._discover_materials(root, on_progress=on_discovery_progress)
        discovery = self._summarize_materials(current_materials)
        if self._should_block_empty_root(
            root=root, current_materials=current_materials, previous_run_state=previous_run_state
        ):
            reason = (
                "Source root appears empty after a previously substantial ingest. "
                "This usually means the source mount or upstream directory is unavailable."
            )
            self._append_log(
                f"- {iso_now()}: ingest-blocked-empty-root root={root.resolve()} reason={reason}"
            )
            self._write_progress(
                status="blocked",
                root=root,
                result=result,
                discovery=discovery,
                total_materials=0,
                blocked_reason=reason,
                resume_completed=_resume_completed_count(previous_run_state.materials)
                if previous_run_state
                else 0,
            )
            raise RuntimeError(reason)
        manifest_entries = self._seed_manifest_entries(
            current_materials=current_materials,
            previous_run_state=previous_run_state,
        )
        result.discovered = discovery.total_materials
        total_materials = len(current_materials)
        consecutive_backend_failures = 0
        processed_since_graph_refresh = 0
        live_graph_checkpoint_count = 0
        last_graph_refresh_at = time.monotonic()
        resume_completed = _resume_completed_count(manifest_entries.values())
        resume_revalidated = 0

        self._append_log(
            f"- {iso_now()}: ingest-discovered root={root.resolve()} "
            f"materials={discovery.total_materials} direct_files={discovery.direct_files} "
            f"archive_members={discovery.archive_members} "
            f"by_root={_format_counts(discovery.by_root)} "
            f"by_family={_format_counts(discovery.by_family)} "
            f"by_family_subproduct={_format_counts(discovery.by_family_subproduct)}"
        )
        self._write_progress(
            status="running",
            root=root,
            result=result,
            discovery=discovery,
            total_materials=total_materials,
            resume_completed=resume_completed,
            resume_revalidated=resume_revalidated,
        )

        for index, material in enumerate(current_materials, start=1):
            entry = manifest_entries[material.relative_import_path.as_posix()]
            self._append_log(
                " ".join(
                    [
                        f"- {iso_now()}: material-start",
                        f"index={index}/{total_materials}",
                        f"relative_import_path={material.relative_import_path.as_posix()}",
                        f"family={material.source_family.value}",
                        f"subproduct={material.source_family_subproduct or '-'}",
                        f"archive_member={material.archive_member or '-'}",
                    ]
                )
            )
            self._write_progress(
                status="running",
                root=root,
                result=result,
                discovery=discovery,
                total_materials=total_materials,
                current_index=index,
                current_material=material,
                resume_completed=resume_completed,
            )
            if self._can_resume_material(material=material, entry=entry, force=force):
                result.imported += 1
                result.skipped += 1
                resume_revalidated += 1
                entry.status = IngestMaterialStatus.SKIPPED
                entry.error = None
                self._append_log(
                    " ".join(
                        [
                            f"- {iso_now()}: material-resumed",
                            f"index={index}/{total_materials}",
                            f"source_id={entry.source_id or '-'}",
                            f"status={entry.status.value}",
                            f"relative_import_path={material.relative_import_path.as_posix()}",
                        ]
                    )
                )
                self._write_ingest_run_state(
                    root=root,
                    total_materials=total_materials,
                    entries=list(manifest_entries.values()),
                )
                self._write_progress(
                    status="running",
                    root=root,
                    result=result,
                    discovery=discovery,
                    total_materials=total_materials,
                    current_index=index,
                    current_material=material,
                    resume_completed=resume_completed,
                    resume_revalidated=resume_revalidated,
                )
                continue
            try:
                source_id, processed = self._ingest_material(
                    material,
                    force=force,
                    on_chunk_progress=lambda chunk_index, chunk_total: self._write_progress(
                        status="running",
                        root=root,
                        result=result,
                        discovery=discovery,
                        total_materials=total_materials,
                        current_index=index,
                        current_material=material,
                        current_chunk_index=chunk_index,
                        current_chunk_total=chunk_total,
                        resume_completed=resume_completed,
                        resume_revalidated=resume_revalidated,
                    ),
                )
            except Exception as exc:
                result.failed += 1
                entry.status = IngestMaterialStatus.FAILED
                entry.error = f"{type(exc).__name__}: {exc}"
                backend_failure = _backend_failure_reason(exc)
                source_unavailable = _source_unavailable_reason(exc)
                blocking_failure = backend_failure or source_unavailable
                consecutive_backend_failures = (
                    consecutive_backend_failures + 1 if blocking_failure else 0
                )
                self._append_log(
                    " ".join(
                        [
                            f"- {iso_now()}: material-failed",
                            f"index={index}/{total_materials}",
                            f"path={_absolute_path_text(material.source_path)}",
                            f"relative_import_path={material.relative_import_path.as_posix()}",
                            f"error={type(exc).__name__}:{exc}",
                        ]
                    )
                )
                if _should_stop_directory_ingest(
                    backend_failure_reason=blocking_failure,
                    consecutive_backend_failures=consecutive_backend_failures,
                ):
                    reason = blocking_failure or str(exc)
                    self._write_ingest_run_state(
                        root=root,
                        total_materials=total_materials,
                        entries=list(manifest_entries.values()),
                    )
                    self._append_log(
                        " ".join(
                            [
                                f"- {iso_now()}: ingest-blocked",
                                f"index={index}/{total_materials}",
                                f"relative_import_path={material.relative_import_path.as_posix()}",
                                f"reason={reason}",
                                f"consecutive_backend_failures={consecutive_backend_failures}",
                            ]
                        )
                    )
                    self._write_progress(
                        status="blocked",
                        root=root,
                        result=result,
                        discovery=discovery,
                        total_materials=total_materials,
                        current_index=index,
                        current_material=material,
                        blocked_reason=reason,
                        resume_completed=resume_completed,
                        resume_revalidated=resume_revalidated,
                    )
                    if backend_failure:
                        raise RuntimeError(
                            "Ingest stopped because the LLM backend is unavailable. "
                            f"Last backend failure: {reason}"
                        ) from exc
                    raise RuntimeError(
                        "Ingest stopped because the source input is unavailable. "
                        f"Last source failure: {reason}"
                    ) from exc
                self._write_progress(
                    status="running",
                    root=root,
                    result=result,
                    discovery=discovery,
                    total_materials=total_materials,
                    current_index=index,
                    current_material=material,
                    resume_completed=resume_completed,
                    resume_revalidated=resume_revalidated,
                )
                self._write_ingest_run_state(
                    root=root,
                    total_materials=total_materials,
                    entries=list(manifest_entries.values()),
                )
                continue

            consecutive_backend_failures = 0
            result.imported += 1
            entry.source_id = source_id
            entry.error = None
            source_row = self.storage.fetch_source(source_id)
            entry.source_sha256 = str(source_row["sha256"]) if source_row else None
            if processed:
                result.processed += 1
                entry.status = IngestMaterialStatus.PROCESSED
                processed_since_graph_refresh += 1
            else:
                result.skipped += 1
                entry.status = IngestMaterialStatus.SKIPPED
            self._append_log(
                " ".join(
                    [
                        f"- {iso_now()}: material-finished",
                        f"index={index}/{total_materials}",
                        f"source_id={source_id}",
                        f"status={entry.status.value}",
                        f"relative_import_path={material.relative_import_path.as_posix()}",
                    ]
                )
            )
            self._write_ingest_run_state(
                root=root,
                total_materials=total_materials,
                entries=list(manifest_entries.values()),
            )
            self._write_progress(
                status="running",
                root=root,
                result=result,
                discovery=discovery,
                total_materials=total_materials,
                current_index=index,
                current_material=material,
                resume_completed=resume_completed,
                resume_revalidated=resume_revalidated,
            )
            if processed and self._should_refresh_live_graph(
                processed_since_graph_refresh=processed_since_graph_refresh,
                last_graph_refresh_at=last_graph_refresh_at,
                total_materials=total_materials,
                checkpoint_count=live_graph_checkpoint_count,
            ):

                def on_checkpoint_graph_progress(graph_progress: dict[str, object]) -> None:
                    self._write_progress(
                        status="running",
                        root=root,
                        result=result,
                        discovery=discovery,
                        total_materials=total_materials,
                        current_index=index,
                        current_material=material,
                        phase="graph_checkpoint",
                        graph_progress=graph_progress,
                        resume_completed=resume_completed,
                        resume_revalidated=resume_revalidated,
                    )

                self._write_progress(
                    status="running",
                    root=root,
                    result=result,
                    discovery=discovery,
                    total_materials=total_materials,
                    current_index=index,
                    current_material=material,
                    phase="graph_checkpoint",
                    resume_completed=resume_completed,
                    resume_revalidated=resume_revalidated,
                )
                self._refresh_live_graph_checkpoint(
                    root=root,
                    manifest_entries=list(manifest_entries.values()),
                    completed=result.processed + result.skipped + result.failed,
                    total_materials=total_materials,
                    graph_progress_callback=on_checkpoint_graph_progress,
                )
                processed_since_graph_refresh = 0
                live_graph_checkpoint_count += 1
                last_graph_refresh_at = time.monotonic()
        result.deleted = self._sync_import_scope(root=root, current_materials=current_materials)
        self._write_progress(
            status="running",
            root=root,
            result=result,
            discovery=discovery,
            total_materials=total_materials,
            current_index=total_materials,
            current_material=current_materials[-1] if current_materials else None,
            phase="graph_sync",
            resume_completed=resume_completed,
            resume_revalidated=resume_revalidated,
        )
        try:

            def on_final_graph_progress(graph_progress: dict[str, object]) -> None:
                self._write_progress(
                    status="running",
                    root=root,
                    result=result,
                    discovery=discovery,
                    total_materials=total_materials,
                    current_index=total_materials,
                    current_material=current_materials[-1] if current_materials else None,
                    phase="graph_sync",
                    graph_progress=graph_progress,
                    resume_completed=resume_completed,
                    resume_revalidated=resume_revalidated,
                )

            self._sync_graph_outputs(
                root=root,
                manifest_entries=list(manifest_entries.values()),
                graph_progress_callback=on_final_graph_progress,
            )
        except Exception as exc:
            backend_failure = _backend_failure_reason(exc)
            if backend_failure:
                current_material = current_materials[-1] if current_materials else None
                self._write_ingest_run_state(
                    root=root,
                    total_materials=total_materials,
                    entries=list(manifest_entries.values()),
                )
                self._append_log(
                    " ".join(
                        [
                            f"- {iso_now()}: ingest-blocked",
                            f"index={total_materials}/{total_materials}",
                            "phase=graph-sync",
                            f"reason={backend_failure}",
                        ]
                    )
                )
                self._write_progress(
                    status="blocked",
                    root=root,
                    result=result,
                    discovery=discovery,
                    total_materials=total_materials,
                    current_index=total_materials,
                    current_material=current_material,
                    blocked_reason=backend_failure,
                    resume_completed=resume_completed,
                    resume_revalidated=resume_revalidated,
                )
                raise RuntimeError(
                    "Ingest stopped because the LLM backend is unavailable during graph sync. "
                    f"Last backend failure: {backend_failure}"
                ) from exc
            raise
        self._write_ingest_run_state(
            root=root,
            total_materials=total_materials,
            entries=list(manifest_entries.values()),
        )
        self._append_log(
            f"- {iso_now()}: ingest-dir root={root.resolve()} imported={result.imported} "
            f"processed={result.processed} skipped={result.skipped} failed={result.failed} "
            f"deleted={result.deleted}"
        )
        self._write_progress(
            status="completed",
            root=root,
            result=result,
            discovery=discovery,
            total_materials=total_materials,
            resume_completed=resume_completed,
            resume_revalidated=resume_revalidated,
        )
        return result

    def reingest(self, source_id: str, *, force: bool = True) -> bool:
        source_row = self.storage.fetch_source(source_id)
        if not source_row:
            raise ValueError(f"Unknown source_id: {source_id}")
        source_path = Path(source_row["uri"].replace("file://", ""))
        _, processed = self.ingest_file(source_path, root=source_path.parent, force=force)
        self.recompute_graph()
        render_project(self.project_root, storage=self.storage)
        return processed

    def rebuild(self) -> BatchResult:
        result = BatchResult()
        imported_root = self.project_root / "raw" / "imported"
        for path in self._discover_files(imported_root):
            relative_import_path = path.relative_to(imported_root)
            self._rebuild_imported_path(path=path, relative_import_path=relative_import_path)
            result.processed += 1
        self.recompute_graph()
        render_project(self.project_root, storage=self.storage)
        self._append_log(f"- {iso_now()}: rebuild processed={result.processed}")
        return result

    def watch(self, root: Path, *, interval_seconds: int = 2) -> None:
        last_seen: dict[str, str] = {}
        while True:
            changed = False
            for path in self._watch_roots(root):
                current_stamp = f"{path.stat().st_mtime_ns}:{path.stat().st_size}"
                if last_seen.get(str(path)) != current_stamp:
                    last_seen[str(path)] = current_stamp
                    changed = True
            if changed:
                self.ingest_directory(root)
            time.sleep(interval_seconds)

    def recompute_graph(
        self,
        *,
        checkpoint_callback: Callable[[], None] | None = None,
        progress_callback: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        evidence_items = self.storage.list_evidence()
        overrides = self.storage.list_manual_overrides()
        self.storage.clear_pending_review_items()
        review_status_by_id = {
            row["item_id"]: row["status"]
            for row in self.storage.list_review_items(include_closed=True)
            if row["status"] != "pending"
        }
        existing_skill_rows = self.storage.list_skill_rows()
        existing_skill_rows_by_id = {str(row["skill_id"]): row for row in existing_skill_rows}
        previous_skill_rows = {
            str(row["skill_id"]): row for row in existing_skill_rows if row["kind"] != "domain"
        }

        support: dict[str, dict[str, object]] = {}
        for evidence_item in evidence_items:
            for candidate in evidence_item.skill_candidates:
                bucket = support.setdefault(candidate, {"evidence": []})
                bucket["evidence"].append(evidence_item)
        sorted_support = sorted(support.items())

        manual_skills: set[str] = set()
        alias_overrides: dict[str, set[str]] = defaultdict(set)
        locked_skills: set[str] = set()
        hidden_skills: set[str] = set()
        for override in overrides:
            payload = json.loads(override["payload_json"])
            if override["action"] == "create_skill":
                manual_skills.add(payload["name"])
            elif override["action"] == "alias_add":
                alias_overrides[override["target_id"]].add(payload["alias"])
            elif override["action"] == "lock":
                locked_skills.add(override["target_id"])
            elif override["action"] == "hide":
                hidden_skills.add(override["target_id"])

        overrides_fingerprint = _overrides_fingerprint(overrides)

        skills_by_id: dict[str, SkillNode] = {}
        states_by_skill_id: dict[str, PersonSkillState] = {}
        edges_by_id: dict[str, SkillEdge] = {}
        evidence_by_skill_id: dict[str, list[EvidenceItem]] = {}
        created_skill_ids: set[str] = set()
        checkpoint_count = 0
        last_checkpoint_at = time.monotonic()

        for domain in DOMAINS:
            skill = SkillNode(
                skill_id=skill_id("domain", domain.name),
                kind=SkillKind.DOMAIN,
                name=domain.name,
                slug=slugify(domain.name),
                aliases=[],
                description=domain.description,
                taxonomy_refs=[],
                status=NodeStatus.ACTIVE,
                created_by="system",
                last_updated=iso_now(),
            )
            skills_by_id[skill.skill_id] = skill

        def flush_graph_checkpoint(*, force: bool = False) -> None:
            nonlocal checkpoint_count, last_checkpoint_at
            has_non_domain_state = any(
                skills_by_id[state.skill_id].kind != SkillKind.DOMAIN
                for state in states_by_skill_id.values()
                if state.skill_id in skills_by_id
            )
            if not force:
                if not states_by_skill_id:
                    return
                if checkpoint_count == 0 and has_non_domain_state:
                    pass
                elif (
                    time.monotonic() - last_checkpoint_at
                    < GRAPH_PROGRESSIVE_RENDER_MIN_INTERVAL_SECONDS
                ):
                    return
            self.storage.replace_graph(
                skills=sorted(
                    skills_by_id.values(),
                    key=lambda skill: (skill.kind.value, skill.name.lower(), skill.skill_id),
                ),
                states=sorted(states_by_skill_id.values(), key=lambda state: state.skill_id),
                edges=sorted(edges_by_id.values(), key=lambda edge: edge.edge_id),
            )
            self.storage.sync_review_queue_file()
            if checkpoint_callback is not None:
                checkpoint_callback()
            checkpoint_count += 1
            last_checkpoint_at = time.monotonic()

        def emit_graph_progress(
            *,
            event: str,
            candidate_index: int,
            candidate_name: str,
            evidence_count: int,
            skill: SkillNode | None = None,
            score_payload: ScorePayload | None = None,
        ) -> None:
            if progress_callback is None:
                return
            payload: dict[str, object] = {
                "event": event,
                "candidate_index": candidate_index,
                "candidate_total": len(sorted_support),
                "candidate_name": candidate_name,
                "candidate_slug": slugify(candidate_name) or "unknown",
                "evidence_count": evidence_count,
            }
            if skill is not None:
                payload["skill_id"] = skill.skill_id
                payload["skill_name"] = skill.name
            if score_payload is not None:
                payload["level"] = score_payload.level
                payload["confidence"] = score_payload.confidence
            progress_callback(payload)

        for candidate_index, (candidate_name, candidate_support) in enumerate(
            sorted_support, start=1
        ):
            candidate_evidence = list(candidate_support["evidence"])
            emit_graph_progress(
                event="candidate-start",
                candidate_index=candidate_index,
                candidate_name=candidate_name,
                evidence_count=len(candidate_evidence),
            )
            support_fingerprint = _candidate_support_fingerprint(
                candidate_name=candidate_name,
                evidence_items=candidate_evidence,
                overrides_fingerprint=overrides_fingerprint,
                canonicalizer_version=self.config.pipeline.canonicalizer_version,
                scorer_version=self.config.pipeline.scorer_version,
                model_name=self.config.backend.model,
            )
            cached = self.storage.fetch_graph_candidate_cache(
                candidate_name=candidate_name,
                support_fingerprint=support_fingerprint,
            )
            decision: CanonicalSkillDecision
            score_payload: ScorePayload | None = None
            if cached:
                decision = CanonicalSkillDecision.model_validate_json(
                    cached["canonical_decision_json"]
                )
                if cached.get("score_payload_json"):
                    score_payload = ScorePayload.model_validate_json(cached["score_payload_json"])
            else:
                decision = self.backend.canonicalize(
                    prompt=load_prompt(self.project_root, "canonicalize_skills.md"),
                    request=CanonicalizationRequest(
                        candidate_name=candidate_name,
                        evidence_items=candidate_evidence,
                        existing_skills=existing_skill_rows,
                        thresholds={
                            "strong_evidence_auto_create": self.config.thresholds.strong_evidence_auto_create,
                            "review_confidence_floor": self.config.thresholds.review_confidence_floor,
                            "consumption_max_level": self.config.thresholds.consumption_max_level,
                        },
                    ),
                )

            if candidate_name in manual_skills and decision.action in {"ignore", "review"}:
                decision.action = "create"
                decision.canonical_name = candidate_name

            if decision.action == "ignore":
                self.storage.upsert_graph_candidate_cache(
                    candidate_name=candidate_name,
                    support_fingerprint=support_fingerprint,
                    canonical_decision_json=decision.model_dump_json(),
                    score_payload_json=None,
                )
                emit_graph_progress(
                    event="candidate-ignored",
                    candidate_index=candidate_index,
                    candidate_name=candidate_name,
                    evidence_count=len(candidate_evidence),
                )
                continue

            if decision.action == "review":
                item_id = f"review_{slugify(candidate_name)}"
                if review_status_by_id.get(item_id) not in {"accepted", "rejected"}:
                    self.storage.upsert_review_item(
                        ReviewItem(
                            item_id=item_id,
                            reason=decision.reason,
                            proposed_change={"type": "create_skill", "name": candidate_name},
                            evidence_ids=[
                                item.evidence_id for item in candidate_support["evidence"]
                            ],
                            risk_level=ReviewRiskLevel(decision.review_risk_level),
                        )
                    )
                self.storage.upsert_graph_candidate_cache(
                    candidate_name=candidate_name,
                    support_fingerprint=support_fingerprint,
                    canonical_decision_json=decision.model_dump_json(),
                    score_payload_json=None,
                )
                emit_graph_progress(
                    event="candidate-review",
                    candidate_index=candidate_index,
                    candidate_name=candidate_name,
                    evidence_count=len(candidate_evidence),
                )
                continue

            canonical_name = decision.canonical_name or candidate_name
            skill = _resolve_skill_node(
                candidate_name=candidate_name,
                canonical_name=canonical_name,
                decision=decision,
                skills_by_id=skills_by_id,
                existing_skill_rows_by_id=existing_skill_rows_by_id,
            )
            skill.aliases = _merged_aliases(
                skill.aliases,
                alias_overrides.get(skill.skill_id, set()),
                decision.aliases,
            )
            if skill.skill_id in hidden_skills:
                skill.status = NodeStatus.HIDDEN
            skills_by_id[skill.skill_id] = skill
            created_skill_ids.add(skill.skill_id)

            merged_evidence = _merge_evidence_items(
                evidence_by_skill_id.get(skill.skill_id, []),
                candidate_evidence,
            )
            evidence_by_skill_id[skill.skill_id] = merged_evidence

            if score_payload is None or len(merged_evidence) != len(candidate_evidence):
                emit_graph_progress(
                    event="skill-score-start",
                    candidate_index=candidate_index,
                    candidate_name=candidate_name,
                    evidence_count=len(merged_evidence),
                    skill=skill,
                )
                self._append_log(
                    " ".join(
                        [
                            f"- {iso_now()}: skill-score-start",
                            f"skill_id={skill.skill_id}",
                            f"candidate_name={slugify(candidate_name) or 'unknown'}",
                            f"evidence={len(merged_evidence)}",
                        ]
                    )
                )
                try:
                    score_payload = self.backend.score_skill(
                        prompt=load_prompt(self.project_root, "score_skill_state.md"),
                        request=ScoringRequest(
                            skill=skill,
                            evidence_items=merged_evidence,
                            thresholds={
                                "consumption_max_level": self.config.thresholds.consumption_max_level
                            },
                            locked=skill.skill_id in locked_skills,
                            hidden=skill.skill_id in hidden_skills,
                        ),
                    )
                except Exception as exc:
                    self._append_log(
                        " ".join(
                            [
                                f"- {iso_now()}: skill-score-failed",
                                f"skill_id={skill.skill_id}",
                                f"candidate_name={slugify(candidate_name) or 'unknown'}",
                                f"error={type(exc).__name__}:{exc}",
                            ]
                        )
                    )
                    raise
                self._append_log(
                    " ".join(
                        [
                            f"- {iso_now()}: skill-score-finished",
                            f"skill_id={skill.skill_id}",
                            f"candidate_name={slugify(candidate_name) or 'unknown'}",
                            f"level={score_payload.level}",
                            f"confidence={score_payload.confidence}",
                        ]
                    )
                )
                emit_graph_progress(
                    event="skill-score-finished",
                    candidate_index=candidate_index,
                    candidate_name=candidate_name,
                    evidence_count=len(merged_evidence),
                    skill=skill,
                    score_payload=score_payload,
                )
            else:
                emit_graph_progress(
                    event="skill-score-cached",
                    candidate_index=candidate_index,
                    candidate_name=candidate_name,
                    evidence_count=len(merged_evidence),
                    skill=skill,
                    score_payload=score_payload,
                )
            self.storage.upsert_graph_candidate_cache(
                candidate_name=candidate_name,
                support_fingerprint=support_fingerprint,
                canonical_decision_json=decision.model_dump_json(),
                score_payload_json=score_payload.model_dump_json(),
            )
            states_by_skill_id[skill.skill_id] = _build_person_skill_state(
                skill_id=skill.skill_id,
                evidence_items=merged_evidence,
                score_payload=score_payload,
                previous_row=previous_skill_rows.get(skill.skill_id),
                locked=skill.skill_id in locked_skills,
            )

            edge = _taxonomy_edge_for_skill(skill)
            if edge is not None:
                edges_by_id[edge.edge_id] = edge

            flush_graph_checkpoint()

        for item_id, status in review_status_by_id.items():
            if status == "pending":
                continue
            item = self.storage.get_review_item(item_id)
            if not item:
                continue
            proposed = json.loads(item["proposed_change_json"])
            name = proposed.get("name")
            skill = build_skill_node(name) if name else None
            if item["status"] == "accepted" and skill and skill.skill_id not in created_skill_ids:
                skill = build_skill_node(name)
                skills_by_id[skill.skill_id] = skill
                created_skill_ids.add(skill.skill_id)
                states_by_skill_id[skill.skill_id] = PersonSkillState(
                    skill_id=skill.skill_id,
                    level=1,
                    xp=12.0,
                    confidence=0.35,
                    core_self_centrality=0.2,
                    recency_score=0.6,
                    breadth_score=0.2,
                    depth_score=0.2,
                    artifact_score=0.0,
                    teaching_score=0.0,
                    first_seen_at=datetime.now(tz=UTC),
                    first_learned_at=None,
                    first_strong_evidence_at=datetime.now(tz=UTC),
                    last_evidence_at=datetime.now(tz=UTC),
                    last_strong_evidence_at=datetime.now(tz=UTC),
                    historical_peak_level=1,
                    historical_peak_at=datetime.now(tz=UTC),
                    acquired_at=datetime.now(tz=UTC),
                    acquisition_basis="manual_review_accept",
                    freshness=FreshnessState.ACTIVE,
                    status=PersonSkillStatus.MANUAL,
                    locked=False,
                    manual_note="Accepted from review queue.",
                )
                edge = _taxonomy_edge_for_skill(skill)
                if edge is not None:
                    edges_by_id[edge.edge_id] = edge

        flush_graph_checkpoint(force=True)

    def _should_refresh_live_graph(
        self,
        *,
        processed_since_graph_refresh: int,
        last_graph_refresh_at: float,
        total_materials: int,
        checkpoint_count: int,
    ) -> bool:
        if processed_since_graph_refresh <= 0:
            return False

        refresh_config = self.config.graph_refresh
        if total_materials <= refresh_config.small_run_live_checkpoint_material_limit:
            material_interval = 1
        else:
            material_interval = refresh_config.live_checkpoint_material_interval
        if processed_since_graph_refresh < material_interval:
            return False
        if checkpoint_count == 0:
            return True
        return (
            time.monotonic() - last_graph_refresh_at
            >= refresh_config.live_checkpoint_min_interval_seconds
        )

    def _refresh_live_graph_checkpoint(
        self,
        *,
        root: Path,
        manifest_entries: list[IngestManifestEntry],
        completed: int,
        total_materials: int,
        graph_progress_callback: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        self._append_log(
            f"- {iso_now()}: graph-checkpoint-start completed={completed}/{total_materials}"
        )
        try:
            self._sync_graph_outputs(
                root=root,
                manifest_entries=manifest_entries,
                graph_progress_callback=graph_progress_callback,
            )
            self._append_log(
                f"- {iso_now()}: graph-checkpoint completed={completed}/{total_materials}"
            )
        except Exception as exc:
            self._append_log(
                f"- {iso_now()}: graph-checkpoint-failed "
                f"completed={completed}/{total_materials} error={type(exc).__name__}:{exc}"
            )

    def _sync_graph_outputs(
        self,
        *,
        root: Path,
        manifest_entries: list[IngestManifestEntry],
        graph_progress_callback: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        self._write_ingest_manifest(root=root, entries=manifest_entries)
        self.recompute_graph(
            checkpoint_callback=lambda: render_project(self.project_root, storage=self.storage),
            progress_callback=graph_progress_callback,
        )
        render_project(self.project_root, storage=self.storage)

    def _discover_files(self, root: Path) -> list[Path]:
        return [
            path for path in _iter_paths_sorted(root) if path.is_file() and ingestable_file(path)
        ]

    def _watch_roots(self, root: Path) -> list[Path]:
        return [
            path
            for path in _iter_paths_sorted(root)
            if path.is_file() and (ingestable_file(path) or self._is_archive(path))
        ]

    def _discover_materials(
        self,
        root: Path,
        *,
        on_progress: Callable[[DiscoverySummary, ImportMaterial | None], None] | None = None,
    ) -> list[ImportMaterial]:
        materials: list[ImportMaterial] = []
        summary = DiscoverySummary()
        last_progress_at = 0.0

        for material in self._iter_materials(root):
            materials.append(material)
            _update_discovery_summary(summary, material)
            if on_progress is None:
                continue
            now = time.monotonic()
            should_emit = (
                summary.total_materials == 1
                or summary.total_materials % DISCOVERY_PROGRESS_EVERY_MATERIALS == 0
                or now - last_progress_at >= DISCOVERY_PROGRESS_MIN_INTERVAL_SECONDS
            )
            if should_emit:
                on_progress(summary, material)
                last_progress_at = now

        if on_progress is not None:
            on_progress(summary, materials[-1] if materials else None)
        return materials

    def _iter_materials(self, root: Path) -> Iterator[ImportMaterial]:
        seen_relative_paths: set[Path] = set()
        for path in _iter_paths_sorted(root):
            if not path.is_file():
                continue
            relative_import_path = self._relative_import_path_for(path=path, root=root)
            if _skip_candidate_path_reason(relative_import_path):
                continue
            if not (ingestable_file(path) or self._is_archive(path)):
                continue
            for material in self._materials_for_path(path=path, root=root):
                if _skip_material_reason(material):
                    continue
                if material.relative_import_path in seen_relative_paths:
                    continue
                seen_relative_paths.add(material.relative_import_path)
                yield material

    def _materials_for_path(self, *, path: Path, root: Path) -> list[ImportMaterial]:
        relative_import_path = self._relative_import_path_for(path=path, root=root)
        if _skip_candidate_path_reason(relative_import_path):
            return []
        if self._is_archive(path):
            return self._archive_materials(path=path, root=root)
        if ingestable_file(path):
            detection = detect_source_family_from_path(relative_import_path)
            return [
                ImportMaterial(
                    source_path=path,
                    relative_import_path=relative_import_path,
                    source_family=detection.source_family,
                    source_family_subproduct=detection.subproduct,
                    detection_reason=detection.reason,
                )
            ]
        return []

    def _archive_materials(self, *, path: Path, root: Path) -> list[ImportMaterial]:
        materials: list[ImportMaterial] = []
        archive_root = self._archive_relative_root(path=path, root=root)
        detection = detect_source_family_from_archive(path)
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                member_path = Path(info.filename)
                if self._unsafe_archive_member(member_path):
                    continue
                if not self._ingestable_archive_member(archive=archive, info=info):
                    continue
                member_detection = refine_archive_member_detection(
                    archive_detection=detection,
                    member_path=member_path,
                )
                materials.append(
                    ImportMaterial(
                        source_path=path,
                        relative_import_path=archive_root / member_path,
                        source_family=member_detection.source_family,
                        source_family_subproduct=member_detection.subproduct,
                        detection_reason=member_detection.reason,
                        archive_member=info.filename,
                    )
                )
        return materials

    def _sync_import_scope(self, *, root: Path, current_materials: list[ImportMaterial]) -> int:
        current_source_ids = {
            source_id_for_relative_path(material.relative_import_path)
            for material in current_materials
        }
        deleted = 0
        scope_root = (
            self.project_root / "raw" / "imported" / slugify(root.name or "imported")
        ).absolute()
        for source_row in self.storage.list_sources():
            if source_row["status"] == "deleted":
                continue
            metadata = json.loads(str(source_row["metadata_json"] or "{}"))
            relative_import_path = metadata.get("relative_import_path")
            if not isinstance(relative_import_path, str) or not relative_import_path:
                continue
            imported_path = (
                self.project_root / "raw" / "imported" / relative_import_path
            ).absolute()
            if not _path_within_scope(imported_path, scope_root):
                continue
            if source_row["source_id"] in current_source_ids:
                continue
            self.storage.mark_source_deleted(str(source_row["source_id"]))
            self.storage.delete_source_derived_records(str(source_row["source_id"]))
            self._delete_source_artifacts(str(source_row["source_id"]), imported_path)
            deleted += 1
        return deleted

    def _should_block_empty_root(
        self,
        *,
        root: Path,
        current_materials: list[ImportMaterial],
        previous_run_state: IngestRunState | None,
    ) -> bool:
        if current_materials:
            return False
        if (
            previous_run_state is None
            or previous_run_state.total_materials < EMPTY_ROOT_BLOCK_THRESHOLD
        ):
            return False
        try:
            next(root.iterdir())
        except StopIteration:
            return True
        except OSError:
            return True
        return False

    def _ingest_material(
        self,
        material: ImportMaterial,
        *,
        force: bool,
        on_chunk_progress: Callable[[int, int], None] | None = None,
    ) -> tuple[str, bool]:
        imported_path = self._import_material(material)
        parsed_document = self._parsed_document_for_material(
            material=material, imported_path=imported_path
        )
        previous_source = self.storage.fetch_source(parsed_document.source.source_id)
        if (
            previous_source
            and previous_source["sha256"] == parsed_document.source.sha256
            and self._ingest_artifacts_complete(parsed_document.source.source_id)
            and not force
        ):
            return parsed_document.source.source_id, False

        self.storage.upsert_source(parsed_document.source)
        self.storage.replace_source_spans(parsed_document.source.source_id, parsed_document.spans)
        self._write_parsed_artifact(parsed_document)

        evidence_items = self._extract_evidence_items(
            parsed_document,
            force=force,
            on_chunk_progress=on_chunk_progress,
        )
        self.storage.replace_source_evidence(parsed_document.source.source_id, evidence_items)
        self._write_evidence_artifact(parsed_document.source.source_id, evidence_items)
        self.storage.clear_extraction_checkpoints(parsed_document.source.source_id)
        return parsed_document.source.source_id, True

    def _ingest_artifacts_complete(self, source_id: str) -> bool:
        parsed_artifact = self.project_root / "parsed" / f"{source_id}.json"
        evidence_artifact = self.project_root / "evidence" / f"{source_id}.json"
        return parsed_artifact.exists() and evidence_artifact.exists()

    def _rebuild_imported_path(self, *, path: Path, relative_import_path: Path) -> None:
        detection = detect_source_family_from_path(relative_import_path)
        parsed_document = self._annotate_parsed_document(
            parse_document(
                path,
                project_relative_path=relative_import_path,
                config=self.config,
                source_family=detection.source_family,
                source_family_subproduct=detection.subproduct,
            ),
            detection=detection,
            archive_member=None,
        )
        self.storage.upsert_source(parsed_document.source)
        self.storage.replace_source_spans(parsed_document.source.source_id, parsed_document.spans)
        self._write_parsed_artifact(parsed_document)
        evidence_items = self._extract_evidence_items(parsed_document, force=True)
        self.storage.replace_source_evidence(parsed_document.source.source_id, evidence_items)
        self._write_evidence_artifact(parsed_document.source.source_id, evidence_items)
        self.storage.clear_extraction_checkpoints(parsed_document.source.source_id)

    def _extract_evidence_items(
        self,
        parsed_document: ParsedDocument,
        *,
        force: bool = False,
        on_chunk_progress: Callable[[int, int], None] | None = None,
    ) -> list[EvidenceItem]:
        skip_reason = _skip_extraction_reason(parsed_document)
        if skip_reason:
            self.storage.clear_extraction_checkpoints(parsed_document.source.source_id)
            self._append_log(
                f"- {iso_now()}: extraction-skipped source_id={parsed_document.source.source_id} "
                f"reason={skip_reason}"
            )
            return []

        evidence_items: list[EvidenceItem] = []
        prompt = load_prompt(self.project_root, "extract_evidence.md")
        chunks = _chunk_document(parsed_document)
        completed_chunks = self._resume_checkpoints_for_document(
            parsed_document=parsed_document,
            chunks=chunks,
            force=force,
        )

        if completed_chunks:
            self._append_log(
                f"- {iso_now()}: extraction-resume source_id={parsed_document.source.source_id} "
                f"completed_chunks={len(completed_chunks)}/{len(chunks)}"
            )
            if on_chunk_progress:
                on_chunk_progress(len(completed_chunks), len(chunks))

        for chunk_index, chunk in enumerate(chunks):
            resumed_evidence = completed_chunks.get(chunk_index)
            if resumed_evidence is not None:
                evidence_items.extend(resumed_evidence)
                if on_chunk_progress:
                    on_chunk_progress(chunk_index + 1, len(chunks))
                continue

            chunk_evidence = self.backend.extract_evidence(
                prompt=prompt,
                document=chunk,
            )
            self.storage.upsert_extraction_checkpoint(
                source_id=parsed_document.source.source_id,
                source_sha256=parsed_document.source.sha256,
                extractor_version=self.config.pipeline.extractor_version,
                chunk_index=chunk_index,
                chunk_fingerprint=_chunk_fingerprint(chunk),
                evidence_items=chunk_evidence,
            )
            evidence_items.extend(chunk_evidence)
            if on_chunk_progress:
                on_chunk_progress(chunk_index + 1, len(chunks))
        return _normalize_evidence_items(parsed_document.source.source_id, evidence_items)

    def _resume_checkpoints_for_document(
        self,
        *,
        parsed_document: ParsedDocument,
        chunks: list[ParsedDocument],
        force: bool,
    ) -> dict[int, list[EvidenceItem]]:
        source_id = parsed_document.source.source_id
        if force:
            self.storage.clear_extraction_checkpoints(source_id)
            return {}

        rows = self.storage.list_extraction_checkpoints(source_id)
        if not rows:
            return {}

        expected_fingerprints = {
            chunk_index: _chunk_fingerprint(chunk) for chunk_index, chunk in enumerate(chunks)
        }
        resumed: dict[int, list[EvidenceItem]] = {}
        for row in rows:
            chunk_index = int(row["chunk_index"])
            if (
                row["source_sha256"] != parsed_document.source.sha256
                or row["extractor_version"] != self.config.pipeline.extractor_version
                or expected_fingerprints.get(chunk_index) != row["chunk_fingerprint"]
            ):
                self.storage.clear_extraction_checkpoints(source_id)
                return {}
            resumed[chunk_index] = [
                EvidenceItem.model_validate(item) for item in json.loads(str(row["evidence_json"]))
            ]
        return resumed

    def _import_material(self, material: ImportMaterial) -> Path:
        destination = self.project_root / "raw" / "imported" / material.relative_import_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if material.archive_member:
            with (
                zipfile.ZipFile(material.source_path) as archive,
                archive.open(material.archive_member) as source_handle,
                destination.open("wb") as destination_handle,
            ):
                shutil.copyfileobj(source_handle, destination_handle)
        else:
            target_path = _absolute_path_no_resolve(material.source_path)
            if not target_path.exists():
                raise FileNotFoundError(
                    f"Source material is unavailable: {target_path}. "
                    "If this path is on a mounted drive, remount it before resuming ingest."
                )
            if destination.is_symlink():
                if destination.readlink() == target_path:
                    return destination
                destination.unlink()
            elif destination.exists():
                destination.unlink()
            destination.symlink_to(target_path)
        return destination

    def _parsed_document_for_material(
        self, *, material: ImportMaterial, imported_path: Path
    ) -> ParsedDocument:
        parsed_document = parse_document(
            imported_path,
            project_relative_path=material.relative_import_path,
            config=self.config,
            source_family=material.source_family,
            source_family_subproduct=material.source_family_subproduct,
        )
        return self._annotate_parsed_document(
            parsed_document,
            detection=FamilyDetection(
                source_family=material.source_family,
                reason=material.detection_reason,
                subproduct=material.source_family_subproduct,
            ),
            archive_member=material.archive_member,
        )

    def _annotate_parsed_document(
        self,
        parsed_document: ParsedDocument,
        *,
        detection: FamilyDetection,
        archive_member: str | None,
    ) -> ParsedDocument:
        metadata = dict(parsed_document.source.metadata)
        metadata["source_family"] = detection.source_family.value
        metadata["source_family_reason"] = detection.reason
        if detection.subproduct:
            metadata["source_family_subproduct"] = detection.subproduct
        if archive_member:
            metadata["archive_member"] = archive_member
        return parsed_document.model_copy(
            update={"source": parsed_document.source.model_copy(update={"metadata": metadata})}
        )

    def _import_path_for(self, *, path: Path, root: Path) -> Path:
        return (
            self.project_root
            / "raw"
            / "imported"
            / self._relative_import_path_for(path=path, root=root)
        )

    def _relative_import_path_for(self, *, path: Path, root: Path) -> Path:
        root_name = slugify(root.name or "imported")
        return Path(root_name) / path.relative_to(root)

    def _archive_relative_root(self, *, path: Path, root: Path) -> Path:
        archive_relative = path.relative_to(root)
        return (
            Path(slugify(root.name or "imported")) / archive_relative.parent / archive_relative.stem
        )

    def _ingest_run_state_path(self, root: Path) -> Path:
        state_root = self.project_root / "state" / "ingest-runs"
        state_root.mkdir(parents=True, exist_ok=True)
        root_hash = short_hash(root.resolve().as_uri(), length=16)
        return state_root / f"{slugify(root.name or 'root')}-{root_hash}.json"

    def _load_ingest_run_state(self, root: Path) -> IngestRunState | None:
        state_path = self._ingest_run_state_path(root)
        if not state_path.exists():
            return None
        try:
            state = IngestRunState.model_validate_json(state_path.read_text())
        except Exception:
            return None
        if state.root_uri != root.resolve().as_uri():
            return None
        return state

    def _resume_cached_materials(
        self, previous_run_state: IngestRunState | None
    ) -> list[ImportMaterial] | None:
        if previous_run_state is None or not previous_run_state.materials:
            return None
        incomplete_statuses = {IngestMaterialStatus.DISCOVERED, IngestMaterialStatus.FAILED}
        if not any(entry.status in incomplete_statuses for entry in previous_run_state.materials):
            return None
        materials: list[ImportMaterial] = []
        for entry in previous_run_state.materials:
            material = ImportMaterial(
                source_path=Path(entry.source_path),
                relative_import_path=Path(entry.relative_import_path),
                source_family=entry.source_family,
                source_family_subproduct=entry.source_family_subproduct,
                detection_reason=entry.detection_reason,
                archive_member=entry.archive_member,
            )
            if _skip_candidate_path_reason(material.relative_import_path) or _skip_material_reason(
                material
            ):
                continue
            materials.append(material)
        if not materials:
            return None
        return materials

    def _write_ingest_run_state(
        self,
        *,
        root: Path,
        total_materials: int,
        entries: list[IngestManifestEntry],
    ) -> Path:
        state = IngestRunState(
            root_uri=root.resolve().as_uri(),
            updated_at=datetime.now(tz=UTC),
            total_materials=total_materials,
            materials=sorted(entries, key=lambda entry: entry.relative_import_path),
        )
        state_path = self._ingest_run_state_path(root)
        state_path.write_text(state.model_dump_json(indent=2) + "\n")
        return state_path

    def _seed_manifest_entries(
        self,
        *,
        current_materials: list[ImportMaterial],
        previous_run_state: IngestRunState | None,
    ) -> dict[str, IngestManifestEntry]:
        previous_entries = {
            entry.relative_import_path: entry
            for entry in (previous_run_state.materials if previous_run_state else [])
        }
        seeded: dict[str, IngestManifestEntry] = {}
        for material in current_materials:
            key = material.relative_import_path.as_posix()
            existing = previous_entries.get(key)
            if existing is not None:
                seeded[key] = existing.model_copy(
                    update={
                        "source_path": _absolute_path_text(material.source_path),
                        "archive_member": material.archive_member,
                        "source_family": material.source_family,
                        "source_family_subproduct": material.source_family_subproduct,
                        "detection_reason": material.detection_reason,
                    }
                )
                continue
            seeded[key] = IngestManifestEntry(
                relative_import_path=key,
                source_path=_absolute_path_text(material.source_path),
                archive_member=material.archive_member,
                source_family=material.source_family,
                source_family_subproduct=material.source_family_subproduct,
                detection_reason=material.detection_reason,
                status=IngestMaterialStatus.DISCOVERED,
            )
        return seeded

    def _can_resume_material(
        self,
        *,
        material: ImportMaterial,
        entry: IngestManifestEntry,
        force: bool,
    ) -> bool:
        if force:
            return False
        if entry.status not in {IngestMaterialStatus.PROCESSED, IngestMaterialStatus.SKIPPED}:
            return False
        if not entry.source_id or not entry.source_sha256:
            return False
        if not self._ingest_artifacts_complete(entry.source_id):
            return False
        current_sha256 = self._material_sha256(material)
        return current_sha256 == entry.source_sha256

    def _material_sha256(self, material: ImportMaterial) -> str | None:
        try:
            if material.archive_member:
                digest = hashlib.sha256()
                with (
                    zipfile.ZipFile(material.source_path) as archive,
                    archive.open(material.archive_member) as handle,
                ):
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                return digest.hexdigest()
            return file_sha256(material.source_path)
        except (FileNotFoundError, KeyError, OSError, zipfile.BadZipFile):
            return None

    def _is_archive(self, path: Path) -> bool:
        return path.suffix.lower() in ARCHIVE_SUFFIXES

    def _unsafe_archive_member(self, member_path: Path) -> bool:
        return member_path.is_absolute() or ".." in member_path.parts

    def _ingestable_archive_member(
        self, *, archive: zipfile.ZipFile, info: zipfile.ZipInfo
    ) -> bool:
        member_path = Path(info.filename)
        if ingestable_file(member_path):
            return True
        with archive.open(info) as handle:
            return sniff_text_bytes(handle.read(4096))

    def _delete_source_artifacts(self, source_id: str, imported_path: Path) -> None:
        parsed_artifact = self.project_root / "parsed" / f"{source_id}.json"
        evidence_artifact = self.project_root / "evidence" / f"{source_id}.json"
        for artifact_path in (parsed_artifact, evidence_artifact, imported_path):
            if artifact_path.exists():
                artifact_path.unlink()

    def _write_parsed_artifact(self, parsed_document) -> None:
        artifact_path = self.project_root / "parsed" / f"{parsed_document.source.source_id}.json"
        artifact_path.write_text(parsed_document.model_dump_json(indent=2) + "\n")

    def _write_evidence_artifact(self, source_id: str, evidence_items: list[EvidenceItem]) -> None:
        artifact_path = self.project_root / "evidence" / f"{source_id}.json"
        artifact_path.write_text(
            json.dumps([item.model_dump(mode="json") for item in evidence_items], indent=2) + "\n"
        )

    def _write_ingest_manifest(self, *, root: Path, entries: list[IngestManifestEntry]) -> Path:
        manifest_root = self.project_root / "state" / "manifests"
        manifest_root.mkdir(parents=True, exist_ok=True)
        manifest_id = f"ingest_{slugify(root.name or 'root')}_{short_hash(f'{root.resolve()}:{iso_now()}', length=10)}"
        manifest = IngestManifest(
            manifest_id=manifest_id,
            root_uri=root.resolve().as_uri(),
            generated_at=datetime.now(tz=UTC),
            materials=sorted(entries, key=lambda entry: entry.relative_import_path),
        )
        manifest_path = manifest_root / f"{manifest_id}.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n")
        return manifest_path

    def _append_log(self, line: str) -> None:
        log_path = self.project_root / "tree" / "log.md"
        with log_path.open("a", encoding="utf-8") as handle:
            if log_path.stat().st_size == 0:
                handle.write("# Ingest Log\n")
            handle.write(f"{line}\n")

    def _summarize_materials(self, materials: list[ImportMaterial]) -> DiscoverySummary:
        summary = DiscoverySummary()
        for material in materials:
            _update_discovery_summary(summary, material)
        return summary

    def _write_progress(
        self,
        *,
        status: str,
        root: Path,
        result: BatchResult,
        discovery: DiscoverySummary,
        total_materials: int | None,
        current_index: int | None = None,
        current_material: ImportMaterial | None = None,
        current_chunk_index: int | None = None,
        current_chunk_total: int | None = None,
        blocked_reason: str | None = None,
        phase: str | None = None,
        graph_progress: dict[str, object] | None = None,
        resume_completed: int = 0,
        resume_revalidated: int = 0,
    ) -> Path:
        progress_path = self.project_root / "state" / "progress.json"
        payload: dict[str, object] = {
            "status": status,
            "root_uri": root.resolve().as_uri(),
            "updated_at": iso_now(),
            "materials": {
                "discovered": discovery.total_materials,
                "direct_files": discovery.direct_files,
                "archive_members": discovery.archive_members,
                "by_root": discovery.by_root,
                "by_family": discovery.by_family,
                "by_family_subproduct": discovery.by_family_subproduct,
            },
            "counts": {
                "imported": result.imported,
                "processed": result.processed,
                "skipped": result.skipped,
                "failed": result.failed,
                "deleted": result.deleted,
            },
            "progress": {
                "completed": resume_completed
                + result.imported
                + result.failed
                - resume_revalidated,
                "total": total_materials,
                "current_index": current_index,
            },
        }
        if resume_completed:
            payload["resume"] = {
                "completed_before_run": resume_completed,
                "revalidated_in_current_run": resume_revalidated,
            }
        if current_chunk_total is not None:
            payload["progress"]["current_chunk_index"] = current_chunk_index
            payload["progress"]["current_chunk_total"] = current_chunk_total
        if phase:
            payload["phase"] = phase
        if graph_progress is not None:
            payload["graph"] = graph_progress
        if current_material:
            payload["current_material"] = {
                "relative_import_path": current_material.relative_import_path.as_posix(),
                "source_path": _absolute_path_text(current_material.source_path),
                "source_family": current_material.source_family.value,
                "source_family_subproduct": current_material.source_family_subproduct,
                "archive_member": current_material.archive_member,
                "detection_reason": current_material.detection_reason,
            }
        if blocked_reason:
            payload["blocked_reason"] = blocked_reason
        progress_path.write_text(json.dumps(payload, indent=2) + "\n")
        return progress_path


def _chunk_document(document: ParsedDocument) -> list[ParsedDocument]:
    if not document.spans:
        return [document]

    chunks: list[ParsedDocument] = []
    current_spans: list[ParsedSpan] = []
    current_characters = 0

    for span in _expand_oversized_spans(document.spans):
        span_length = len(span.text)
        would_overflow = current_spans and (
            len(current_spans) >= MAX_EXTRACTION_SPANS
            or current_characters + span_length > MAX_EXTRACTION_CHARACTERS
        )
        if would_overflow:
            chunks.append(
                ParsedDocument(
                    source=document.source,
                    text="",
                    spans=current_spans,
                    attachments=document.attachments,
                )
            )
            current_spans = []
            current_characters = 0

        current_spans.append(span)
        current_characters += span_length

    if current_spans:
        chunks.append(
            ParsedDocument(
                source=document.source,
                text="",
                spans=current_spans,
                attachments=document.attachments,
            )
        )

    return chunks


def _expand_oversized_spans(spans: list[ParsedSpan]) -> Iterator[ParsedSpan]:
    for span in spans:
        if len(span.text) <= MAX_EXTRACTION_CHARACTERS:
            yield span
            continue

        start_offset = 0
        fragment_index = 0
        while start_offset < len(span.text):
            remaining = span.text[start_offset:]
            if len(remaining) <= OVERSIZED_SPAN_TARGET_CHARACTERS:
                split_offset = len(span.text)
            else:
                split_offset = _best_span_split_offset(
                    span.text,
                    start_offset=start_offset,
                    target_length=OVERSIZED_SPAN_TARGET_CHARACTERS,
                )

            fragment_text = span.text[start_offset:split_offset].strip()
            if fragment_text:
                prefix = span.text[:start_offset]
                fragment_start = span.span_start + start_offset
                fragment_end = fragment_start + len(fragment_text)
                fragment_line_start = span.line_start + prefix.count("\n")
                fragment_line_end = fragment_line_start + fragment_text.count("\n")
                yield span.model_copy(
                    update={
                        "span_id": f"{span.span_id}::chunk{fragment_index}",
                        "text": fragment_text,
                        "span_start": fragment_start,
                        "span_end": fragment_end,
                        "line_start": fragment_line_start,
                        "line_end": fragment_line_end,
                    }
                )
                fragment_index += 1

            start_offset = split_offset


def _best_span_split_offset(text: str, *, start_offset: int, target_length: int) -> int:
    preferred_end = min(len(text), start_offset + target_length)
    if preferred_end >= len(text):
        return len(text)

    window_start = max(start_offset + 1, preferred_end - 300)
    window = text[window_start:preferred_end]
    for marker in ("\n\n", "\n", ". ", "; ", ", ", " "):
        split_index = window.rfind(marker)
        if split_index != -1:
            return window_start + split_index + len(marker)
    return preferred_end


def _backend_failure_reason(exc: Exception) -> str | None:
    message = str(exc).strip()
    if not message:
        return None

    normalized = message.lower()
    if isinstance(exc, BackendError):
        return message
    if "llm backend request failed" in normalized:
        return message
    if "provider_error" in normalized:
        return message
    if "quota exhausted" in normalized:
        return message
    if "exhausted your capacity" in normalized:
        return message
    if "quota will reset" in normalized:
        return message
    if "model_cooldown" in normalized:
        return message
    if "reset_seconds" in normalized:
        return message
    if "auth_unavailable" in normalized:
        return message
    if "no auth available" in normalized:
        return message
    return None


def _source_unavailable_reason(exc: Exception) -> str | None:
    if not isinstance(exc, FileNotFoundError):
        return None
    message = str(exc).strip()
    if "source material is unavailable" in message.lower():
        return message
    return None


def _should_stop_directory_ingest(
    *,
    backend_failure_reason: str | None,
    consecutive_backend_failures: int,
) -> bool:
    if backend_failure_reason is None:
        return False

    normalized = backend_failure_reason.lower()
    if (
        "quota exhausted" in normalized
        or "exhausted your capacity" in normalized
        or "quota will reset" in normalized
        or "rate limit" in normalized
        or "model_cooldown" in normalized
        or "reset_seconds" in normalized
        or "auth_unavailable" in normalized
        or "no auth available" in normalized
        or "structured response validation failed" in normalized
        or "invalid json" in normalized
        or "source material is unavailable" in normalized
    ):
        return True

    return consecutive_backend_failures >= MAX_CONSECUTIVE_BACKEND_FAILURES


def _chunk_fingerprint(document: ParsedDocument) -> str:
    payload = {
        "spans": [
            {
                "span_id": span.span_id,
                "span_start": span.span_start,
                "span_end": span.span_end,
                "text": span.text,
            }
            for span in document.spans
        ],
        "attachments": [
            {
                "attachment_id": attachment.attachment_id,
                "kind": attachment.kind.value,
                "reference": attachment.reference,
                "resolved_path": attachment.resolved_path,
                "extracted_text": attachment.extracted_text,
            }
            for attachment in document.attachments
        ],
    }
    return short_hash(json.dumps(payload, sort_keys=True), length=16)


def _normalize_evidence_items(
    source_id: str, evidence_items: list[EvidenceItem]
) -> list[EvidenceItem]:
    normalized_by_id: dict[str, EvidenceItem] = {}
    for item in evidence_items:
        normalized = item.model_copy(
            update={
                "source_id": source_id,
                "quote": " ".join(item.quote.split()),
                "skill_candidates": sorted(set(item.skill_candidates)),
                "artifact_candidates": sorted(set(item.artifact_candidates)),
            }
        )
        evidence_id = _stable_evidence_id(normalized)
        normalized = normalized.model_copy(update={"evidence_id": evidence_id})
        existing = normalized_by_id.get(evidence_id)
        if existing is None or normalized.confidence > existing.confidence:
            normalized_by_id[evidence_id] = normalized

    return sorted(
        normalized_by_id.values(),
        key=lambda item: (
            item.span_start,
            item.span_end,
            item.evidence_type.value,
            item.evidence_id,
        ),
    )


def _stable_evidence_id(item: EvidenceItem) -> str:
    payload = {
        "source_id": item.source_id,
        "span_start": item.span_start,
        "span_end": item.span_end,
        "quote": item.quote,
        "evidence_type": item.evidence_type.value,
        "signal_class": item.signal_class.value,
        "skill_candidates": item.skill_candidates,
        "artifact_candidates": item.artifact_candidates,
    }
    return f"ev_{short_hash(json.dumps(payload, sort_keys=True), length=16)}"


def _latest_evidence_at(evidence_items: list[EvidenceItem]) -> datetime | None:
    values = [item.time_reference for item in evidence_items if item.time_reference]
    if not values:
        return None
    latest = max(values)
    return _time_reference_to_datetime(latest)


def _earliest_evidence_at(evidence_items: list[EvidenceItem]) -> datetime | None:
    values = [item.time_reference for item in evidence_items if item.time_reference]
    if not values:
        return None
    earliest = min(values)
    return _time_reference_to_datetime(earliest)


def _earliest_learning_evidence_at(evidence_items: list[EvidenceItem]) -> datetime | None:
    learning_values = [
        item.time_reference
        for item in evidence_items
        if item.time_reference
        and item.evidence_type.value in {"studied", "researched", "passed_assessment"}
    ]
    if not learning_values:
        return None
    earliest = min(learning_values)
    return _time_reference_to_datetime(earliest)


def _latest_strong_evidence_at(evidence_items: list[EvidenceItem]) -> datetime | None:
    strong_values = [
        item.time_reference
        for item in evidence_items
        if item.time_reference
        and item.evidence_type.value not in {"mentioned", "self_claimed", "studied", "researched"}
    ]
    if not strong_values:
        return None
    latest = max(strong_values)
    return _time_reference_to_datetime(latest)


def _earliest_strong_evidence_at(evidence_items: list[EvidenceItem]) -> datetime | None:
    strong_values = [
        item.time_reference
        for item in evidence_items
        if item.time_reference
        and item.evidence_type.value not in {"mentioned", "self_claimed", "studied", "researched"}
    ]
    if not strong_values:
        return None
    earliest = min(strong_values)
    return _time_reference_to_datetime(earliest)


def _freshness_from_evidence(
    evidence_items: list[EvidenceItem],
) -> tuple[float, FreshnessState]:
    reference_time = _latest_strong_evidence_at(evidence_items) or _latest_evidence_at(
        evidence_items
    )
    if not reference_time:
        return 0.0, FreshnessState.HISTORICAL

    age_days = max(0, (datetime.now(tz=UTC) - reference_time).days)
    if age_days <= 90:
        return 1.0, FreshnessState.ACTIVE
    if age_days <= 180:
        return 0.7, FreshnessState.WARMING
    if age_days <= 365:
        return 0.4, FreshnessState.STALE
    return 0.15, FreshnessState.HISTORICAL


def _build_person_skill_state(
    *,
    skill_id: str,
    evidence_items: list[EvidenceItem],
    score_payload,
    previous_row: dict[str, object] | None,
    locked: bool,
) -> PersonSkillState:
    current_first_seen_at = _earliest_evidence_at(evidence_items)
    current_first_learned_at = _earliest_learning_evidence_at(evidence_items)
    current_first_strong_evidence_at = _earliest_strong_evidence_at(evidence_items)
    last_evidence_at = _latest_evidence_at(evidence_items)
    last_strong_evidence_at = _latest_strong_evidence_at(evidence_items)
    recency_score, freshness = _freshness_from_evidence(evidence_items)

    previous_first_seen_at = _row_datetime(previous_row, "first_seen_at")
    previous_first_learned_at = _row_datetime(previous_row, "first_learned_at")
    previous_first_strong_evidence_at = _row_datetime(previous_row, "first_strong_evidence_at")

    first_seen_at = _merge_earliest_datetime(current_first_seen_at, previous_first_seen_at)
    first_learned_at = _merge_earliest_datetime(current_first_learned_at, previous_first_learned_at)
    first_strong_evidence_at = (
        _merge_earliest_datetime(
            current_first_strong_evidence_at, previous_first_strong_evidence_at
        )
        if current_first_strong_evidence_at or previous_first_strong_evidence_at
        else None
    )
    acquired_at, acquisition_basis = _estimate_acquired_at(
        first_seen_at=first_seen_at,
        first_learned_at=first_learned_at,
        first_strong_evidence_at=first_strong_evidence_at,
        previous_acquired_at=_row_datetime(previous_row, "acquired_at"),
        previous_acquisition_basis=str(previous_row["acquisition_basis"])
        if previous_row and previous_row.get("acquisition_basis")
        else None,
    )

    current_level = max(0, min(5, int(score_payload.level)))
    previous_peak_level = max(
        int(previous_row["historical_peak_level"] or 0) if previous_row else 0,
        int(previous_row["level"] or 0) if previous_row else 0,
    )
    historical_peak_level = max(current_level, previous_peak_level)

    previous_peak_at = _row_datetime(previous_row, "historical_peak_at")
    if historical_peak_level > previous_peak_level:
        historical_peak_at = last_strong_evidence_at or last_evidence_at or datetime.now(tz=UTC)
    elif previous_peak_at:
        historical_peak_at = previous_peak_at
    else:
        historical_peak_at = _row_datetime(
            previous_row, "last_strong_evidence_at"
        ) or _row_datetime(previous_row, "last_evidence_at")

    return PersonSkillState(
        skill_id=skill_id,
        level=current_level,
        xp=round(sum(support_score(item) for item in evidence_items) * 100, 2),
        confidence=_clamp_unit_score(score_payload.confidence),
        core_self_centrality=_core_self_centrality(
            evidence_items=evidence_items,
            first_seen_at=first_seen_at,
            last_evidence_at=last_evidence_at,
        ),
        recency_score=recency_score,
        breadth_score=_clamp_unit_score(score_payload.breadth_score),
        depth_score=_clamp_unit_score(score_payload.depth_score),
        artifact_score=_clamp_unit_score(score_payload.artifact_score),
        teaching_score=_clamp_unit_score(score_payload.teaching_score),
        first_seen_at=first_seen_at,
        first_learned_at=first_learned_at,
        first_strong_evidence_at=first_strong_evidence_at,
        last_evidence_at=last_evidence_at,
        last_strong_evidence_at=last_strong_evidence_at,
        historical_peak_level=historical_peak_level,
        historical_peak_at=historical_peak_at,
        acquired_at=acquired_at,
        acquisition_basis=acquisition_basis,
        freshness=freshness,
        status=PersonSkillStatus(score_payload.status),
        locked=locked,
        manual_note=score_payload.manual_note,
    )


def _clamp_unit_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _row_datetime(row: dict[str, object] | None, key: str) -> datetime | None:
    if not row or not row.get(key):
        return None
    raw_value = str(row[key])
    if raw_value.endswith("Z"):
        raw_value = raw_value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(raw_value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _core_self_centrality(
    *,
    evidence_items: list[EvidenceItem],
    first_seen_at: datetime | None,
    last_evidence_at: datetime | None,
) -> float:
    if not evidence_items:
        return 0.0

    unique_sources = len({item.source_id for item in evidence_items})
    unique_evidence_types = len({item.evidence_type.value for item in evidence_items})
    artifact_backed_count = sum(
        1
        for item in evidence_items
        if item.evidence_type.value
        in {"implemented", "debugged", "designed", "presented", "taught", "reviewed"}
    )

    duration_score = 0.0
    if first_seen_at and last_evidence_at:
        duration_days = max(0, (last_evidence_at - first_seen_at).days)
        duration_score = min(1.0, duration_days / 365)

    recurrence_score = min(1.0, unique_sources / 4)
    variety_score = min(1.0, unique_evidence_types / 5)
    artifact_score = min(1.0, artifact_backed_count / 4)

    centrality = (
        (duration_score * 0.35)
        + (recurrence_score * 0.3)
        + (variety_score * 0.15)
        + (artifact_score * 0.2)
    )
    return round(min(1.0, centrality), 2)


def _path_within_scope(path: Path, scope_root: Path) -> bool:
    try:
        path.relative_to(scope_root)
        return True
    except ValueError:
        return False


def _absolute_path_no_resolve(path: Path) -> Path:
    # `Path.resolve()` stats each path component. On rclone/FUSE mounts that is
    # expensive enough to stall resume seeding, and the ingest only needs a
    # stable absolute path string, not symlink resolution.
    return path if path.is_absolute() else path.absolute()


def _absolute_path_text(path: Path) -> str:
    return _absolute_path_no_resolve(path).as_posix()


def _merge_earliest_datetime(left: datetime | None, right: datetime | None) -> datetime | None:
    if left and right:
        return min(left, right)
    return left or right


def _iter_paths_sorted(root: Path) -> Iterator[Path]:
    for current_root, dirnames, filenames in os.walk(root):
        current_root_path = Path(current_root)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not _low_signal_directory_name(dirname)
            and not _skip_discovery_directory(current_root_path / dirname)
        ]
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            yield current_root_path / filename


def _skip_discovery_directory(path: Path) -> bool:
    # Opencode exports can contain expanded session directories named
    # `*.jsonl/` next to the real compressed `*.jsonl.gz` files. Traversing
    # those directories explodes discovery on rclone/FUSE mounts and duplicates
    # the same session content, so they are pruned before os.walk enters them.
    normalized_path = path.as_posix().lower()
    return "/agent-logs/opencode/" in normalized_path and path.name.lower().endswith(".jsonl")


def _low_signal_directory_name(dirname: str) -> bool:
    lowered = dirname.lower()
    return lowered in LOW_SIGNAL_DIRECTORY_NAMES or any(
        lowered.startswith(prefix) for prefix in LOW_SIGNAL_DIRECTORY_PREFIXES
    )


def _material_root_name(relative_import_path: Path) -> str:
    parts = relative_import_path.parts
    if len(parts) >= 2:
        return parts[1]
    if parts:
        return parts[0]
    return "root"


def _update_discovery_summary(summary: DiscoverySummary, material: ImportMaterial) -> None:
    summary.total_materials += 1
    if material.archive_member:
        summary.archive_members += 1
    else:
        summary.direct_files += 1
    root_name = _material_root_name(material.relative_import_path)
    summary.by_root[root_name] = summary.by_root.get(root_name, 0) + 1
    family_name = material.source_family.value
    summary.by_family[family_name] = summary.by_family.get(family_name, 0) + 1
    if material.source_family_subproduct:
        subproduct_key = f"{family_name}:{material.source_family_subproduct}"
        summary.by_family_subproduct[subproduct_key] = (
            summary.by_family_subproduct.get(subproduct_key, 0) + 1
        )


def _skip_extraction_reason(parsed_document: ParsedDocument) -> str | None:
    metadata = parsed_document.source.metadata
    relative_import_path = str(metadata.get("relative_import_path") or "").lower()
    source_family = str(metadata.get("source_family") or "").lower()
    source_family_subproduct = str(metadata.get("source_family_subproduct") or "").lower()
    filename = str(metadata.get("filename") or Path(relative_import_path).name).lower()
    family_normalizer = str(metadata.get("family_normalizer") or "").lower()
    family_normalizer_record_count = metadata.get("family_normalizer_record_count")
    normalized_text = parsed_document.text.strip().lower()

    if not parsed_document.spans:
        return "empty parsed document"

    if filename in NO_DATA_FILENAMES or normalized_text in {"no data", "sin datos"}:
        return "placeholder no-data export"

    if source_family == SourceFamily.INSTAGRAM_EXPORT.value:
        if filename in LOW_SIGNAL_INSTAGRAM_FILENAMES:
            return "low-signal instagram export index"
        if any(marker in relative_import_path for marker in LOW_SIGNAL_INSTAGRAM_PATH_MARKERS):
            return "low-signal instagram account-metadata export"

    if source_family == SourceFamily.TWITTER_ARCHIVE.value:
        if any(marker in relative_import_path for marker in LOW_SIGNAL_TWITTER_PATH_MARKERS):
            return "twitter archive support asset"
        if filename in LOW_SIGNAL_TWITTER_FILENAMES:
            return "low-signal twitter archive metadata/export module"
        if source_family_subproduct in LOW_SIGNAL_TWITTER_SUBPRODUCTS:
            return "low-signal twitter account graph export"
        if (
            family_normalizer == "twitter-ytd-js"
            and isinstance(family_normalizer_record_count, int)
            and family_normalizer_record_count == 0
        ):
            return "empty twitter archive ytd module"

    if (
        source_family == SourceFamily.REDDIT_EXPORT.value
        and filename in LOW_SIGNAL_REDDIT_FILENAMES
    ):
        return "low-signal reddit account metadata/export index"

    if source_family == SourceFamily.DISCORD_DATA_PACKAGE.value:
        if source_family_subproduct != "messages":
            return "low-signal discord non-message export"
        if any(marker in relative_import_path for marker in LOW_SIGNAL_DISCORD_PATH_MARKERS):
            return "low-signal discord account/server metadata"
        if source_family_subproduct in LOW_SIGNAL_DISCORD_SUBPRODUCTS:
            return "low-signal discord account/server metadata"
        if filename in LOW_SIGNAL_DISCORD_FILENAMES:
            return "low-signal discord channel/package metadata"

    google_reason = _skip_google_takeout_path_reason(
        relative_import_path=relative_import_path,
        source_family=source_family,
    )
    if google_reason:
        return google_reason

    return None


def _skip_material_reason(material: ImportMaterial) -> str | None:
    relative_import_path = material.relative_import_path.as_posix().lower()
    filename = Path(relative_import_path).name

    if filename in NO_DATA_FILENAMES:
        return "placeholder no-data export"

    if material.source_family == SourceFamily.INSTAGRAM_EXPORT:
        if filename in LOW_SIGNAL_INSTAGRAM_FILENAMES:
            return "low-signal instagram export index"
        if any(marker in relative_import_path for marker in LOW_SIGNAL_INSTAGRAM_PATH_MARKERS):
            return "low-signal instagram account-metadata export"

    if material.source_family == SourceFamily.TWITTER_ARCHIVE:
        if any(marker in relative_import_path for marker in LOW_SIGNAL_TWITTER_PATH_MARKERS):
            return "twitter archive support asset"
        if filename in LOW_SIGNAL_TWITTER_FILENAMES:
            return "low-signal twitter archive metadata/export module"
        if (material.source_family_subproduct or "").lower() in LOW_SIGNAL_TWITTER_SUBPRODUCTS:
            return "low-signal twitter account graph export"

    if (
        material.source_family == SourceFamily.REDDIT_EXPORT
        and filename in LOW_SIGNAL_REDDIT_FILENAMES
    ):
        return "low-signal reddit account metadata/export index"

    if material.source_family == SourceFamily.DISCORD_DATA_PACKAGE:
        if (material.source_family_subproduct or "").lower() != "messages":
            return "low-signal discord non-message export"
        if any(marker in relative_import_path for marker in LOW_SIGNAL_DISCORD_PATH_MARKERS):
            return "low-signal discord account/server metadata"
        if (material.source_family_subproduct or "").lower() in LOW_SIGNAL_DISCORD_SUBPRODUCTS:
            return "low-signal discord account/server metadata"
        if filename in LOW_SIGNAL_DISCORD_FILENAMES:
            return "low-signal discord channel/package metadata"

    google_reason = _skip_google_takeout_path_reason(
        relative_import_path=relative_import_path,
        source_family=material.source_family.value,
    )
    if google_reason:
        return google_reason

    return None


def _skip_candidate_path_reason(relative_import_path: Path) -> str | None:
    if relative_import_path.name.startswith("."):
        return "low-signal hidden metadata file"
    if relative_import_path.suffix.lower() in LOW_SIGNAL_FILE_SUFFIXES:
        return "low-signal backup/temp file"
    if _expanded_opencode_session_path(relative_import_path):
        return "expanded opencode session directory duplicate"
    return _skip_google_takeout_path_reason(
        relative_import_path=relative_import_path.as_posix(),
        source_family=detect_source_family_from_path(relative_import_path).source_family.value,
    )


def _expanded_opencode_session_path(relative_import_path: Path) -> bool:
    parts = tuple(part.lower() for part in relative_import_path.parts)
    if "agent-logs" not in parts or "opencode" not in parts:
        return False
    try:
        opencode_index = parts.index("opencode")
    except ValueError:
        return False
    return any(part.endswith(".jsonl") for part in parts[opencode_index + 1 : -1])


def _skip_google_takeout_path_reason(
    *, relative_import_path: str, source_family: str
) -> str | None:
    if source_family != SourceFamily.GOOGLE_TAKEOUT.value:
        return None

    normalized_path = _normalized_path_text(relative_import_path)
    filename = Path(normalized_path).name
    suffix = Path(normalized_path).suffix

    if filename in LOW_SIGNAL_GOOGLE_TAKEOUT_FILENAMES:
        return "low-signal google takeout export index"
    if any(filename.startswith(prefix) for prefix in LOW_SIGNAL_GOOGLE_TAKEOUT_PREFIXES):
        return "low-signal google takeout external wordlist"
    if any(marker in normalized_path for marker in LOW_SIGNAL_GOOGLE_TAKEOUT_PATH_MARKERS):
        return "low-signal google takeout account/payment/device metadata"
    if any(marker in normalized_path for marker in LOW_SIGNAL_GOOGLE_TAKEOUT_FILE_MARKERS):
        return "low-signal google takeout browser settings metadata"
    if "/drive/" in normalized_path and suffix in GOOGLE_TAKEOUT_DRIVE_ARCHIVE_SUFFIXES:
        return "google takeout drive binary archive container"

    return None


def _normalized_path_text(value: str) -> str:
    # Google Takeout localizes folder names and sometimes uses non-breaking spaces.
    normalized = unicodedata.normalize("NFKD", value.lower().replace("\xa0", " "))
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "-"
    return ",".join(f"{name}:{counts[name]}" for name in sorted(counts))


def _resume_completed_count(entries) -> int:
    return sum(
        1
        for entry in entries
        if entry.status in {IngestMaterialStatus.PROCESSED, IngestMaterialStatus.SKIPPED}
    )


def _resolve_skill_node(
    *,
    candidate_name: str,
    canonical_name: str,
    decision: CanonicalSkillDecision,
    skills_by_id: dict[str, SkillNode],
    existing_skill_rows_by_id: dict[str, dict[str, object]],
) -> SkillNode:
    if decision.action == "use_existing":
        if decision.skill_id and decision.skill_id in skills_by_id:
            return skills_by_id[decision.skill_id]
        if decision.skill_id and decision.skill_id in existing_skill_rows_by_id:
            return _skill_node_from_row(existing_skill_rows_by_id[decision.skill_id])
        existing_match = _existing_skill_row_by_name(
            canonical_name=canonical_name,
            existing_skill_rows_by_id=existing_skill_rows_by_id,
        )
        if existing_match is not None:
            return _skill_node_from_row(existing_match)
    return build_skill_node(canonical_name or candidate_name)


def _existing_skill_row_by_name(
    *,
    canonical_name: str,
    existing_skill_rows_by_id: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    normalized_name = canonical_name.strip().lower()
    for row in existing_skill_rows_by_id.values():
        if str(row.get("name") or "").strip().lower() == normalized_name:
            return row
    return None


def _skill_node_from_row(row: dict[str, object]) -> SkillNode:
    return SkillNode(
        skill_id=str(row["skill_id"]),
        kind=SkillKind(str(row["kind"])),
        name=str(row["name"]),
        slug=str(row["slug"]),
        aliases=[],
        description=str(row["description"]) if row.get("description") is not None else None,
        taxonomy_refs=[],
        status=NodeStatus(str(row["status"])),
        created_by=str(row["created_by"]),
        last_updated=_row_datetime(row, "last_updated") or datetime.now(tz=UTC),
    )


def _merged_aliases(
    existing_aliases: list[str],
    override_aliases: set[str],
    decision_aliases: list[str],
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for alias in [*existing_aliases, *sorted(override_aliases), *decision_aliases]:
        normalized = alias.strip()
        if not normalized:
            continue
        lookup = normalized.lower()
        if lookup in seen:
            continue
        seen.add(lookup)
        merged.append(normalized)
    return merged


def _merge_evidence_items(
    existing_items: list[EvidenceItem],
    new_items: list[EvidenceItem],
) -> list[EvidenceItem]:
    merged_by_id = {item.evidence_id: item for item in existing_items}
    for item in new_items:
        merged_by_id[item.evidence_id] = item
    return [merged_by_id[evidence_id] for evidence_id in sorted(merged_by_id)]


def _taxonomy_edge_for_skill(skill: SkillNode) -> SkillEdge | None:
    if skill.kind != SkillKind.SKILL or not skill.description or "::" not in skill.description:
        return None
    domain_name = skill.description.split("::", maxsplit=1)[0]
    return SkillEdge(
        edge_id=f"edge_{short_hash(f'{domain_name}:{skill.skill_id}', length=10)}",
        from_skill_id=skill_id("domain", domain_name),
        to_skill_id=skill.skill_id,
        edge_type="parent_of",
        weight=1.0,
        source="taxonomy",
        confidence=1.0,
    )


def _overrides_fingerprint(overrides: list[dict[str, object]]) -> str:
    payload = [
        {
            "override_id": row.get("override_id"),
            "target_id": row.get("target_id"),
            "action": row.get("action"),
            "payload_json": row.get("payload_json"),
        }
        for row in sorted(
            overrides,
            key=lambda row: (
                str(row.get("override_id") or ""),
                str(row.get("target_id") or ""),
                str(row.get("action") or ""),
            ),
        )
    ]
    return short_hash(json.dumps(payload, sort_keys=True), length=24)


def _candidate_support_fingerprint(
    *,
    candidate_name: str,
    evidence_items: list[EvidenceItem],
    overrides_fingerprint: str,
    canonicalizer_version: str,
    scorer_version: str,
    model_name: str,
) -> str:
    payload = {
        "candidate_name": candidate_name,
        "overrides_fingerprint": overrides_fingerprint,
        "canonicalizer_version": canonicalizer_version,
        "scorer_version": scorer_version,
        "model_name": model_name,
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "source_id": item.source_id,
                "evidence_type": item.evidence_type.value,
                "signal_class": item.signal_class.value,
                "confidence": item.confidence,
                "time_reference": item.time_reference,
                "skill_candidates": item.skill_candidates,
            }
            for item in sorted(evidence_items, key=lambda item: item.evidence_id)
        ],
    }
    return short_hash(json.dumps(payload, sort_keys=True), length=24)


def _time_reference_to_datetime(value: str) -> datetime:
    normalized = _normalize_partial_time_reference(value)
    normalized = normalized.replace("Z", "+00:00") if normalized.endswith("Z") else normalized
    if re.fullmatch(r"\d{4}", normalized):
        normalized = f"{normalized}-01-01"
    elif re.fullmatch(r"\d{4}-\d{2}", normalized):
        normalized = f"{normalized}-01"
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _normalize_partial_time_reference(value: str) -> str:
    normalized = value.strip()
    normalized = re.sub(r"(?i)\bxx\b", "01", normalized)
    normalized = re.sub(r"(?i)\bunknown\b", "01", normalized)
    normalized = normalized.replace("??", "01")
    return normalized


def _estimate_acquired_at(
    *,
    first_seen_at: datetime | None,
    first_learned_at: datetime | None,
    first_strong_evidence_at: datetime | None,
    previous_acquired_at: datetime | None,
    previous_acquisition_basis: str | None,
) -> tuple[datetime | None, str | None]:
    if first_strong_evidence_at:
        return first_strong_evidence_at, "strong_evidence"
    if first_learned_at:
        return first_learned_at, "learning_evidence"
    if first_seen_at:
        return first_seen_at, "first_observed"
    return previous_acquired_at, previous_acquisition_basis
